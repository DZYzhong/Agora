from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
import logging
import os
from typing import Callable

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from packages.core.schema_manager import ensure_schema
from packages.core.settings import RuntimePolicy, validate_runtime_policy
from packages.knowledge.index_rebuilder import rebuild_indexes_from_assets
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.postgres_fts import has_fts_support
from packages.storage.qdrant.fake import FakeVectorIndex


DEFAULT_DATABASE_URL = "sqlite+pysqlite:///.agora/agora.db"
AGORA_TEST_AUTH_BYPASS = "AGORA_TEST_AUTH_BYPASS"


class ReadinessProbeUnavailableError(RuntimeError):
    pass


@dataclass
class ReadinessProbe:
    engine: Engine
    owned: bool
    cleanup_error: Exception | None = None


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


def create_readiness_probe_engine(policy: RuntimePolicy) -> Engine:
    url = make_url(policy.database_url)
    if url.get_backend_name() != "sqlite":
        return create_engine(url)
    if url.database == ":memory:":
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    query = dict(url.query)
    query.update({"mode": "ro", "uri": "true"})
    read_only_url = url.set(database=f"file:{url.database}", query=query)
    return create_engine(
        read_only_url,
        connect_args={"check_same_thread": False},
    )


@contextmanager
def open_readiness_probe(
    policy: RuntimePolicy,
    engine_factory: Callable[[RuntimePolicy], Engine],
) -> Generator[ReadinessProbe, None, None]:
    url = make_url(policy.database_url)
    if url.get_backend_name() == "sqlite" and url.database == ":memory:":
        if get_engine.cache_info().currsize == 0:
            raise ReadinessProbeUnavailableError(
                "in-memory application engine has not been initialized"
            )
        probe = ReadinessProbe(engine=get_engine(), owned=False)
        yield probe
        return

    probe = ReadinessProbe(engine=engine_factory(policy), owned=True)
    try:
        yield probe
    finally:
        try:
            probe.engine.dispose()
        except Exception as exc:
            probe.cleanup_error = exc


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


def get_runtime_policy() -> RuntimePolicy:
    return validate_runtime_policy(
        os.environ.get("AGORA_ENV"),
        os.environ.get("AGORA_DATABASE_URL", DEFAULT_DATABASE_URL),
        os.environ.get(AGORA_TEST_AUTH_BYPASS) == "1",
        os.environ.get("AGORA_LOCAL_INIT_ROOT"),
    )


def auth_bypass_enabled() -> bool:
    return get_runtime_policy().auth_bypass


logger = logging.getLogger(__name__)


def _postgres_keyword_index_enabled() -> bool:
    """True when the configured database is PostgreSQL and carries the FTS
    column. Probes with an independent engine to avoid recursion through
    get_engine() (which itself rebuilds indexes)."""
    try:
        policy = get_runtime_policy()
        if make_url(policy.database_url).get_backend_name() != "postgresql":
            return False
        engine = create_app_engine(policy.database_url)
        try:
            return has_fts_support(engine)
        finally:
            engine.dispose()
    except Exception as exc:
        logger.warning("keyword index probe failed, using Fake: %s", exc)
        return False


@lru_cache
def _postgres_keyword_index_enabled_cached() -> bool:
    return _postgres_keyword_index_enabled()


@lru_cache
def get_keyword_index():
    """Runtime keyword retrieval: PostgreSQL FTS on PG, in-memory Fake on
    SQLite (tests/CI). Fake was rebuilt per request and never shared across
    requests; the PG path queries committed assets directly."""
    if _postgres_keyword_index_enabled_cached():
        from packages.storage.postgres_fts import PostgresKeywordIndex

        return PostgresKeywordIndex(get_runtime_policy().database_url)
    from packages.storage.opensearch.fake import FakeKeywordIndex

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
