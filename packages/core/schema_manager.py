from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import tempfile
from typing import Any

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import String as SAString
from sqlalchemy import column, create_engine, inspect, or_, select, table, text
from sqlalchemy.engine import Connection, Engine, make_url
from sqlalchemy.sql.sqltypes import Boolean, DateTime, Integer, JSON, String, Text


MIGRATION_REQUIRED = "MIGRATION_REQUIRED"
P1_REVISION = "20260813_0001"
ROOT_DIR = Path(__file__).resolve().parents[2]


class MigrationRequiredError(RuntimeError):
    def __init__(self, message: str):
        super().__init__(f"{MIGRATION_REQUIRED}: {message}")


@dataclass(frozen=True)
class SchemaMigrationResult:
    action: str
    fingerprint: str
    revision_before: str | None
    revision_after: str | None
    backup_path: Path | None = None


def _alembic_config(database_url: str) -> Config:
    config = Config(str(ROOT_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def get_alembic_heads() -> tuple[str, ...]:
    return tuple(ScriptDirectory.from_config(_alembic_config("sqlite://")).get_heads())


def _sqlite_path(database_url: str) -> Path | None:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        return None
    return Path(url.database).expanduser().resolve()


def _normalized_type(column_type: Any) -> str:
    if isinstance(column_type, Text):
        return "TEXT"
    if isinstance(column_type, DateTime):
        return "DATETIME"
    if isinstance(column_type, JSON):
        return "JSON"
    if isinstance(column_type, Boolean):
        return "BOOLEAN"
    if isinstance(column_type, Integer):
        return "INTEGER"
    if isinstance(column_type, String):
        return "STRING"
    return " ".join(str(column_type).upper().split())


# PostgreSQL renders index/check predicate text through pg_get_expr, which
# rewrites the DDL: `x IN ('a', 'b')` becomes `x = ANY (ARRAY['a', 'b'])`,
# literals get `::character varying`-style casts, and columns get a `::text`
# cast. SQLite keeps the predicate text verbatim. These helpers fold the
# PostgreSQL renderings back into the portable form so signatures agree across
# backends. The cast vocabulary is bounded to PostgreSQL's fixed type names so
# a cast can never run past the following token.
_PG_CAST_RE = re.compile(
    r"::(?:CHARACTER VARYING|DOUBLE PRECISION|TIMESTAMP(?: WITH(?:OUT)? TIME ZONE)?|"
    r"CHARACTER|VARCHAR(?:\(\d+\))?|BIGINT|SMALLINT|INTEGER|BOOLEAN|NUMERIC|"
    r"TEXT|JSONB|JSON|UUID|BYTEA|INTERVAL|REAL|CHAR(?:\(\d+\))?|INT|DATE|TIME)(?:\[\])?"
)
_PG_ANY_ARRAY_RE = re.compile(r"(\S+?) = ANY \(ARRAY\[([^\]]*)\]\)")
_PG_ALL_ARRAY_RE = re.compile(r"(\S+?) (?:<>|!=) ALL \(ARRAY\[([^\]]*)\]\)")
_DOUBLE_WRAPPED_ARRAY_RE = re.compile(r"\(\(ARRAY\[([^\]]*)\]\)\)")
_BARE_IDENTIFIER_PARENS_RE = re.compile(r"^\(([A-Z0-9_]+)\)(?=\s|$)")


def _fold_any_array(match: re.Match[str]) -> str:
    return f"{match.group(1)} IN ({match.group(2)})"


def _fold_all_array(match: re.Match[str]) -> str:
    return f"{match.group(1)} NOT IN ({match.group(2)})"


def _strip_outer_parens(text: str) -> str:
    """Strip one redundant outer parenthesis pair at a time, but only when the
    opening parenthesis at position 0 is closed by the final character (i.e. the
    pair truly wraps the whole expression)."""
    while text.startswith("("):
        depth = 0
        wrapped = False
        for index, char in enumerate(text):
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    if index == len(text) - 1:
                        text = text[1:-1].strip()
                        wrapped = True
                    break
        if not wrapped:
            break
    return text


def _normalized_predicate(value: Any) -> str | None:
    if value is None:
        return None
    predicate = " ".join(str(value).strip().upper().replace('"', "").split())
    predicate = _PG_CAST_RE.sub("", predicate)
    # pg_get_expr wraps the ARRAY constructor in an extra pair of parentheses
    # when it carries a type cast; collapse that back to a single wrap.
    predicate = _DOUBLE_WRAPPED_ARRAY_RE.sub(r"(ARRAY[\1])", predicate)
    predicate = _PG_ANY_ARRAY_RE.sub(_fold_any_array, predicate)
    predicate = _PG_ALL_ARRAY_RE.sub(_fold_all_array, predicate)
    predicate = _strip_outer_parens(predicate)
    predicate = _BARE_IDENTIFIER_PARENS_RE.sub(r"\1", predicate)
    return predicate


def _index_predicate(index: dict[str, Any]) -> Any:
    options = index.get("dialect_options", {})
    predicate = options.get("sqlite_where")
    if predicate is None:
        predicate = options.get("postgresql_where")
    return predicate


def _normalized_foreign_key_options(foreign_key: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    options = foreign_key.get("options") or {}
    return tuple(
        sorted(
            (name, value.upper() if isinstance(value, str) else value)
            for name, value in options.items()
        )
    )


def _schema_signature(bind: Engine | Connection) -> dict[str, Any]:
    inspector = inspect(bind)
    table_names = sorted(name for name in inspector.get_table_names() if name != "alembic_version")
    tables: dict[str, Any] = {}
    for table_name in table_names:
        pk_columns = set(inspector.get_pk_constraint(table_name).get("constrained_columns") or ())
        columns = []
        for column in inspector.get_columns(table_name):
            column_type = _normalized_type(column["type"])
            default = None if column.get("default") is None else str(column["default"])
            # PostgreSQL reports boolean server defaults as `true`/`false` while
            # SQLite stores them as `1`/`0`; normalize so signatures agree.
            if column_type == "BOOLEAN" and default is not None:
                default = {"TRUE": "1", "FALSE": "0", "1": "1", "0": "0"}.get(default.upper(), default)
            columns.append(
                {
                    "name": column["name"],
                    "type": column_type,
                    "nullable": bool(column["nullable"]),
                    # SQLite reports per-column primary_key from get_columns while
                    # PostgreSQL does not; derive from the table PK constraint so
                    # signatures are identical across backends.
                    "primary_key": int(column["name"] in pk_columns),
                    "default": default,
                }
            )
        foreign_keys = sorted(
            (
                tuple(foreign_key["constrained_columns"]),
                foreign_key["referred_table"],
                tuple(foreign_key["referred_columns"]),
                _normalized_foreign_key_options(foreign_key),
            )
            for foreign_key in inspector.get_foreign_keys(table_name)
        )
        indexes = sorted(
            (
                index["name"],
                tuple(index["column_names"]),
                bool(index["unique"]),
                _normalized_predicate(_index_predicate(index)),
            )
            for index in inspector.get_indexes(table_name)
            if not index.get("duplicates_constraint")
        )
        unique_constraints = sorted(
            tuple(constraint["column_names"])
            for constraint in inspector.get_unique_constraints(table_name)
        )
        check_constraints = sorted(
            _normalized_predicate(constraint.get("sqltext"))
            for constraint in inspector.get_check_constraints(table_name)
        )
        tables[table_name] = {
            "columns": columns,
            "primary_key": tuple(inspector.get_pk_constraint(table_name).get("constrained_columns") or ()),
            "foreign_keys": foreign_keys,
            "indexes": indexes,
            "unique_constraints": unique_constraints,
            "check_constraints": check_constraints,
        }
    return tables


def _fingerprint(signature: dict[str, Any]) -> str:
    encoded = json.dumps(signature, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@lru_cache(maxsize=None)
def _canonical_signature(revision: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="agora-schema-") as directory:
        database_url = f"sqlite+pysqlite:///{Path(directory) / 'canonical.db'}"
        command.upgrade(_alembic_config(database_url), revision)
        engine = create_engine(database_url)
        try:
            return _schema_signature(engine)
        finally:
            engine.dispose()


def _read_revision(connection: Connection) -> str | None:
    return connection.scalar(text("SELECT version_num FROM alembic_version"))


def _online_sqlite_backup(database_url: str) -> Path:
    database_path = _sqlite_path(database_url)
    if database_path is None:
        raise MigrationRequiredError("automatic backup requires a file-backed SQLite database")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = database_path.with_name(f"{database_path.name}.backup-{timestamp}")
    source_uri = f"file:{database_path}?mode=ro"
    with sqlite3.connect(source_uri, uri=True) as source, sqlite3.connect(backup_path) as destination:
        source.backup(destination)
    return backup_path


def _known_revision(config: Config, revision: str) -> bool:
    try:
        return ScriptDirectory.from_config(config).get_revision(revision) is not None
    except Exception:
        return False


def _legacy_task_session_validation_statement():
    task_sessions = table(
        "task_sessions",
        column("id", SAString()),
        column("project_id", SAString()),
        column("org_id", SAString()),
    )
    projects = table(
        "projects",
        column("id", SAString()),
        column("org_id", SAString()),
    )
    return (
        select(
            task_sessions.c.id.label("session_id"),
            task_sessions.c.project_id,
            task_sessions.c.org_id.label("session_org_id"),
            projects.c.org_id.label("project_org_id"),
        )
        .select_from(task_sessions.outerjoin(projects, projects.c.id == task_sessions.c.project_id))
        .where(or_(projects.c.id.is_(None), projects.c.org_id != task_sessions.c.org_id))
        .limit(1)
    )


def _validate_legacy_p1_data(connection: Connection) -> None:
    if connection.dialect.name == "sqlite":
        violation = connection.exec_driver_sql("PRAGMA foreign_key_check").first()
        if violation is not None:
            raise MigrationRequiredError(
                f"foreign key check failed for table {violation[0]!r}, rowid={violation[1]!r}"
            )

    invalid_session = connection.execute(_legacy_task_session_validation_statement()).mappings().first()
    if invalid_session is None:
        return
    if invalid_session["project_org_id"] is None:
        detail = f"references missing project {invalid_session['project_id']!r}"
    else:
        detail = (
            f"org_id {invalid_session['session_org_id']!r} does not match "
            f"project org_id {invalid_session['project_org_id']!r}"
        )
    raise MigrationRequiredError(f"task_sessions row {invalid_session['session_id']!r} {detail}")


def ensure_schema(
    database_url: str,
    *,
    dry_run: bool = False,
    postgres_backup_confirmed: bool = False,
    engine: Engine | None = None,
) -> SchemaMigrationResult:
    config = _alembic_config(database_url)
    head_revision = ScriptDirectory.from_config(config).get_current_head()
    database_path = _sqlite_path(database_url)
    if database_path is not None and not database_path.exists():
        if dry_run:
            return SchemaMigrationResult("upgrade_empty", _fingerprint({}), None, head_revision)
        database_path.parent.mkdir(parents=True, exist_ok=True)

    schema_engine = engine or create_engine(database_url)
    owns_engine = engine is None
    try:
        with schema_engine.begin() as connection:
            config.attributes["connection"] = connection
            signature = _schema_signature(connection)
            fingerprint = _fingerprint(signature)
            table_names = set(inspect(connection).get_table_names())
            has_version_table = "alembic_version" in table_names

            if not table_names:
                if not dry_run:
                    command.upgrade(config, "head")
                return SchemaMigrationResult("upgrade_empty", fingerprint, None, head_revision)

            if has_version_table:
                revision = _read_revision(connection)
                if revision is None or not _known_revision(config, revision):
                    raise MigrationRequiredError(f"unknown Alembic revision {revision!r}; fingerprint={fingerprint}")
                if signature != _canonical_signature(revision):
                    raise MigrationRequiredError(
                        f"schema does not match revision {revision}; fingerprint={fingerprint}"
                    )
                if revision == P1_REVISION:
                    _validate_legacy_p1_data(connection)
                if not dry_run:
                    command.upgrade(config, "head")
                return SchemaMigrationResult("upgrade_versioned", fingerprint, revision, head_revision)

            if signature != _canonical_signature(P1_REVISION):
                raise MigrationRequiredError(f"unknown or partial unversioned schema; fingerprint={fingerprint}")

            _validate_legacy_p1_data(connection)

            if dry_run:
                return SchemaMigrationResult("stamp_0001_and_upgrade", fingerprint, None, head_revision)

            backend = make_url(database_url).get_backend_name()
            if backend == "sqlite":
                backup_path = _online_sqlite_backup(database_url)
            elif postgres_backup_confirmed:
                backup_path = None
            else:
                raise MigrationRequiredError("PostgreSQL backup confirmation is required before stamping P1")

            command.stamp(config, P1_REVISION)
            command.upgrade(config, "head")
            return SchemaMigrationResult(
                "stamp_0001_and_upgrade",
                fingerprint,
                None,
                head_revision,
                backup_path,
            )
    finally:
        if owns_engine:
            schema_engine.dispose()
