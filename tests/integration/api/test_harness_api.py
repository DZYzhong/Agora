from fastapi.testclient import TestClient

from apps.api.main import app


def _run_git(repo_path, *args):
    import subprocess

    subprocess.run(["git", *args], cwd=repo_path, check=True, capture_output=True, text=True)


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


def test_close_work_endpoint_can_prepare_development_update_from_repo_diff(tmp_path):
    client = TestClient(app)
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    _run_git(repo_path, "init")
    _run_git(repo_path, "config", "user.email", "dev@example.com")
    _run_git(repo_path, "config", "user.name", "Dev")
    source = repo_path / "src" / "risk.py"
    source.parent.mkdir()
    source.write_text("RISK = 'old'\n", encoding="utf-8")
    _run_git(repo_path, "add", ".")
    _run_git(repo_path, "commit", "-m", "initial")
    source.write_text("RISK = 'new'\n", encoding="utf-8")

    project = client.post(
        "/projects",
        json={
            "org_id": "org_1",
            "name": "Risk",
            "slug": "risk",
            "git_remotes": ["git@example.com:risk.git"],
        },
    ).json()
    start = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "调整风险策略",
            "agent_type": "codex",
        },
    ).json()

    response = client.post(
        "/harness/close-work",
        json={
            "session_id": start["session_id"],
            "status": "closed",
            "repo_path": str(repo_path),
            "agent_summary": "调整风险策略",
            "test_result": "pytest passed",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["writeback"]["status"] == "draft"
    assert body["writeback"]["type"] == "development_update"
    assert "src/risk.py" in body["writeback"]["content"]
