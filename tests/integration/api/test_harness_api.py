from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import get_engine, get_keyword_index, get_vector_index
from apps.api.main import app
from packages.core.models import HumanConfirmationModel, WorkArtifactModel, WorkItemModel


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
    assert body["protocol_version"] == "1.0"
    assert body["request_id"] == body["session_id"]
    assert body["capabilities"]["local_repository_observation"] is True
    assert body["next_actions"][0]["type"] == "plan_context"
    assert body["session_id"]
    assert body["project"]["id"] == project["id"]
    assert body["workflow_version_id"]


def test_complete_workflow_step_advances_current_step_and_work_item_stage():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_complete_step",
            "name": "Complete Step",
            "slug": "complete-step",
            "git_remotes": [],
        },
    ).json()
    started = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "帮我做 AG-200：补充结算审计",
            "agent_type": "codex",
        },
    ).json()

    response = client.post(
        "/harness/complete-workflow-step",
        json={
            "session_id": started["session_id"],
            "step_key": "analysis",
            "summary": "已确认结算审计涉及状态流转、幂等和重试边界。",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["workflow_execution"]["current_step_key"] == "design"
    assert body["completed_step"]["step_key"] == "analysis"
    assert body["completed_step"]["status"] == "completed"
    assert body["next_step"]["step_key"] == "design"
    assert body["next_step"]["status"] == "running"
    assert body["next_actions"][0]["type"] == "prepare_context"

    work_item = client.get(f"/projects/{project['id']}/work-items/{started['work_item_id']}").json()
    assert work_item["stage"] == "design"
    assert work_item["workflow_execution"]["steps"][0]["status"] == "completed"
    assert work_item["workflow_execution"]["steps"][1]["status"] == "running"


def test_complete_workflow_step_captures_artifacts_and_human_confirmation():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_step_evidence",
            "name": "Step Evidence",
            "slug": "step-evidence",
            "git_remotes": [],
        },
    ).json()
    started = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "帮我做 AG-202：补充账单导出权限校验",
            "agent_type": "codex",
        },
    ).json()

    response = client.post(
        "/harness/complete-workflow-step",
        json={
            "session_id": started["session_id"],
            "step_key": "analysis",
            "summary": "完成权限校验任务分析。",
            "artifacts": [
                {
                    "type": "analysis_note",
                    "title": "AG-202 分析记录",
                    "content": "账单导出涉及角色权限、审计日志和批量导出限流。",
                    "metadata": {"path": "docs/tasks/AG-202/analysis.md"},
                }
            ],
            "human_confirmation": {
                "confirmation_type": "step_review",
                "decision": "approved",
                "comment": "分析范围确认，可以进入设计。",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["artifacts"][0]["type"] == "analysis_note"
    assert body["artifacts"][0]["title"] == "AG-202 分析记录"
    assert body["human_confirmation"]["decision"] == "approved"

    db = sessionmaker(bind=get_engine())()
    try:
        artifact = db.get(WorkArtifactModel, body["artifacts"][0]["id"])
        confirmation = db.get(HumanConfirmationModel, body["human_confirmation"]["id"])
        assert artifact.work_item_id == started["work_item_id"]
        assert artifact.step_key == "analysis"
        assert artifact.content == "账单导出涉及角色权限、审计日志和批量导出限流。"
        assert artifact.created_by_user_id == "auth-bypass-user"
        assert confirmation.work_item_id == started["work_item_id"]
        assert confirmation.step_key == "analysis"
        assert confirmation.confirmed_by_user_id == "auth-bypass-user"
    finally:
        db.close()


def test_complete_workflow_step_rejects_non_current_step():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_complete_step_guard",
            "name": "Complete Step Guard",
            "slug": "complete-step-guard",
            "git_remotes": [],
        },
    ).json()
    started = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "帮我做 AG-201：补充风控审计",
            "agent_type": "codex",
        },
    ).json()

    response = client.post(
        "/harness/complete-workflow-step",
        json={
            "session_id": started["session_id"],
            "step_key": "implementation",
            "summary": "尝试跳过分析设计评审。",
        },
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error"]["code"] == "WORKFLOW_STEP_NOT_CURRENT"
    assert detail["next_actions"][0]["type"] == "complete_current_workflow_step"


def test_start_work_endpoint_resolves_project_from_local_observation():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_local_observation",
            "name": "Observed API",
            "slug": "observed-api",
            "git_remotes": ["https://git.example.cn/platform/api.git"],
        },
    ).json()

    response = client.post(
        "/harness/start-work",
        json={
            "user_message": "实现 AG-128",
            "agent_type": "codex",
            "branch_name": "feature/AG-128-observed",
            "local_observation": {
                "repository": {
                    "host": "git.example.cn",
                    "path": "platform/api",
                    "normalized": "git.example.cn/platform/api",
                },
                "branch_name": "feature/AG-128-observed",
                "head_commit": "0123456789abcdef",
                "dirty": True,
                "changed_file_count": 1,
                "untracked_file_count": 1,
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["project"]["id"] == project["id"]
    assert body["protocol_version"] == "1.0"


def test_start_work_endpoint_rejects_local_paths_as_repo_remote():
    client = TestClient(app)

    response = client.post(
        "/harness/start-work",
        json={
            "user_message": "分析本地项目",
            "agent_type": "codex",
            "repo_remote": "/Users/daniel/Documents/private-repo",
        },
    )

    assert response.status_code == 422


def test_start_work_endpoint_uses_work_item_clarification_error_for_ambiguous_work():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_work_clarification",
            "name": "Payment Clarification",
            "slug": "payment-clarification",
            "git_remotes": [],
        },
    ).json()
    db = sessionmaker(bind=get_engine())()
    try:
        db.add_all(
            [
                WorkItemModel(org_id=project["org_id"], project_id=project["id"], title="支付状态流转"),
                WorkItemModel(org_id=project["org_id"], project_id=project["id"], title="支付回调重试"),
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "继续支付任务",
            "agent_type": "codex",
        },
    )

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["error"]["code"] == "WORK_ITEM_CLARIFICATION_REQUIRED"
    assert "支付状态流转" in detail["error"]["message"]
    assert detail["next_actions"][0]["type"] == "clarify"


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


def test_prepare_writeback_persists_draft_without_indexing():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_prepare_writeback",
            "name": "Prepare Writeback",
            "slug": "prepare-writeback",
            "git_remotes": [],
        },
    ).json()
    started = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "Prepare a draft",
            "agent_type": "codex",
        },
    ).json()

    response = client.post(
        "/harness/prepare-writeback",
        json={
            "session_id": started["session_id"],
            "type": "development_summary",
            "title": "Prepared draft",
            "content": "This draft must not be indexed before acceptance.",
            "asset_refs": [],
        },
    )

    assert response.status_code == 200
    draft = response.json()
    assert draft["status"] == "draft"
    stored = client.get(f"/projects/{project['id']}/writebacks").json()
    assert stored == [
        {
            "id": draft["id"],
            "project_id": project["id"],
            "type": "development_summary",
            "title": "Prepared draft",
            "content": "This draft must not be indexed before acceptance.",
            "status": "draft",
            "accepted_asset_id": None,
        }
    ]
    assert get_keyword_index().list_assets(org_id=project["org_id"], project_id=project["id"]) == []
    assert get_vector_index()._assets == []


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
    test_file = repo_path / "tests" / "test_risk.py"
    test_file.parent.mkdir()
    test_file.write_text("def test_risk_policy():\n    assert True\n", encoding="utf-8")

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
            "agent_summary": "修复迭代缺陷 AG-128：调整发布风险策略，补充回归测试。",
            "test_result": "pytest tests/test_risk.py - passed",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["writeback"]["status"] == "draft"
    assert body["writeback"]["type"] == "development_update"
    assert "src/risk.py" in body["writeback"]["content"]
    assert body["development_update"]["summary"] == "修复迭代缺陷 AG-128：调整发布风险策略，补充回归测试。"
    assert body["development_update"]["changed_files"] == [
        {"path": "src/risk.py", "status": "修改", "category": "源码"},
        {"path": "tests/test_risk.py", "status": "新增", "category": "测试"},
    ]
    assert body["development_update"]["tests"] == [
        {"command": "pytest tests/test_risk.py", "status": "passed", "raw": "pytest tests/test_risk.py - passed"}
    ]
    assert body["development_update"]["risks"] == ["未识别到明显结构性风险，仍需审核业务语义和测试充分性。"]
    assert body["development_update"]["follow_ups"] == ["请确认以上变更描述、影响文件和测试结果准确后再 Accept 入库。"]

    sessions = client.get(f"/projects/{project['id']}/sessions").json()
    assert sessions[0]["id"] == start["session_id"]
    assert sessions[0]["status"] == "closed"
    assert sessions[0]["closed_at"]
    assert sessions[0]["events"][0]["event_type"] == "development_update_captured"
    assert sessions[0]["events"][0]["payload"]["writeback_id"] == body["writeback"]["id"]
    detail = client.get(f"/projects/{project['id']}/sessions/{start['session_id']}").json()
    assert detail["development_updates"][0]["writeback_id"] == body["writeback"]["id"]
    assert detail["development_updates"][0]["summary"] == body["development_update"]["summary"]
    assert detail["development_updates"][0]["tests"][0]["status"] == "passed"

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
    assert "调整发布风险策略" in context["summary"]


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

    assert context["operation"] == "prepare_context"
    assert context["deprecation"]["legacy_endpoint"] == "/harness/plan-context"
    assert context["provisional"] is True
    sessions = client.get(f"/projects/{project['id']}/sessions").json()
    context_packs = sessions[0]["context_packs"]
    assert context_packs[0]["id"] == context["id"]
    assert context_packs[0]["level"] == context["level"]
    assert context_packs[0]["source_refs"][0]["chunk_id"]
    assert sessions[0]["events"][0]["event_type"] == "context_planned"
    assert sessions[0]["events"][0]["payload"]["context_pack_id"] == context["id"]


