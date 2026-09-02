from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from apps.api.dependencies import create_app_engine


P1_TABLES = {
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

P2_TABLES = {
    "users",
    "credentials",
    "project_memberships",
    "work_items",
    "work_sessions",
    "idempotency_records",
}

P4_TABLES = {
    "workflow_definitions",
    "workflow_versions",
    "workflow_executions",
    "workflow_step_runs",
    "work_artifacts",
    "human_confirmations",
}

P5_TABLES = {
    "skill_versions",
}

P6_TABLES = {
    "quality_evidence",
}

P7_TABLES = {
    "security_audit_events",
}

P8_TABLES = {
    "repository_revision_signals",
    "work_item_links",
    "pull_request_signals",
}


def _alembic_config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_alembic_upgrade_head_creates_current_schema(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"

    command.upgrade(_alembic_config(database_url), "head")

    inspector = inspect(create_engine(database_url))
    assert P1_TABLES | P2_TABLES | P4_TABLES | P5_TABLES | P6_TABLES | P7_TABLES | P8_TABLES <= set(inspector.get_table_names())


@pytest.mark.parametrize("database_url", ["sqlite:///:memory:", "sqlite+pysqlite:///:memory:"])
def test_create_app_engine_upgrades_empty_in_memory_database_on_same_engine(database_url):
    engine = create_app_engine(database_url)

    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM assets")) == 0
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260902_0015"


def test_p8_pull_request_signals_schema_links_project_work_item_and_actor(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"
    engine = create_engine(database_url)
    command.upgrade(_alembic_config(database_url), "head")
    inspector = inspect(engine)

    columns = {column["name"] for column in inspector.get_columns("pull_request_signals")}
    assert {
        "id",
        "org_id",
        "project_id",
        "work_item_id",
        "provider",
        "repository_identity",
        "pull_request_id",
        "pull_request_url",
        "title",
        "action",
        "source_branch",
        "target_branch",
        "head_sha",
        "merge_commit_sha",
        "status",
        "metadata",
        "created_by_user_id",
        "created_at",
    } <= columns
    referred_tables = {foreign_key["referred_table"] for foreign_key in inspector.get_foreign_keys("pull_request_signals")}
    assert {"projects", "work_items", "users"} <= referred_tables


def test_p8_work_item_links_schema_enforces_project_provider_key_identity(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"
    engine = create_engine(database_url)
    command.upgrade(_alembic_config(database_url), "head")
    inspector = inspect(engine)

    columns = {column["name"] for column in inspector.get_columns("work_item_links")}
    assert {
        "id",
        "org_id",
        "project_id",
        "work_item_id",
        "provider",
        "external_key",
        "external_url",
        "title",
        "status",
        "metadata",
        "created_by_user_id",
        "created_at",
        "updated_at",
    } <= columns
    uniques = inspector.get_unique_constraints("work_item_links")
    assert any(item["column_names"] == ["project_id", "provider", "external_key"] for item in uniques)
    referred_tables = {foreign_key["referred_table"] for foreign_key in inspector.get_foreign_keys("work_item_links")}
    assert {"projects", "work_items", "users"} <= referred_tables


def test_p8_repository_revision_signal_schema_links_project_and_work_item(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"
    engine = create_engine(database_url)
    command.upgrade(_alembic_config(database_url), "head")
    inspector = inspect(engine)

    columns = {column["name"] for column in inspector.get_columns("repository_revision_signals")}
    assert {
        "id",
        "org_id",
        "project_id",
        "work_item_id",
        "provider",
        "repository_identity",
        "branch",
        "observed_head_sha",
        "previous_head_sha",
        "signal_type",
        "status",
        "raw_ref",
        "metadata",
        "created_by_user_id",
        "created_at",
    } <= columns
    referred_tables = {foreign_key["referred_table"] for foreign_key in inspector.get_foreign_keys("repository_revision_signals")}
    assert {"projects", "work_items", "users"} <= referred_tables


def test_p7_security_audit_schema_links_actor_and_project(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"
    engine = create_engine(database_url)
    command.upgrade(_alembic_config(database_url), "head")
    inspector = inspect(engine)

    columns = {column["name"] for column in inspector.get_columns("security_audit_events")}
    assert {
        "id",
        "org_id",
        "project_id",
        "actor_user_id",
        "actor_credential_id",
        "actor_credential_kind",
        "action",
        "target_type",
        "target_id",
        "decision",
        "reason",
        "metadata",
        "created_at",
    } <= columns
    referred_tables = {foreign_key["referred_table"] for foreign_key in inspector.get_foreign_keys("security_audit_events")}
    assert {"projects", "users", "credentials"} <= referred_tables


def test_p6_quality_evidence_schema_links_to_work_item_session_and_user(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"
    engine = create_engine(database_url)
    command.upgrade(_alembic_config(database_url), "head")
    inspector = inspect(engine)

    columns = {column["name"] for column in inspector.get_columns("quality_evidence")}
    assert {
        "id",
        "org_id",
        "project_id",
        "work_item_id",
        "session_id",
        "evidence_type",
        "source",
        "status",
        "conclusion",
        "command",
        "output_summary",
        "raw_ref",
        "metadata",
        "created_by_user_id",
        "created_at",
    } <= columns
    referred_tables = {foreign_key["referred_table"] for foreign_key in inspector.get_foreign_keys("quality_evidence")}
    assert {"projects", "work_items", "work_sessions", "users"} <= referred_tables


def test_p2_schema_has_required_foreign_keys_and_uniqueness(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"
    engine = create_engine(database_url)
    command.upgrade(_alembic_config(database_url), "head")
    inspector = inspect(engine)

    credential_uniques = inspector.get_unique_constraints("credentials")
    membership_uniques = inspector.get_unique_constraints("project_memberships")
    idempotency_uniques = inspector.get_unique_constraints("idempotency_records")
    work_item_indexes = inspector.get_indexes("work_items")
    work_session_uniques = inspector.get_unique_constraints("work_sessions")
    work_session_indexes = inspector.get_indexes("work_sessions")

    assert any(item["column_names"] == ["token_hash"] for item in credential_uniques)
    assert any(item["column_names"] == ["project_id", "user_id"] for item in membership_uniques)
    assert any(
        item["column_names"] == ["credential_id", "operation", "idempotency_key"]
        for item in idempotency_uniques
    )
    assert any(
        item["unique"] and item["column_names"] == ["project_id", "external_key"]
        for item in work_item_indexes
    )
    assert work_session_uniques == []
    assert not any(item["unique"] for item in work_session_indexes)

    assert {foreign_key["referred_table"] for foreign_key in inspector.get_foreign_keys("work_sessions")} == {
        "work_items",
        "users",
        "credentials",
    }
    assert {foreign_key["referred_table"] for foreign_key in inspector.get_foreign_keys("idempotency_records")} == {
        "users",
        "credentials",
    }

    idempotency_columns = {column["name"] for column in inspector.get_columns("idempotency_records")}
    assert {
        "user_id",
        "credential_id",
        "operation",
        "idempotency_key",
        "request_hash",
        "response_json",
        "status",
        "replay_expires_at",
        "created_at",
        "updated_at",
    } <= idempotency_columns


def test_work_item_external_key_is_unique_only_when_present(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"
    engine = create_engine(database_url)
    command.upgrade(_alembic_config(database_url), "head")

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO projects
                    (id, org_id, name, slug, git_remotes, status, created_at, updated_at)
                VALUES
                    ('project-1', 'org-1', 'Project', 'project', '[]', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO work_items
                    (id, org_id, project_id, external_key, title, status, stage, source, created_at, updated_at)
                VALUES
                    ('work-null-1', 'org-1', 'project-1', NULL, 'One', 'active', 'backlog', 'manual', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                    ('work-null-2', 'org-1', 'project-1', NULL, 'Two', 'active', 'backlog', 'manual', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                    ('work-key-1', 'org-1', 'project-1', 'TASK-1', 'Three', 'active', 'backlog', 'manual', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            )
        )

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO work_items
                        (id, org_id, project_id, external_key, title, status, stage, source, created_at, updated_at)
                    VALUES
                        ('work-key-2', 'org-1', 'project-1', 'TASK-1', 'Duplicate', 'active', 'backlog', 'manual', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """
                )
            )


def test_downgrade_to_p1_keeps_p1_tables_and_reupgrade_restores_p2(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"
    config = _alembic_config(database_url)
    engine = create_engine(database_url)
    command.upgrade(config, "20260813_0001")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO projects
                    (id, org_id, name, slug, git_remotes, status, created_at, updated_at)
                VALUES
                    ('project-1', 'org-1', 'Project', 'project', '[]', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO task_sessions
                    (id, org_id, project_id, task_id, agent_type, intent, status, created_at)
                VALUES
                    ('session-1', 'org-1', 'project-1', 'TASK-1', 'codex', 'implement', 'started', CURRENT_TIMESTAMP)
                """
            )
        )

    command.upgrade(config, "head")
    command.downgrade(config, "20260813_0001")

    downgraded_tables = set(inspect(engine).get_table_names())
    assert P1_TABLES <= downgraded_tables
    assert P2_TABLES.isdisjoint(downgraded_tables)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM projects")) == 1
        assert connection.scalar(text("SELECT count(*) FROM task_sessions")) == 1

    command.upgrade(config, "head")

    assert P2_TABLES <= set(inspect(engine).get_table_names())
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM projects")) == 1
        assert connection.scalar(text("SELECT count(*) FROM task_sessions")) == 1
        assert connection.scalar(text("SELECT count(*) FROM work_sessions")) == 1


def test_alembic_config_file_is_committed():
    assert Path("alembic.ini").exists()
