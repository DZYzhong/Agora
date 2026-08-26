from __future__ import annotations

import importlib
from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import CheckConstraint, MetaData, create_engine, inspect, text
from sqlalchemy.dialects import postgresql

from packages.core.database import Base
import packages.core.models  # noqa: F401


P1_TABLE_NAMES = {
    "projects",
    "assets",
    "project_initialization_jobs",
    "context_packs",
    "skills",
    "skill_runs",
    "task_sessions",
    "session_events",
    "writebacks",
}

P2_TABLE_NAMES = {
    "users",
    "credentials",
    "project_memberships",
    "work_items",
    "work_sessions",
    "idempotency_records",
}

LEGACY_SESSION_IDS = {"session-shared-1", "session-shared-2", "session-taskless"}


def _alembic_config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _create_p1_database(database_url: str, entry_state: str) -> None:
    command.upgrade(_alembic_config(database_url), "20260813_0001")

    if entry_state == "unversioned_create_all":
        engine = create_engine(database_url)
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE alembic_version"))
        engine.dispose()


def _seed_p1_database(database_url: str) -> None:
    engine = create_engine(database_url)
    statements = [
        """
        INSERT INTO projects
            (id, org_id, name, slug, description, git_remotes, default_branch, status, created_at, updated_at)
        VALUES
            ('project-1', 'org-1', 'Project One', 'project-one', 'First', '[\"git@example/one\"]', 'main', 'active', '2026-08-13 01:00:00', '2026-08-13 02:00:00'),
            ('project-2', 'org-2', 'Project Two', 'project-two', 'Second', '[]', NULL, 'active', '2026-08-13 03:00:00', '2026-08-13 04:00:00')
        """,
        """
        INSERT INTO assets
            (id, org_id, project_id, type, source, source_uri, title, content, summary, metadata, content_hash, created_at, updated_at)
        VALUES
            ('asset-1', 'org-1', 'project-1', 'code_file', 'git', 'src/one.py', 'one.py', 'print(1)', 'one', '{}', 'hash-1', '2026-08-13 01:00:00', '2026-08-13 02:00:00'),
            ('asset-2', 'org-2', 'project-2', 'doc', 'manual', 'README.md', 'Readme', 'Project two', NULL, '{}', NULL, '2026-08-13 03:00:00', '2026-08-13 04:00:00')
        """,
        """
        INSERT INTO context_packs
            (id, org_id, project_id, level, summary, key_facts, source_refs, created_at)
        VALUES
            ('context-1', 'org-1', 'project-1', 'project', 'Context', '[{\"fact\": \"kept\"}]', '[{\"asset_id\": \"asset-1\"}]', '2026-08-13 01:00:00')
        """,
        """
        INSERT INTO skills
            (id, org_id, project_id, slug, name, status, definition, created_at)
        VALUES
            ('skill-1', 'org-1', 'project-1', 'review', 'Review', 'approved', '{\"instructions\": \"review\"}', '2026-08-13 01:00:00')
        """,
        """
        INSERT INTO task_sessions
            (id, org_id, project_id, task_id, agent_type, intent, status, created_at, closed_at)
        VALUES
            ('session-shared-1', 'org-1', 'project-1', 'TASK-42', 'codex', 'first intent', 'closed', '2026-08-13 05:00:00', '2026-08-13 06:00:00'),
            ('session-shared-2', 'org-1', 'project-1', 'TASK-42', 'claude', 'second intent', 'working', '2026-08-13 07:00:00', NULL),
            ('session-taskless', 'org-1', 'project-1', NULL, 'codex', 'taskless intent', 'started', '2026-08-13 08:00:00', NULL)
        """,
        """
        INSERT INTO session_events
            (id, session_id, event_type, payload, created_at)
        VALUES
            ('event-1', 'session-shared-1', 'started', '{\"kept\": true}', '2026-08-13 05:00:00'),
            ('event-2', 'session-taskless', 'started', '{}', '2026-08-13 08:00:00')
        """,
        """
        INSERT INTO skill_runs
            (id, org_id, project_id, session_id, skill_id, input, output, warnings, status, created_at)
        VALUES
            ('run-1', 'org-1', 'project-1', 'session-shared-2', 'skill-1', '{}', '{\"kept\": true}', '[]', 'completed', '2026-08-13 07:00:00')
        """,
        """
        INSERT INTO writebacks
            (id, org_id, project_id, session_id, type, title, content, asset_refs, status, accepted_asset_id, created_at, updated_at)
        VALUES
            ('writeback-1', 'org-1', 'project-1', 'session-shared-1', 'doc', 'Kept', 'Content', '[\"asset-1\"]', 'draft', NULL, '2026-08-13 06:00:00', '2026-08-13 06:00:00')
        """,
    ]
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
    engine.dispose()


