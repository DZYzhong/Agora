from collections.abc import Generator
from functools import lru_cache
import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from packages.core.schema_manager import ensure_schema
from packages.knowledge.index_rebuilder import rebuild_indexes_from_assets
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex


DEFAULT_DATABASE_URL = "sqlite+pysqlite:///.agora/agora.db"
AGORA_TEST_AUTH_BYPASS = "AGORA_TEST_AUTH_BYPASS"


def create_app_engine(database_url: str) -> Engine:
    url = make_url(database_url)
    is_sqlite = url.get_backend_name() == "sqlite"
    if is_sqlite and url.database == ":memory:":
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        ensure_schema(database_url, engine=engine)
        return engine

    ensure_schema(database_url)
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    return create_engine(database_url, connect_args=connect_args)


@lru_cache
def get_engine():
    database_url = os.environ.get("AGORA_DATABASE_URL", DEFAULT_DATABASE_URL)
    engine = create_app_engine(database_url)
    _rebuild_search_indexes(engine)
    return engine


def get_db_session() -> Generator[Session, None, None]:
    """Own only session lifetime; application commands own transactions."""
    session_factory = sessionmaker(bind=get_engine())
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def auth_bypass_enabled() -> bool:
    return os.environ.get(AGORA_TEST_AUTH_BYPASS) == "1"


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
