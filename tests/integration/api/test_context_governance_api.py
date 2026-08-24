from fastapi.testclient import TestClient

from apps.api.main import app

HUMAN_TOKEN = "context-human-token"
AGENT_TOKEN = "context-agent-token"


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _production_auth(monkeypatch) -> None:
    monkeypatch.delenv("AGORA_TEST_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("AGORA_BOOTSTRAP_HUMAN_TOKEN", HUMAN_TOKEN)
    monkeypatch.setenv("AGORA_BOOTSTRAP_AGENT_TOKEN", AGENT_TOKEN)
    monkeypatch.setenv("AGORA_BOOTSTRAP_ORG_ID", "local-org")


def _create_project(client: TestClient) -> dict:
    response = client.post(
        "/projects",
        headers=_headers(HUMAN_TOKEN),
        json={
            "org_id": "ignored-org",
            "name": "Context Governance",
            "slug": "context-governance",
            "git_remotes": ["git@example.com:agora/context-governance.git"],
            "default_branch": "main",
        },
    )
    assert response.status_code == 201
    return response.json()


def _proposal_payload(expected_head_revision_id: str | None = None) -> dict:
    return {
        "type": "initial",
        "title": "Initial project context",
        "summary": "支付服务上下文初始版本。",
        "target_branch": "main",
        "expected_head_revision_id": expected_head_revision_id,
        "to_commit_sha": "abc123",
        "content": {
            "project_overview": "支付服务负责状态流转和审计。",
            "domains": ["payments"],
            "modules": [{"path": "src/payments/state_machine.py", "summary": "支付状态机"}],
            "risks": ["重复请求可能产生重复审计事件"],
            "test_strategy": ["状态流转单元测试"],
        },
        "source_anchors": [
            {
                "kind": "code",
                "path": "src/payments/state_machine.py",
                "start_line": 1,
                "end_line": 12,
            }
        ],
        "provenance": {
            "generating_tool": "codex",
            "schema_version": "context-revision/v1",
            "repository_commit": "abc123",
        },
    }


def test_agent_submits_context_proposal_and_human_accepts_revision(monkeypatch):
    _production_auth(monkeypatch)
    with TestClient(app) as client:
        project = _create_project(client)

        create_response = client.post(
            f"/projects/{project['id']}/context/proposals",
            headers=_headers(AGENT_TOKEN),
            json=_proposal_payload(),
        )
        assert create_response.status_code == 201
        proposal = create_response.json()
        assert proposal["status"] == "submitted"
        assert proposal["stream"]["branch"] == "main"
        assert proposal["stream"]["head_revision_id"] is None
        assert proposal["source_anchors"][0]["path"] == "src/payments/state_machine.py"

        approve_response = client.post(
            f"/projects/{project['id']}/context/proposals/{proposal['id']}/approve",
            headers=_headers(HUMAN_TOKEN),
            json={
                "expected_head_revision_id": None,
                "comment": "同意作为项目初始上下文。",
                "revision_signal": {
                    "target_branch": "main",
                    "observed_head_sha": "abc123",
                    "contains_to_commit": True,
                },
            },
        )
        assert approve_response.status_code == 200
        accepted = approve_response.json()
        assert accepted["proposal"]["status"] == "approved"
        assert accepted["revision"]["id"] == accepted["stream"]["head_revision_id"]
        assert accepted["revision"]["content"]["project_overview"] == "支付服务负责状态流转和审计。"
        assert accepted["revision"]["source_anchors"][0]["path"] == "src/payments/state_machine.py"
        assert accepted["outbox_event"]["type"] == "context_head_changed"

        streams = client.get(f"/projects/{project['id']}/context/streams", headers=_headers(HUMAN_TOKEN)).json()
        assert streams[0]["head_revision_id"] == accepted["revision"]["id"]


def test_accepting_stale_context_proposal_marks_needs_rebase(monkeypatch):
    _production_auth(monkeypatch)
    with TestClient(app) as client:
        project = _create_project(client)
        first = client.post(
            f"/projects/{project['id']}/context/proposals",
            headers=_headers(AGENT_TOKEN),
            json=_proposal_payload(),
        ).json()
        accepted = client.post(
            f"/projects/{project['id']}/context/proposals/{first['id']}/approve",
            headers=_headers(HUMAN_TOKEN),
            json={
                "expected_head_revision_id": None,
                "revision_signal": {
                    "target_branch": "main",
                    "observed_head_sha": "abc123",
                    "contains_to_commit": True,
                },
            },
        ).json()

        stale = client.post(
            f"/projects/{project['id']}/context/proposals",
            headers=_headers(AGENT_TOKEN),
            json=_proposal_payload(expected_head_revision_id=None),
        ).json()
        stale_accept = client.post(
            f"/projects/{project['id']}/context/proposals/{stale['id']}/approve",
            headers=_headers(HUMAN_TOKEN),
            json={
                "expected_head_revision_id": None,
                "revision_signal": {
                    "target_branch": "main",
                    "observed_head_sha": "abc123",
                    "contains_to_commit": True,
                },
            },
        )

        assert stale_accept.status_code == 409
        body = stale_accept.json()
        assert body["proposal"]["status"] == "needs_rebase"
        assert body["stream"]["head_revision_id"] == accepted["revision"]["id"]


def test_prepare_context_uses_accepted_revision_after_approval(monkeypatch, tmp_path):
    _production_auth(monkeypatch)
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src/payments.py").write_text("payment state machine", encoding="utf-8")
    with TestClient(app) as client:
        project = _create_project(client)
        client.post(
            f"/projects/{project['id']}/initialize-local",
            headers=_headers(HUMAN_TOKEN),
            json={"repo_path": str(repo)},
        )
        proposal = client.post(
            f"/projects/{project['id']}/context/proposals",
            headers=_headers(AGENT_TOKEN),
            json=_proposal_payload(),
        ).json()
        accepted = client.post(
            f"/projects/{project['id']}/context/proposals/{proposal['id']}/approve",
            headers=_headers(HUMAN_TOKEN),
            json={
                "expected_head_revision_id": None,
                "revision_signal": {
                    "target_branch": "main",
                    "observed_head_sha": "abc123",
                    "contains_to_commit": True,
                },
            },
        ).json()
        started = client.post(
            "/harness/start-work",
            headers=_headers(AGENT_TOKEN),
            json={
                "project_id": project["id"],
                "user_message": "帮我做 PAY-242：补充退款状态审计",
                "agent_type": "codex",
            },
        ).json()

        bundle = client.post(
            "/harness/prepare-context",
            headers=_headers(AGENT_TOKEN),
            json={
                "session_id": started["session_id"],
                "query": "退款状态审计",
                "token_budget": 1400,
            },
        ).json()

        assert bundle["provisional"] is False
        assert bundle["freshness"]["context_coverage"] == "fresh"
        assert bundle["freshness"]["accepted_revision_id"] == accepted["revision"]["id"]
        assert bundle["capability_pins"]["context_revision_id"] == accepted["revision"]["id"]