def _schema_manager():
    return importlib.import_module("packages.core.schema_manager")


@pytest.mark.parametrize("entry_state", ["versioned", "unversioned_create_all"])
def test_schema_manager_migrates_p1_without_losing_data(tmp_path, entry_state):
    database_path = tmp_path / f"{entry_state}.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    _create_p1_database(database_url, entry_state)
    _seed_p1_database(database_url)

    result = _schema_manager().ensure_schema(database_url)

    engine = create_engine(database_url)
    inspector = inspect(engine)
    assert {"users", "credentials", "project_memberships", "work_items", "work_sessions", "idempotency_records"} <= set(
        inspector.get_table_names()
    )

    expected_counts = {
        "projects": 2,
        "assets": 2,
        "context_packs": 1,
        "skills": 1,
        "skill_runs": 1,
        "writebacks": 1,
        "session_events": 2,
        "task_sessions": 3,
        "work_items": 2,
        "work_sessions": 3,
    }
    with engine.connect() as connection:
        for table_name, expected_count in expected_counts.items():
            assert connection.scalar(text(f"SELECT count(*) FROM {table_name}")) == expected_count

        assert set(connection.scalars(text("SELECT id FROM work_sessions"))) == LEGACY_SESSION_IDS
        assert set(connection.scalars(text("SELECT session_id FROM session_events"))) == {
            "session-shared-1",
            "session-taskless",
        }
        assert set(connection.scalars(text("SELECT session_id FROM writebacks"))) == {"session-shared-1"}
        assert set(connection.scalars(text("SELECT session_id FROM skill_runs"))) == {"session-shared-2"}

        shared_work_item_count = connection.scalar(
            text("SELECT count(*) FROM work_items WHERE project_id = 'project-1' AND external_key = 'TASK-42'")
        )
        taskless_work_item_count = connection.scalar(
            text("SELECT count(*) FROM work_items WHERE project_id = 'project-1' AND external_key IS NULL")
        )
        assert shared_work_item_count == 1
        assert taskless_work_item_count == 1

        migrated_sessions = connection.execute(
            text(
                """
                SELECT ws.id, ws.user_id, ws.credential_id, ws.initial_request_id,
                       ws.agent_type, ws.intent, ws.status AS session_status,
                       ws.created_at, ws.closed_at, ws.legacy_imported,
                       u.org_id, u.status AS user_status, u.is_placeholder
                FROM work_sessions AS ws
                JOIN users AS u ON u.id = ws.user_id
                ORDER BY ws.id
                """
            )
        ).mappings().all()
        assert all(row["credential_id"] is None for row in migrated_sessions)
        assert all(row["initial_request_id"] is None for row in migrated_sessions)
        assert all(row["legacy_imported"] for row in migrated_sessions)
        assert all(row["org_id"] == "org-1" for row in migrated_sessions)
        assert {row["session_status"] for row in migrated_sessions} == {"closed", "working", "started"}
        assert all(row["user_status"] == "disabled" for row in migrated_sessions)
        assert {(row["agent_type"], row["intent"]) for row in migrated_sessions} == {
            ("codex", "first intent"),
            ("claude", "second intent"),
            ("codex", "taskless intent"),
        }
        sessions_by_id = {row["id"]: row for row in migrated_sessions}
        assert sessions_by_id["session-shared-1"]["created_at"] == "2026-08-13 05:00:00.000000"
        assert sessions_by_id["session-shared-1"]["closed_at"] == "2026-08-13 06:00:00.000000"
        assert sessions_by_id["session-shared-2"]["created_at"] == "2026-08-13 07:00:00.000000"
        assert sessions_by_id["session-taskless"]["created_at"] == "2026-08-13 08:00:00.000000"
        assert connection.scalar(text("SELECT count(*) FROM users WHERE status = 'disabled' AND is_placeholder")) == 2

    if entry_state == "unversioned_create_all":
        assert result.backup_path is not None
        backup_path = Path(result.backup_path)
        assert backup_path.exists()
        assert backup_path != database_path
        assert backup_path.stat().st_ino != database_path.stat().st_ino
        with sqlite3.connect(backup_path) as backup:
            backup_tables = {row[0] for row in backup.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            assert P1_TABLE_NAMES <= backup_tables
            assert "alembic_version" not in backup_tables
            assert "work_sessions" not in backup_tables
            assert backup.execute("SELECT count(*) FROM task_sessions").fetchone()[0] == 3
    else:
        assert result.backup_path is None


def test_unknown_partial_schema_is_rejected_without_mutation(tmp_path):
    database_path = tmp_path / "partial.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE projects (id TEXT PRIMARY KEY, unexpected TEXT)")
        connection.execute("INSERT INTO projects (id, unexpected) VALUES ('keep-me', 'unchanged')")

    before_bytes = database_path.read_bytes()

    with pytest.raises(RuntimeError, match="MIGRATION_REQUIRED"):
        _schema_manager().ensure_schema(database_url)

    assert database_path.read_bytes() == before_bytes
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT id, unexpected FROM projects").fetchall() == [("keep-me", "unchanged")]
        assert connection.execute(
            "SELECT count(*) FROM sqlite_master WHERE type = 'table' AND name = 'alembic_version'"
        ).fetchone()[0] == 0


