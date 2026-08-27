from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from apps.api import dependencies
from apps.api.main import app
from packages.core.models import OutboxEventModel
from packages.core.uow import SqlAlchemyUnitOfWork


def test_health_endpoint_returns_ok():
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint_reports_database_schema_and_configuration(monkeypatch):
    monkeypatch.setenv("AGORA_BOOTSTRAP_HUMAN_TOKEN", "human-token")
    monkeypatch.setenv("AGORA_BOOTSTRAP_AGENT_TOKEN", "agent-token")
    monkeypatch.setenv("AGORA_BOOTSTRAP_CI_TOKEN", "ci-token")
    client = TestClient(app)

    response = client.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"]["status"] == "ok"
    assert body["checks"]["schema"]["revision"] == "20260826_0012"
    assert body["checks"]["configuration"]["missing_required"] == []
    assert body["checks"]["configuration"]["environment"] == "test"


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
