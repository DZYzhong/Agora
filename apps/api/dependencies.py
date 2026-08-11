from collections.abc import Generator
from functools import lru_cache
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from packages.core.database import Base
import packages.core.models  # noqa: F401
from packages.knowledge.index_rebuilder import rebuild_indexes_from_assets
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex


DEFAULT_DATABASE_URL = "sqlite+pysqlite:///.agora/agora.db"


def create_app_engine(database_url: str) -> Engine:
    if database_url.startswith("sqlite") and database_url != "sqlite+pysqlite:///:memory:":
        database_path = database_url.rsplit("///", 1)[-1]
        if database_path and database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    if database_url == "sqlite+pysqlite:///:memory:":
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


@lru_cache
def get_engine():
    database_url = os.environ.get("AGORA_DATABASE_URL", DEFAULT_DATABASE_URL)
    engine = create_app_engine(database_url)
    Base.metadata.create_all(engine)
    _rebuild_search_indexes(engine)
    return engine


def get_db_session() -> Generator[Session, None, None]:
    session_factory = sessionmaker(bind=get_engine())
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@lru_cache
def get_keyword_index() -> FakeKeywordIndex:
    return FakeKeywordIndex()


@lru_cache
def get_vector_index() -> FakeVectorIndex:
    return FakeVectorIndex()


def _rebuild_search_indexes(engine: Engine) -> None:
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        rebuild_indexes_from_assets(session, get_keyword_index(), get_vector_index())
    finally:
        session.close()
