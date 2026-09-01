from fastapi.testclient import TestClient
import shutil
import subprocess

from apps.api.main import app


def test_api_p0_usable_loop_initializes_assets_plans_context_and_accepts_writeback(
    authenticated_client,
    local_init_root,
):
    repo = local_init_root / "sample_repo"
    shutil.copytree("tests/fixtures/sample_repo", repo)
    client = authenticated_client
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
        json={"repo_path": str(repo)},
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
    accepted_asset_id = accept_response.json()["accepted_asset_id"]

    writebacks_response = client.get(f"/projects/{project['id']}/writebacks")
    assert writebacks_response.status_code == 200
    accepted_writeback = next(writeback for writeback in writebacks_response.json() if writeback["id"] == writeback_id)
    assert accepted_writeback["accepted_asset_id"] == accepted_asset_id

    later_context = client.post(
        "/harness/plan-context",
        json={"session_id": session_id, "query": "退款失败重试 幂等", "token_budget": 1000},
    ).json()
    assert "幂等" in later_context["summary"]


def test_initialize_local_clones_project_remote_when_repo_path_is_missing(
    authenticated_client, local_init_root
):
    source_repo = local_init_root / "source_repo"
    shutil.copytree("tests/fixtures/sample_repo", source_repo)
    subprocess.run(["git", "init"], cwd=source_repo, check=True)
    subprocess.run(["git", "add", "."], cwd=source_repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Agora Test", "-c", "user.email=agora@example.com", "commit", "-m", "fixture"],
        cwd=source_repo,
        check=True,
    )

    target_repo = local_init_root / "cloned_repo"
    client = authenticated_client
    project = client.post(
        "/projects",
        json={
            "org_id": "org_clone",
            "name": "Payment Clone",
            "slug": "payment-clone",
            "git_remotes": [str(source_repo)],
        },
    ).json()

    init_response = client.post(
        f"/projects/{project['id']}/initialize-local",
        json={"repo_path": str(target_repo)},
    )

    assert init_response.status_code == 200
    assert init_response.json()["asset_count"] > 0
    assert target_repo.exists()
    assert (target_repo / "README.md").exists()


def test_initialize_local_requires_git_remote_when_repo_path_is_missing(
    authenticated_client, local_init_root
):
    client = authenticated_client
    project = client.post(
        "/projects",
        json={
            "org_id": "org_no_remote",
            "name": "No Remote",
            "slug": "no-remote",
            "git_remotes": [],
        },
    ).json()

    init_response = client.post(
        f"/projects/{project['id']}/initialize-local",
        json={"repo_path": str(local_init_root / "missing_repo")},
    )

    assert init_response.status_code == 400
    assert "no Git remote" in init_response.json()["detail"]
