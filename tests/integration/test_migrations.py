from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_head_creates_current_schema(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "head")

    inspector = inspect(create_engine(database_url))
    assert {
        "projects",
        "assets",
        "project_initialization_jobs",
        "context_packs",
        "skills",
        "skill_runs",
        "task_sessions",
        "session_events",
        "writebacks",
    }.issubset(set(inspector.get_table_names()))


def test_alembic_config_file_is_committed():
    assert Path("alembic.ini").exists()