def test_prepare_context_endpoint_returns_budgeted_provisional_bundle(tmp_path):
    client = TestClient(app)
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src/refund.py").write_text("Refund retry idempotency implementation.", encoding="utf-8")
    project = client.post(
        "/projects",
        json={
            "org_id": "org_prepare_context",
            "name": "Prepare Context",
            "slug": "prepare-context",
            "git_remotes": ["git@example.com:prepare-context.git"],
        },
    ).json()
    client.post(f"/projects/{project['id']}/initialize-local", json={"repo_path": str(repo)})
    start = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "实现退款幂等",
            "agent_type": "codex",
        },
    ).json()

    response = client.post(
        "/harness/prepare-context",
        json={
            "session_id": start["session_id"],
            "query": "Refund retry idempotency",
            "token_budget": 700,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["operation"] == "prepare_context"
    assert body["protocol_version"] == "1.0"
    assert body["id"] == body["context_pack_id"]
    assert body["provisional"] is True
    assert body["freshness"]["repository_relation"] == "unknown"
    assert body["freshness"]["context_coverage"] != "fresh"
    assert body["freshness"]["accepted_revision_id"] is None
    assert body["freshness"]["recommended_action"] == "use_provisional_context"
    assert body["budget"]["estimated_tokens"] <= 700
    assert body["source_refs"]


def test_prepare_context_endpoint_returns_token_budget_too_small():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_tiny_budget",
            "name": "Tiny Budget",
            "slug": "tiny-budget",
            "git_remotes": [],
        },
    ).json()
    start = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "分析项目",
            "agent_type": "codex",
        },
    ).json()

    response = client.post(
        "/harness/prepare-context",
        json={
            "session_id": start["session_id"],
            "query": "anything",
            "token_budget": 5,
        },
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error"]["code"] == "TOKEN_BUDGET_TOO_SMALL"
    assert detail["next_actions"][0]["type"] == "increase_token_budget"