def test_schema_manager_dry_run_reports_fingerprint_without_mutation(tmp_path):
    database_path = tmp_path / "p1.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    _create_p1_database(database_url, "unversioned_create_all")
    before_bytes = database_path.read_bytes()

    result = _schema_manager().ensure_schema(database_url, dry_run=True)

    assert result.action == "stamp_0001_and_upgrade"
    assert len(result.fingerprint) == 64
    assert result.backup_path is None
    assert database_path.read_bytes() == before_bytes


@pytest.mark.parametrize("entry_state", ["versioned", "unversioned_create_all"])
@pytest.mark.parametrize("corruption", ["missing_project", "org_mismatch"])
def test_legacy_task_session_project_boundary_is_validated_before_p2_ddl(tmp_path, entry_state, corruption):
    database_path = tmp_path / f"{entry_state}-{corruption}.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    _create_p1_database(database_url, entry_state)
    _seed_p1_database(database_url)
    engine = create_engine(database_url)
    with engine.begin() as connection:
        if corruption == "missing_project":
            connection.execute(
                text("UPDATE task_sessions SET project_id = 'missing-project' WHERE id = 'session-shared-1'")
            )
        else:
            connection.execute(text("UPDATE task_sessions SET org_id = 'org-2' WHERE id = 'session-shared-1'"))

    with pytest.raises(RuntimeError, match="MIGRATION_REQUIRED.*task_sessions"):
        _schema_manager().ensure_schema(database_url)

    inspector = inspect(engine)
    assert P2_TABLE_NAMES.isdisjoint(inspector.get_table_names())
    if entry_state == "versioned":
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260813_0001"
    else:
        assert "alembic_version" not in inspector.get_table_names()
        assert list(tmp_path.glob(f"{database_path.name}.backup-*")) == []


def test_sqlite_foreign_key_check_rejects_corrupt_p1_before_p2_ddl(tmp_path):
    database_path = tmp_path / "broken-foreign-key.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    _create_p1_database(database_url, "unversioned_create_all")
    _seed_p1_database(database_url)
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("UPDATE assets SET project_id = 'missing-project' WHERE id = 'asset-1'"))

    with pytest.raises(RuntimeError, match="MIGRATION_REQUIRED.*foreign key"):
        _schema_manager().ensure_schema(database_url)

    assert P2_TABLE_NAMES.isdisjoint(inspect(engine).get_table_names())
    assert list(tmp_path.glob(f"{database_path.name}.backup-*")) == []


def test_legacy_validation_query_compiles_for_postgres():
    statement = _schema_manager()._legacy_task_session_validation_statement()

    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "LEFT OUTER JOIN projects" in compiled
    assert "task_sessions.project_id" in compiled
    assert "task_sessions.org_id" in compiled


