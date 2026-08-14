from __future__ import annotations

import importlib
from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, inspect, text

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

LEGACY_SESSION_IDS = {"session-shared-1", "session-shared-2", "session-taskless"}


def _alembic_config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _create_p1_database(database_url: str, entry_state: str) -> None:
    if entry_state == "versioned":
        command.upgrade(_alembic_config(database_url), "20260813_0001")
        return

    engine = create_engine(database_url)
    Base.metadata.create_all(engine, tables=[Base.metadata.tables[name] for name in sorted(P1_TABLE_NAMES)])
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
