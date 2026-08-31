import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api import dependencies
from apps.api.main import app
from apps.api.routers import health as health_router
from packages.core.models import OutboxEventModel
from packages.core.uow import SqlAlchemyUnitOfWork


def _memory_engine():
    return create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _configure_database(monkeypatch, database_url):
    monkeypatch.setenv("AGORA_ENV", "test")
    monkeypatch.setenv("AGORA_DATABASE_URL", database_url)
    monkeypatch.setenv("AGORA_TEST_AUTH_BYPASS", "1")


def _upgrade_to_previous_revision(database_url):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    assert len(heads) == 1
    previous_revision = script.get_revision(heads[0]).down_revision
    assert isinstance(previous_revision, str)
    command.upgrade(config, previous_revision)


def test_health_endpoint_stays_dependency_free(monkeypatch):
    def fail_if_called():
        raise AssertionError("health endpoint touched a dependency")

    for dependency_name in (
        "get_runtime_policy",
        "create_readiness_probe_engine",
        "open_readiness_probe",
        "get_engine",
        "get_alembic_heads",
        "build_readiness_result",
    ):
        monkeypatch.setattr(health_router, dependency_name, fail_if_called, raising=False)
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint_returns_503_for_invalid_secret_bearing_configuration(monkeypatch):
    secret_database_url = "postgresql://secret-user:secret-password@secret-host/agora"
    monkeypatch.setenv("AGORA_ENV", "invalid-environment")
    monkeypatch.setenv("AGORA_DATABASE_URL", secret_database_url)
    monkeypatch.setattr(
        health_router,
        "get_engine",
        lambda: pytest.fail("invalid configuration must not create an engine"),
    )
    monkeypatch.setattr(
        health_router,
        "create_readiness_probe_engine",
        lambda policy: pytest.fail("invalid configuration must not create a probe engine"),
        raising=False,
    )
    client = TestClient(app)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {
            "configuration": {
                "status": "error",
                "code": "AGORA_ENV_INVALID",
                "error": "RuntimeConfigurationError",
            },
            "database": {"status": "unknown", "code": "CHECK_NOT_RUN"},
            "schema": {"status": "unknown", "code": "CHECK_NOT_RUN"},
        },
    }
    assert "secret-user" not in response.text
    assert "secret-password" not in response.text
    assert "secret-host" not in response.text


def test_readiness_endpoint_returns_503_when_engine_creation_fails(monkeypatch):
    class SecretEngineError(RuntimeError):
        pass

    def fail_engine_creation():
        raise SecretEngineError("postgresql://user:password@database/agora")

    monkeypatch.setattr(health_router, "get_engine", fail_engine_creation)
    monkeypatch.setattr(
        health_router,
        "create_readiness_probe_engine",
        lambda policy: fail_engine_creation(),
        raising=False,
    )

    response = TestClient(app).get("/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["database"] == {
        "status": "error",
        "code": "ENGINE_CREATION_FAILED",
        "error": "SecretEngineError",
    }
    assert "password" not in response.text


def test_readiness_endpoint_returns_503_when_database_query_fails(monkeypatch):
    class SecretDatabaseError(RuntimeError):
        pass

    class FailingConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def execute(self, statement):
            raise SecretDatabaseError("SELECT secret_value FROM private_table")

    class FailingEngine:
        def connect(self):
            return FailingConnection()

        def dispose(self):
            pass

    monkeypatch.setattr(health_router, "get_engine", lambda: FailingEngine())
    monkeypatch.setattr(
        health_router,
        "create_readiness_probe_engine",
        lambda policy: FailingEngine(),
        raising=False,
    )

    response = TestClient(app).get("/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["database"] == {
        "status": "error",
        "code": "DATABASE_QUERY_FAILED",
        "error": "SecretDatabaseError",
    }
    assert response.json()["checks"]["schema"] == {
        "status": "unknown",
        "code": "CHECK_NOT_RUN",
    }
    assert "secret_value" not in response.text


def test_readiness_returns_503_when_owned_probe_disposal_fails(monkeypatch):
    class SecretCleanupError(RuntimeError):
        pass

    delegate = dependencies.create_app_engine("sqlite+pysqlite:///:memory:")

    class CleanupFailingEngine:
        def connect(self):
            return delegate.connect()

        def dispose(self):
            raise SecretCleanupError("postgresql://user:cleanup-secret@database/agora")

    monkeypatch.setattr(
        health_router,
        "create_readiness_probe_engine",
        lambda policy: CleanupFailingEngine(),
    )

    response = TestClient(app).get("/ready")

    delegate.dispose()
    assert response.status_code == 503
    assert response.json()["checks"]["database"] == {
        "status": "error",
        "code": "PROBE_CLEANUP_FAILED",
        "error": "SecretCleanupError",
    }
    assert "cleanup-secret" not in response.text


