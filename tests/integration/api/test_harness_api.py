from fastapi.testclient import TestClient

from apps.api.main import app


def test_start_work_endpoint_returns_session():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_1",
            "name": "Payment",
            "slug": "payment",
            "git_remotes": ["git@example.com:payment.git"],
        },
    ).json()

    response = client.post(
        "/harness/start-work",
        json={
            "user_message": "帮我做 AG-128",
            "repo_remote": "git@example.com:payment.git",
            "agent_type": "codex",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"]
    assert body["project"]["id"] == project["id"]


def test_start_work_endpoint_can_resolve_exact_project_id_when_remotes_repeat():
    client = TestClient(app)
    first = client.post(
        "/projects",
        json={
            "org_id": "org_1",
            "name": "First Payment",
            "slug": "first-payment",
            "git_remotes": ["git@example.com:shared-payment.git"],
        },
    ).json()
    client.post(
        "/projects",
        json={
            "org_id": "org_1",
            "name": "Second Payment",
            "slug": "second-payment",
            "git_remotes": ["git@example.com:shared-payment.git"],
        },
    )

    response = client.post(
        "/harness/start-work",
        json={
            "project_id": first["id"],
            "user_message": "分析这个项目",
            "repo_remote": "git@example.com:shared-payment.git",
            "agent_type": "web-context-tester",
        },
    )

    assert response.status_code == 200
    assert response.json()["project"]["id"] == first["id"]
