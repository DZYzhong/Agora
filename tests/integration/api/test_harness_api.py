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

    sessions = client.get(f"/projects/{project['id']}/sessions").json()
    assert sessions[0]["id"] == start["session_id"]
    assert sessions[0]["status"] == "closed"
    assert sessions[0]["closed_at"]
    assert sessions[0]["events"][0]["event_type"] == "development_update_captured"
    assert sessions[0]["events"][0]["payload"]["writeback_id"] == body["writeback"]["id"]

    accept_response = client.post(f"/projects/{project['id']}/writebacks/{body['writeback']['id']}/accept")
    assert accept_response.status_code == 200

    later_start = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "查询风险策略变更沉淀",
            "agent_type": "codex",
        },
    ).json()
    context = client.post(
        "/harness/plan-context",
        json={
            "session_id": later_start["session_id"],
            "query": "调整风险策略 src/risk.py pytest passed",
            "token_budget": 1200,
        },
    ).json()

    assert context["source_refs"][0]["source_uri"] == f"writebacks/{body['writeback']['id']}"
    assert "调整风险策略" in context["summary"]


def test_fetch_context_ref_returns_traceable_asset_content(tmp_path):
    client = TestClient(app)
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "README.md").write_text("# Fetch Ref\n\nReference project.", encoding="utf-8")
    (repo / "docs/ref.md").write_text("Reference detail line one.\nReference detail line two.", encoding="utf-8")
    project = client.post(
        "/projects",
        json={
            "org_id": "org_fetch_ref",
            "name": "Fetch Ref",
            "slug": "fetch-ref",
            "git_remotes": ["git@example.com:fetch-ref.git"],
        },
    ).json()
    client.post(
        f"/projects/{project['id']}/initialize-local",
        json={"repo_path": str(repo)},
    )
    assets = client.get(f"/projects/{project['id']}/assets").json()
    asset = next(asset for asset in assets if asset["source_uri"] == "docs/ref.md")
    start = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "Inspect reference details",
            "agent_type": "codex",
        },
    ).json()

    response = client.post(
        "/harness/fetch-context-ref",
        json={
            "session_id": start["session_id"],
            "asset_id": asset["id"],
            "max_tokens": 20,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["asset_id"] == asset["id"]
    assert body["title"] == "docs/ref.md"
    assert body["source_uri"] == "docs/ref.md"
    assert "Reference detail line one." in body["content"]


def test_plan_context_persists_context_pack_on_session_timeline(tmp_path):
    client = TestClient(app)
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src/service.py").write_text("Refund retry idempotency implementation.", encoding="utf-8")
    project = client.post(
        "/projects",
        json={
            "org_id": "org_context_pack",
            "name": "Context Pack",
            "slug": "context-pack",
            "git_remotes": ["git@example.com:context-pack.git"],
        },
    ).json()
    client.post(
        f"/projects/{project['id']}/initialize-local",
        json={"repo_path": str(repo)},
    )
    start = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "Implement refund retry",
            "agent_type": "codex",
        },
    ).json()

    context = client.post(
        "/harness/plan-context",
        json={
            "session_id": start["session_id"],
            "query": "refund retry idempotency",
            "token_budget": 1200,
        },
    ).json()

    sessions = client.get(f"/projects/{project['id']}/sessions").json()
    context_packs = sessions[0]["context_packs"]
    assert context_packs[0]["id"] == context["id"]
    assert context_packs[0]["level"] == context["level"]
    assert context_packs[0]["source_refs"][0]["chunk_id"]
    assert sessions[0]["events"][0]["event_type"] == "context_planned"
    assert sessions[0]["events"][0]["payload"]["context_pack_id"] == context["id"]
