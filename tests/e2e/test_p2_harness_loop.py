from fastapi.testclient import TestClient

from apps.api.main import app
from apps.mcp.server import list_tools

HUMAN_TOKEN = "p2-human-token"
AGENT_TOKEN = "p2-agent-token"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_p2_canonical_harness_loop_uses_authenticated_public_operations(monkeypatch, tmp_path):
    monkeypatch.delenv("AGORA_TEST_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("AGORA_BOOTSTRAP_HUMAN_TOKEN", HUMAN_TOKEN)
    monkeypatch.setenv("AGORA_BOOTSTRAP_AGENT_TOKEN", AGENT_TOKEN)
    monkeypatch.setenv("AGORA_BOOTSTRAP_ORG_ID", "org_p2_loop")

    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "refund.py").write_text("Refund retry idempotency and rollback evidence.", encoding="utf-8")

    with TestClient(app) as client:
        missing_auth = client.post(
            "/harness/start-work",
            json={"user_message": "实现退款重试", "agent_type": "codex"},
        )
        assert missing_auth.status_code == 401
        assert missing_auth.json()["detail"]["code"] == "AUTH_REQUIRED"

        project = client.post(
            "/projects",
            headers=_auth(HUMAN_TOKEN),
            json={
                "org_id": "attacker_org_is_ignored",
                "name": "P2 Harness Loop",
                "slug": "p2-harness-loop",
                "git_remotes": ["https://git.example.cn/team/p2-harness-loop.git"],
            },
        ).json()
        assert project["org_id"] == "org_p2_loop"
        client.post(
            f"/projects/{project['id']}/initialize-local",
            headers=_auth(HUMAN_TOKEN),
            json={"repo_path": str(repo)},
        )

        payload = {
            "user_message": "实现 AG-200 退款重试幂等",
            "agent_type": "codex",
            "local_observation": {
                "repository": {
                    "host": "git.example.cn",
                    "path": "team/p2-harness-loop",
                    "normalized": "git.example.cn/team/p2-harness-loop",
                },
                "branch_name": "feature/AG-200-refund-retry",
                "head_commit": "0123456789abcdef",
                "dirty": False,
                "changed_file_count": 0,
                "untracked_file_count": 0,
            },
        }
        first = client.post(
            "/harness/start-work",
            headers={**_auth(AGENT_TOKEN), "Idempotency-Key": "p2-loop-start"},
            json=payload,
        )
        replay = client.post(
            "/harness/start-work",
            headers={**_auth(AGENT_TOKEN), "Idempotency-Key": "p2-loop-start"},
            json=payload,
        )
        assert first.status_code == 200
        assert replay.json()["session_id"] == first.json()["session_id"]
        started = first.json()
        assert started["protocol_version"] == "1.0"
        assert started["task_id"] == "AG-200"

        context = client.post(
            "/harness/prepare-context",
            headers=_auth(AGENT_TOKEN),
            json={
                "session_id": started["session_id"],
                "query": "refund retry idempotency rollback",
                "token_budget": 800,
            },
        )
        assert context.status_code == 200
        bundle = context.json()
        assert bundle["operation"] == "prepare_context"
        assert bundle["provisional"] is True
        assert bundle["budget"]["estimated_tokens"] <= 800
        assert bundle["freshness"]["context_coverage"] != "fresh"

        source = client.post(
            "/harness/fetch-context-ref",
            headers=_auth(AGENT_TOKEN),
            json={
                "session_id": started["session_id"],
                "asset_id": bundle["source_refs"][0]["asset_id"],
                "max_tokens": 80,
            },
        )
        assert source.status_code == 200
        assert "Refund retry" in source.json()["content"]

        close = client.post(
            "/harness/close-work",
            headers=_auth(AGENT_TOKEN),
            json={
                "session_id": started["session_id"],
                "status": "closed",
                "agent_summary": "完成 AG-200 退款重试幂等处理。",
                "test_result": "pytest tests/refund - passed",
            },
        )
        assert close.status_code == 200
        assert close.json()["status"] == "closed"

        sessions = client.get(f"/projects/{project['id']}/sessions", headers=_auth(HUMAN_TOKEN)).json()
        assert sessions[0]["status"] == "closed"
        assert [event["event_type"] for event in sessions[0]["events"]] == [
            "context_prepared",
            "development_update_captured",
        ]