def test_probe_disposal_failure_does_not_override_connection_failure(monkeypatch):
    class SecretConnectionError(RuntimeError):
        pass

    class SecretCleanupError(RuntimeError):
        pass

    class FailingEngine:
        def connect(self):
            raise SecretConnectionError("postgresql://user:connection-secret@database/agora")

        def dispose(self):
            raise SecretCleanupError("postgresql://user:cleanup-secret@database/agora")

    monkeypatch.setattr(
        health_router,
        "create_readiness_probe_engine",
        lambda policy: FailingEngine(),
    )

    response = TestClient(app).get("/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["database"] == {
        "status": "error",
        "code": "DATABASE_CONNECTION_FAILED",
        "error": "SecretConnectionError",
    }
    assert "connection-secret" not in response.text
    assert "cleanup-secret" not in response.text


def test_readiness_endpoint_returns_503_when_alembic_revision_is_missing(monkeypatch):
    engine = _memory_engine()
    monkeypatch.setattr(health_router, "get_engine", lambda: engine)
    monkeypatch.setattr(
        health_router,
        "create_readiness_probe_engine",
        lambda policy: engine,
        raising=False,
    )

    response = TestClient(app).get("/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["database"] == {
        "status": "ok",
        "code": "DATABASE_REACHABLE",
    }
    assert response.json()["checks"]["schema"] == {
        "status": "error",
        "code": "SCHEMA_REVISION_MISSING",
    }
    engine.dispose()


def test_readiness_endpoint_returns_503_when_database_revision_is_stale(monkeypatch):
    engine = _memory_engine()
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(text("INSERT INTO alembic_version VALUES ('stale-revision')"))
    monkeypatch.setattr(health_router, "get_engine", lambda: engine)
    monkeypatch.setattr(
        health_router,
        "create_readiness_probe_engine",
        lambda policy: engine,
        raising=False,
    )

    response = TestClient(app).get("/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["schema"] == {
        "status": "error",
        "code": "SCHEMA_REVISION_STALE",
    }
    engine.dispose()


def test_readiness_probe_does_not_migrate_a_real_stale_database(monkeypatch, tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'readiness-stale-test.db'}"
    _upgrade_to_previous_revision(database_url)
    _configure_database(monkeypatch, database_url)
    engine = create_engine(database_url)
    with engine.connect() as connection:
        revisions_before = connection.scalars(
            text("SELECT version_num FROM alembic_version")
        ).all()

    response = TestClient(app).get("/ready")

    with engine.connect() as connection:
        revisions_after = connection.scalars(
            text("SELECT version_num FROM alembic_version")
        ).all()
    engine.dispose()
    assert response.status_code == 503
    assert response.json()["checks"]["schema"] == {
        "status": "error",
        "code": "SCHEMA_REVISION_STALE",
    }
    assert revisions_after == revisions_before


def test_readiness_rejects_current_head_with_an_unexpected_extra_row(
    monkeypatch, tmp_path
):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'readiness-extra-head-test.db'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(
            text("INSERT INTO alembic_version VALUES (:revision)"),
            {"revision": health_router.get_alembic_heads()[0]},
        )
        connection.execute(
            text("INSERT INTO alembic_version VALUES ('unexpected-stale-row')")
        )
    engine.dispose()
    _configure_database(monkeypatch, database_url)

    response = TestClient(app).get("/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["schema"] == {
        "status": "error",
        "code": "SCHEMA_REVISION_STALE",
    }
    assert "unexpected-stale-row" not in response.text


def test_readiness_rejects_duplicate_current_head_rows(monkeypatch, tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'readiness-duplicate-head-test.db'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(
            text("INSERT INTO alembic_version VALUES (:revision), (:revision)"),
            {"revision": health_router.get_alembic_heads()[0]},
        )
    engine.dispose()
    _configure_database(monkeypatch, database_url)

    response = TestClient(app).get("/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["schema"] == {
        "status": "error",
        "code": "SCHEMA_REVISION_STALE",
    }


def test_readiness_endpoint_returns_200_for_valid_isolated_test_configuration():
    dependencies.get_engine()
    response = TestClient(app).get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {
            "configuration": {"status": "ok", "code": "RUNTIME_POLICY_VALID"},
            "database": {"status": "ok", "code": "DATABASE_REACHABLE"},
            "schema": {"status": "ok", "code": "SCHEMA_CURRENT"},
        },
    }


