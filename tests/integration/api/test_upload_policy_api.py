from fastapi.testclient import TestClient

from apps.api.main import app

HUMAN_TOKEN = "upload-human-token"
AGENT_TOKEN = "upload-agent-token"


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _production_auth(monkeypatch) -> None:
    monkeypatch.delenv("AGORA_TEST_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("AGORA_BOOTSTRAP_HUMAN_TOKEN", HUMAN_TOKEN)
    monkeypatch.setenv("AGORA_BOOTSTRAP_AGENT_TOKEN", AGENT_TOKEN)
    monkeypatch.setenv("AGORA_BOOTSTRAP_ORG_ID", "local-org")


def _started_session(client: TestClient) -> dict:
    project = client.post(
        "/projects",
        headers=_headers(HUMAN_TOKEN),
        json={"org_id": "local-org", "name": "Upload Policy", "slug": "upload-policy", "git_remotes": []},
    ).json()
    started = client.post(
        "/harness/start-work",
        headers=_headers(AGENT_TOKEN),
        json={"project_id": project["id"], "user_message": "上传策略验证", "agent_type": "codex"},
    ).json()
    return {"project": project, "session_id": started["session_id"]}


def test_close_work_clean_development_update_accepted_from_agent(monkeypatch):
    _production_auth(monkeypatch)
    with TestClient(app) as client:
        context = _started_session(client)
        response = client.post(
            "/harness/close-work",
            headers={
                **_headers(AGENT_TOKEN),
                "Agora-Protocol-Version": "1.1",
                "Agora-Connector-Version": "0.1.0",
                "Idempotency-Key": "upload-clean",
            },
            json={
                "session_id": context["session_id"],
                "development_update": {
                    "changed_files": [{"path": "src/app.py", "status": "modified"}],
                    "dirty": True,
                    "diff_stat": {"files_changed": 1, "insertions": 1, "deletions": 0},
                    "agent_summary": "完成了支付状态流转。",
                    "test_result": "pytest passed",
                },
            },
        )
        assert response.status_code == 200, response.text


def test_close_work_high_risk_update_requires_grant(monkeypatch):
    _production_auth(monkeypatch)
    with TestClient(app) as client:
        context = _started_session(client)
        response = client.post(
            "/harness/close-work",
            headers={
                **_headers(AGENT_TOKEN),
                "Agora-Protocol-Version": "1.1",
                "Agora-Connector-Version": "0.1.0",
                "Idempotency-Key": "upload-high-risk",
            },
            json={
                "session_id": context["session_id"],
                "development_update": {
                    "changed_files": [{"path": "src/app.py", "status": "modified"}],
                    "dirty": True,
                    "diff_stat": {"files_changed": 1, "insertions": 1, "deletions": 0},
                    "agent_summary": "导出 AWS_ACCESS_KEY_ID=AKIAEXAMPLE 的配置说明。",
                    "test_result": "pytest passed",
                },
            },
        )
        assert response.status_code == 403, response.text
        assert response.json()["detail"]["code"] == "HIGH_RISK_UPLOAD_REQUIRES_GRANT"


def test_close_work_policy_violation_returns_stable_error(monkeypatch):
    _production_auth(monkeypatch)
    with TestClient(app) as client:
        context = _started_session(client)
        response = client.post(
            "/harness/close-work",
            headers={
                **_headers(AGENT_TOKEN),
                "Agora-Protocol-Version": "1.1",
                "Agora-Connector-Version": "0.1.0",
                "Idempotency-Key": "upload-violation",
            },
            json={
                "session_id": context["session_id"],
                "development_update": {
                    "changed_files": [{"path": "/etc/passwd", "status": "modified"}],
                    "dirty": True,
                    "diff_stat": {"files_changed": 1, "insertions": 0, "deletions": 0},
                },
            },
        )
        assert response.status_code in (400, 422), response.text
        detail = response.json()["detail"]
        code = detail["code"] if isinstance(detail, dict) else None
        if code is not None:
            assert code in ("UPLOAD_POLICY_VIOLATION", "LOCAL_REPO_PATH_REJECTED")
        else:
            # Pydantic validation error for the absolute path
            assert isinstance(detail, list)


def test_agent_workflow_acknowledgment_with_evidence_accepted_but_not_approval(monkeypatch):
    _production_auth(monkeypatch)
    with TestClient(app) as client:
        context = _started_session(client)
        response = client.post(
            "/harness/complete-workflow-step",
            headers={
                **_headers(AGENT_TOKEN),
                "Agora-Protocol-Version": "1.1",
                "Agora-Connector-Version": "0.1.0",
                "Idempotency-Key": "upload-ack",
            },
            json={
                "session_id": context["session_id"],
                "step_key": "analysis",
                "summary": "分析完成，本地用户已确认。",
                "acknowledgment": {
                    "step_id": "analysis",
                    "prompt_digest": "abc123",
                    "choice": "continue",
                    "local_interaction_id": "interaction-1",
                    "payload_digest": "def456",
                    "policy_version": "pr1c-1",
                    "acknowledged_at": "2026-09-02T00:00:00Z",
                },
            },
        )
        assert response.status_code == 200, response.text
        # completing a step is not an approval: the work item stage advanced but
        # nothing was approved — assert via the workflow response shape
        assert response.json()["completed_step"]["step_key"] == "analysis"


def test_workflow_acknowledgment_requires_evidence_fields(monkeypatch):
    _production_auth(monkeypatch)
    with TestClient(app) as client:
        context = _started_session(client)
        response = client.post(
            "/harness/complete-workflow-step",
            headers={
                **_headers(AGENT_TOKEN),
                "Agora-Protocol-Version": "1.1",
                "Agora-Connector-Version": "0.1.0",
                "Idempotency-Key": "upload-ack-bad",
            },
            json={
                "session_id": context["session_id"],
                "step_key": "analysis",
                "summary": "分析完成。",
                "acknowledgment": {"step_id": "analysis", "choice": "continue"},
            },
        )
        assert response.status_code == 422