def test_unversioned_p1_with_modified_check_constraint_is_rejected_unchanged(tmp_path):
    database_path = tmp_path / "modified-check.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    _create_p1_database(database_url, "unversioned_create_all")
    engine = create_engine(database_url)
    metadata = MetaData()
    altered_context_packs = Base.metadata.tables["context_packs"].to_metadata(metadata)
    altered_context_packs.append_constraint(
        CheckConstraint("length(summary) > 0", name="ck_context_packs_nonempty_summary")
    )
    with engine.begin() as connection:
        Base.metadata.tables["context_packs"].drop(connection)
        altered_context_packs.create(connection)
    engine.dispose()
    before_bytes = database_path.read_bytes()

    with pytest.raises(RuntimeError, match="MIGRATION_REQUIRED"):
        _schema_manager().ensure_schema(database_url)

    assert database_path.read_bytes() == before_bytes


def test_unversioned_p1_with_modified_foreign_key_options_is_rejected_unchanged(tmp_path):
    database_path = tmp_path / "modified-foreign-key.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    _create_p1_database(database_url, "unversioned_create_all")
    engine = create_engine(database_url)
    before_columns = inspect(engine).get_columns("assets")
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            PRAGMA foreign_keys = OFF;
            ALTER TABLE assets RENAME TO assets_original;
            CREATE TABLE assets (
                id VARCHAR NOT NULL,
                org_id VARCHAR NOT NULL,
                project_id VARCHAR NOT NULL,
                type VARCHAR NOT NULL,
                source VARCHAR NOT NULL,
                source_uri VARCHAR NOT NULL,
                title VARCHAR NOT NULL,
                content TEXT NOT NULL,
                summary TEXT,
                metadata JSON NOT NULL,
                content_hash VARCHAR,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                PRIMARY KEY (id),
                FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE ON UPDATE CASCADE
            );
            DROP TABLE assets_original;
            CREATE INDEX ix_assets_org_id ON assets (org_id);
            CREATE INDEX ix_assets_project_id ON assets (project_id);
            CREATE INDEX ix_assets_type ON assets (type);
            CREATE INDEX ix_assets_source ON assets (source);
            """
        )
    engine.dispose()
    altered_inspector = inspect(create_engine(database_url))
    assert [column["name"] for column in altered_inspector.get_columns("assets")] == [
        column["name"] for column in before_columns
    ]
    assert altered_inspector.get_foreign_keys("assets")[0]["options"] == {
        "ondelete": "CASCADE",
        "onupdate": "CASCADE",
    }
    before_bytes = database_path.read_bytes()

    with pytest.raises(RuntimeError, match="MIGRATION_REQUIRED"):
        _schema_manager().ensure_schema(database_url)

    assert database_path.read_bytes() == before_bytes


@pytest.mark.parametrize("corruption", ["missing_project", "org_mismatch", "foreign_key"])
def test_direct_alembic_upgrade_rejects_corrupt_p1_before_p2_ddl(tmp_path, corruption):
    database_path = tmp_path / f"direct-{corruption}.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    config = _alembic_config(database_url)
    _create_p1_database(database_url, "versioned")
    _seed_p1_database(database_url)
    engine = create_engine(database_url)
    with engine.begin() as connection:
        if corruption == "missing_project":
            connection.execute(
                text("UPDATE task_sessions SET project_id = 'missing-project' WHERE id = 'session-shared-1'")
            )
        elif corruption == "org_mismatch":
            connection.execute(text("UPDATE task_sessions SET org_id = 'org-2' WHERE id = 'session-shared-1'"))
        else:
            connection.execute(text("UPDATE assets SET project_id = 'missing-project' WHERE id = 'asset-1'"))

    with pytest.raises(RuntimeError, match="legacy P1 validation"):
        command.upgrade(config, "head")

    inspector = inspect(engine)
    assert P2_TABLE_NAMES.isdisjoint(inspector.get_table_names())
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260813_0001"


def test_p2_revision_legacy_validation_query_compiles_for_postgres():
    revision = ScriptDirectory.from_config(Config("alembic.ini")).get_revision("20260814_0002")

    compiled = str(revision.module._legacy_task_session_validation_statement().compile(dialect=postgresql.dialect()))

    assert "LEFT OUTER JOIN projects" in compiled
    assert "task_sessions.project_id" in compiled
    assert "task_sessions.org_id" in compiled
