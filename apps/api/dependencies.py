from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from packages.core.database import Base
import packages.core.models  # noqa: F401
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex


@lru_cache
def get_engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
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
