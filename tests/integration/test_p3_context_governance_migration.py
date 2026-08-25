from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def _alembic_config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_p3_context_governance_tables_are_created(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"

    command.upgrade(_alembic_config(database_url), "head")

    inspector = inspect(create_engine(database_url))
    assert {
        "context_streams",
        "context_revisions",
        "context_proposals",
        "approval_decisions",
        "outbox_events",
    } <= set(inspector.get_table_names())
    outbox_columns = {column["name"] for column in inspector.get_columns("outbox_events")}
    assert "last_error" in outbox_columns
