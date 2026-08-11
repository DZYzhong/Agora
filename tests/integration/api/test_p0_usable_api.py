from fastapi.testclient import TestClient

from apps.api.main import app


def test_api_p0_usable_loop_initializes_assets_plans_context_and_accepts_writeback():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_usable",
            "name": "Payment Usable",
            "slug": "payment-usable",
            "git_remotes": ["git@example.com:payment-usable.git"],
        },
    ).json()

    init_response = client.post(
        f"/projects/{project['id']}/initialize-local",
        json={"repo_path": "tests/fixtures/sample_repo"},
    )

    assert init_response.status_code == 200
    assert init_response.json()["asset_count"] > 0

    assets_response = client.get(f"/projects/{project['id']}/assets")
    assert assets_response.status_code == 200
    assert any(asset["title"] == "README.md" for asset in assets_response.json())

    start_response = client.post(
        "/harness/start-work",
        json={
            "user_message": "分析如何实现退款失败重试",
            "repo_remote": "git@example.com:payment-usable.git",
            "agent_type": "codex",
        },
    )
    assert start_response.status_code == 200
    session_id = start_response.json()["session_id"]

    context_response = client.post(
        "/harness/plan-context",
        json={"session_id": session_id, "query": "退款失败重试", "token_budget": 1000},
    )

    assert context_response.status_code == 200
    assert context_response.json()["source_refs"]

    writeback_response = client.post(
        "/harness/prepare-writeback",
        json={
            "session_id": session_id,
            "type": "development_summary",
            "title": "退款失败重试总结",
            "content": "退款失败重试需要限制次数并保持幂等。",
        },
    )
    assert writeback_response.status_code == 200
    writeback_id = writeback_response.json()["id"]

    accept_response = client.post(f"/projects/{project['id']}/writebacks/{writeback_id}/accept")
    assert accept_response.status_code == 200
    assert accept_response.json()["status"] == "accepted"

    later_context = client.post(
        "/harness/plan-context",
        json={"session_id": session_id, "query": "退款失败重试 幂等", "token_budget": 1000},
    ).json()
    assert "幂等" in later_context["summary"]
