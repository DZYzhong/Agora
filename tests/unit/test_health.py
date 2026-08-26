from fastapi.testclient import TestClient

from apps.api.main import app


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
