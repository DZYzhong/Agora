import pytest
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


def test_health_endpoint_stays_dependency_free(monkeypatch):
    def fail_if_called():
        raise AssertionError("health endpoint touched a dependency")

    monkeypatch.setattr(health_router, "get_engine", fail_if_called)
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

    monkeypatch.setattr(health_router, "get_engine", lambda: FailingEngine())

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


def test_readiness_endpoint_returns_503_when_alembic_revision_is_missing(monkeypatch):
    engine = _memory_engine()
    monkeypatch.setattr(health_router, "get_engine", lambda: engine)

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

    response = TestClient(app).get("/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["schema"] == {
        "status": "error",
        "code": "SCHEMA_REVISION_STALE",
    }
    engine.dispose()


def test_readiness_endpoint_returns_200_for_valid_isolated_test_configuration():
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


def test_metrics_endpoint_exposes_prometheus_style_operational_counters():
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

    response = TestClient(app).get("/metrics")

    assert response.status_code == 200
    assert "agora_ready 0" in response.text


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