def test_readiness_reuses_initialized_in_memory_application_engine(monkeypatch):
    monkeypatch.setenv("AGORA_ENV", "development")
    monkeypatch.setenv("AGORA_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.delenv("AGORA_TEST_AUTH_BYPASS", raising=False)
    application_engine = dependencies.get_engine()

    response = TestClient(app).get("/ready")

    assert response.status_code == 200
    assert response.json()["checks"]["schema"] == {
        "status": "ok",
        "code": "SCHEMA_CURRENT",
    }
    assert dependencies.get_engine() is application_engine
    with application_engine.connect() as connection:
        assert connection.scalars(
            text("SELECT version_num FROM alembic_version")
        ).all() == list(health_router.get_alembic_heads())


def test_readiness_returns_stable_503_before_in_memory_startup_initialization(monkeypatch):
    monkeypatch.setenv("AGORA_ENV", "development")
    monkeypatch.setenv("AGORA_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.delenv("AGORA_TEST_AUTH_BYPASS", raising=False)
    dependencies.get_engine.cache_clear()

    response = TestClient(app).get("/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["database"] == {
        "status": "error",
        "code": "ENGINE_CREATION_FAILED",
        "error": "ReadinessProbeUnavailableError",
    }
    assert "memory" not in response.text
    assert dependencies.get_engine.cache_info().currsize == 0


def test_metrics_endpoint_exposes_prometheus_style_operational_counters():
    dependencies.get_engine()
    client = TestClient(app)

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    text = response.text
    assert "agora_ready 1" in text
    assert "agora_schema_revision_info" in text
    assert "agora_projects_total" in text
    assert "agora_pending_context_proposals_total" in text


def test_metrics_reports_not_ready_without_raising_when_readiness_fails(monkeypatch):
    monkeypatch.setattr(
        health_router,
        "build_readiness_result",
        lambda: {
            "status": "not_ready",
            "checks": {
                "configuration": {"status": "ok", "code": "RUNTIME_POLICY_VALID"},
                "database": {
                    "status": "error",
                    "code": "ENGINE_CREATION_FAILED",
                    "error": "RuntimeError",
                },
                "schema": {"status": "unknown", "code": "CHECK_NOT_RUN"},
            },
        },
        raising=False,
    )
    monkeypatch.setattr(
        health_router,
        "get_engine",
        lambda: pytest.fail("failed readiness must not retry dependency access"),
    )
    monkeypatch.setattr(
        health_router,
        "create_readiness_probe_engine",
        lambda policy: pytest.fail("failed readiness must not retry probe dependencies"),
        raising=False,
    )

    response = TestClient(app).get("/metrics")

    assert response.status_code == 200
    assert "agora_ready 0" in response.text


def test_metrics_emits_not_ready_when_probe_disposal_fails(monkeypatch):
    class SecretCleanupError(RuntimeError):
        pass

    delegate = dependencies.create_app_engine("sqlite+pysqlite:///:memory:")

    class CleanupFailingEngine:
        def connect(self):
            return delegate.connect()

        def dispose(self):
            raise SecretCleanupError("postgresql://user:cleanup-secret@database/agora")

    monkeypatch.setattr(
        health_router,
        "create_readiness_probe_engine",
        lambda policy: CleanupFailingEngine(),
    )
    monkeypatch.setattr(
        health_router,
        "get_engine",
        lambda: pytest.fail("cleanup failure must not collect database metrics"),
    )

    response = TestClient(app).get("/metrics")

    delegate.dispose()
    assert response.status_code == 200
    assert "agora_ready 0" in response.text
    assert "cleanup-secret" not in response.text


def test_metrics_endpoint_exposes_outbox_backlog_counters():
    session = sessionmaker(bind=dependencies.get_engine())()
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            session.add_all(
                [
                    OutboxEventModel(
                        org_id="org_1",
                        aggregate_type="context_stream",
                        aggregate_id="stream-main",
                        type="context_head_changed",
                        payload={"project_id": "project-1"},
                        status="pending",
                        attempts=0,
                        idempotency_key="context_head_changed:stream-main:rev-1",
                    ),
                    OutboxEventModel(
                        org_id="org_1",
                        aggregate_type="context_stream",
                        aggregate_id="stream-main",
                        type="context_head_changed",
                        payload={"project_id": "project-1"},
                        status="dead",
                        attempts=3,
                        last_error="projection schema mismatch",
                        idempotency_key="context_head_changed:stream-main:rev-2",
                    ),
                ]
            )
            uow.commit()
    finally:
        session.close()
    client = TestClient(app)

    response = client.get("/metrics")

    assert response.status_code == 200
    text = response.text
    assert "agora_outbox_events_total{status=\"pending\"} 1" in text
    assert "agora_outbox_events_total{status=\"dead\"} 1" in text
    assert "agora_outbox_retryable_total 1" in text


def test_api_generates_request_id_for_every_response():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) >= 16


def test_api_preserves_incoming_request_id():
    client = TestClient(app)

    response = client.get("/health", headers={"X-Request-ID": "deploy-smoke-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "deploy-smoke-123"


def test_api_adds_request_id_to_error_responses():
    client = TestClient(app)

    response = client.get("/missing-route")

    assert response.status_code == 404
    assert response.headers["X-Request-ID"]
