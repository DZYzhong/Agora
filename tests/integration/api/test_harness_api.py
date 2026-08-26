from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import get_engine, get_keyword_index, get_vector_index
from apps.api.main import app
from packages.core.models import HumanConfirmationModel, QualityEvidenceModel, WorkArtifactModel, WorkItemModel


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
    assert body["capabilities"]["quality_evidence"] is True


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


def test_record_evidence_and_quality_status_preserve_failed_test_fact():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_quality_status",
            "name": "Quality Status",
            "slug": "quality-status",
            "git_remotes": [],
        },
    ).json()
    started = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "帮我做 AG-801：修复支付回调重试",
            "agent_type": "codex",
        },
    ).json()

    response = client.post(
        "/harness/record-evidence",
        json={
            "session_id": started["session_id"],
            "evidence_type": "local_test",
            "source": "ai_tool",
            "status": "failed",
            "conclusion": "pytest failed: 回调幂等测试失败，不能发布。",
            "command": ".venv/bin/pytest tests/payment/test_callback_retry.py",
            "output_summary": "1 failed: duplicate callback created two settlement records.",
            "raw_ref": "local://pytest/payment-callback-retry",
            "metadata": {"commit_sha": "abc123", "coverage": "not_collected"},
        },
    )

    assert response.status_code == 201
    evidence = response.json()["evidence"]
    assert evidence["work_item_id"] == started["work_item_id"]
    assert evidence["status"] == "failed"
    assert evidence["classification"] == "evidence"

    quality = client.post(
        "/harness/get-quality-status",
        json={
            "session_id": started["session_id"],
            "scope": "work_item",
        },
    ).json()

    assert quality["operation"] == "get_quality_status"
    assert quality["quality_state"] == "failing"
    assert quality["counts"]["failed"] == 1
    assert quality["counts"]["passed"] == 0
    assert quality["unverified_claims"] == []
    assert quality["evidence"][0]["id"] == evidence["id"]
    assert quality["evidence"][0]["command"] == ".venv/bin/pytest tests/payment/test_callback_retry.py"

    db = sessionmaker(bind=get_engine())()
    try:
        stored = db.get(QualityEvidenceModel, evidence["id"])
        assert stored.work_item_id == started["work_item_id"]
        assert stored.session_id == started["session_id"]
        assert stored.status == "failed"
    finally:
        db.close()


def test_quality_status_reports_missing_evidence_as_unverified_not_passed():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_quality_missing",
            "name": "Quality Missing",
            "slug": "quality-missing",
            "git_remotes": [],
        },
    ).json()
    started = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "帮我做 AG-802：调整订单状态流转",
            "agent_type": "codex",
        },
    ).json()

    quality = client.post(
        "/harness/get-quality-status",
        json={
            "session_id": started["session_id"],
            "scope": "work_item",
        },
    ).json()

    assert quality["quality_state"] == "unverified"
    assert quality["counts"] == {"passed": 0, "failed": 0, "warning": 0, "unknown": 0}
    assert quality["gaps"][0]["code"] == "NO_QUALITY_EVIDENCE"
    assert quality["unverified_claims"] == [
        {
            "claim": "No passing tests or CI evidence has been recorded for this scope.",
            "reason": "Agora does not infer passed quality from AI summaries or workflow progress.",
        }
    ]


def test_project_status_aggregates_work_items_quality_and_pending_approvals():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_project_status",
            "name": "Project Status",
            "slug": "project-status",
            "git_remotes": [],
        },
    ).json()
    passing = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "帮我做 AG-803：发布账单导出",
            "agent_type": "codex",
        },
    ).json()
    failing = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "帮我做 AG-804：修复退款回调",
            "agent_type": "codex",
        },
    ).json()
    client.post(
        "/harness/record-evidence",
        json={
            "session_id": passing["session_id"],
            "evidence_type": "local_test",
            "source": "ai_tool",
            "status": "passed",
            "conclusion": "账单导出相关测试通过。",
            "command": "pytest tests/billing",
            "output_summary": "12 passed",
        },
    )
    client.post(
        "/harness/record-evidence",
        json={
            "session_id": failing["session_id"],
            "evidence_type": "local_test",
            "source": "ai_tool",
            "status": "failed",
            "conclusion": "退款回调幂等测试失败。",
            "command": "pytest tests/refund",
            "output_summary": "1 failed",
        },
    )
    client.post(
        "/harness/submit-skill-candidate",
        json={
            "session_id": passing["session_id"],
            "slug": "billing-release-review",
            "name": "Billing Release Review",
            "summary": "沉淀账单发布检查经验。",
            "triggers": ["billing", "release"],
            "instructions": "检查账单发布风险。",
            "artifact_ids": [],
        },
    )

    status = client.post(
        "/harness/get-project-status",
        json={
            "project_id": project["id"],
        },
    ).json()

    assert status["operation"] == "get_project_status"
    assert status["project"]["id"] == project["id"]
    assert status["work_item_counts"]["total"] == 2
    assert status["delivery_readiness"]["state"] == "blocked"
    assert status["quality_dimensions"]["local_test"]["passed"] == 1
    assert status["quality_dimensions"]["local_test"]["failed"] == 1
    assert status["quality_counts"]["passing"] == 1
    assert status["quality_counts"]["failing"] == 1
    assert status["pending_approvals"]["skill_candidates"] == 1
    assert {item["quality_state"] for item in status["work_items"]} == {"passing", "failing"}
    failing_item = next(item for item in status["work_items"] if item["quality_state"] == "failing")
    assert failing_item["quality_evidence"][0]["status"] == "failed"
    assert failing_item["quality_evidence"][0]["classification"] == "evidence"
    assert status["blockers"] == [
        {
            "code": "FAILING_QUALITY_EVIDENCE",
            "severity": "high",
            "work_item_id": failing_item["id"],
            "work_item_title": failing_item["title"],
            "reason": "At least one failed quality evidence record exists.",
        }
    ]


def test_submit_skill_candidate_from_work_session_creates_reviewable_project_skill():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_skill_candidate_from_ai",
            "name": "Skill Candidate From AI",
            "slug": "skill-candidate-from-ai",
            "git_remotes": [],
        },
    ).json()
    started = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "帮我做 AG-601：补充发布风险检查",
            "agent_type": "codex",
        },
    ).json()
    completed = client.post(
        "/harness/complete-workflow-step",
        json={
            "session_id": started["session_id"],
            "step_key": "analysis",
            "summary": "完成发布风险检查经验总结。",
            "artifacts": [
                {
                    "type": "analysis_note",
                    "title": "AG-601 风险检查经验",
                    "content": "发布前必须检查回滚方案、测试证据和配置开关。",
                    "metadata": {"path": "docs/tasks/AG-601/analysis.md"},
                }
            ],
        },
    ).json()

    response = client.post(
        "/harness/submit-skill-candidate",
        json={
            "session_id": started["session_id"],
            "slug": "release-risk-review",
            "name": "Release Risk Review",
            "summary": "把发布风险检查经验沉淀成团队 skill。",
            "triggers": ["release", "risk", "rollback"],
            "instructions": "检查回滚方案、测试证据、配置开关和风险说明。",
            "artifact_ids": [completed["artifacts"][0]["id"]],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["operation"] == "submit_skill_candidate"
    assert body["skill"]["status"] == "candidate"
    assert body["skill"]["definition"]["source"] == "ai_tool_submission"
    assert body["skill"]["definition"]["work_item_id"] == started["work_item_id"]
    assert body["skill"]["definition"]["evidence_artifact_ids"] == [completed["artifacts"][0]["id"]]
    assert body["next_actions"][0]["type"] == "human_review_skill_candidate"

    skills = client.get(f"/projects/{project['id']}/skills").json()
    candidate = next(skill for skill in skills if skill["id"] == body["skill"]["id"])
    assert candidate["status"] == "candidate"
    assert candidate["evidence_refs"][0]["title"] == "AG-601 风险检查经验"


def test_prepare_context_returns_applicable_approved_skill_versions_for_ai_tool():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_prepare_context_skills",
            "name": "Prepare Context Skills",
            "slug": "prepare-context-skills",
            "git_remotes": [],
        },
    ).json()
    skill = client.post(
        f"/projects/{project['id']}/skills",
        json={
            "slug": "release-readiness-review",
            "name": "Release Readiness Review",
            "status": "candidate",
            "definition": {
                "version": "1.0.0",
                "summary": "发布前检查团队标准流程。",
                "triggers": ["release", "rollback"],
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "instructions": "检查风险说明、测试证据、回滚方案、监控和负责人。",
                "risk_constraints": ["缺少测试证据时必须标记为风险"],
            },
        },
    ).json()
    approved = client.post(f"/projects/{project['id']}/skills/{skill['id']}/approve").json()
    other = client.post(
        f"/projects/{project['id']}/skills",
        json={
            "slug": "database-migration-review",
            "name": "Database Migration Review",
            "status": "candidate",
            "definition": {
                "version": "1.0.0",
                "triggers": ["migration"],
                "instructions": "检查数据库迁移。",
            },
        },
    ).json()
    client.post(f"/projects/{project['id']}/skills/{other['id']}/approve")
    started = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "帮我做 AG-702：准备 release 回滚风险检查",
            "agent_type": "codex",
        },
    ).json()

    response = client.post(
        "/harness/prepare-context",
        json={
            "session_id": started["session_id"],
            "query": "release 回滚风险检查",
            "token_budget": 2200,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["operation"] == "prepare_context"
    assert body["capability_pins"]["skill_version_ids"] == [approved["current_version"]["id"]]
    assert body["capability_pins"]["skill_version_id"] == approved["current_version"]["id"]
    assert [skill["slug"] for skill in body["skills"]] == ["release-readiness-review"]
    assert body["skills"][0]["version"] == "1.0.0"
    assert body["skills"][0]["instructions"] == "检查风险说明、测试证据、回滚方案、监控和负责人。"
    assert body["skills"][0]["risk_constraints"] == ["缺少测试证据时必须标记为风险"]


def test_submit_skill_candidate_merges_duplicate_slug_into_existing_candidate():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_skill_candidate_dedupe",
            "name": "Skill Candidate Dedupe",
            "slug": "skill-candidate-dedupe",
            "git_remotes": [],
        },
    ).json()
    started = client.post(
        "/harness/start-work",
        json={
            "project_id": project["id"],
            "user_message": "帮我做 AG-703：沉淀发布风险检查",
            "agent_type": "codex",
        },
    ).json()
    first_artifact = client.post(
        "/harness/complete-workflow-step",
        json={
            "session_id": started["session_id"],
            "step_key": "analysis",
            "summary": "第一次发布风险检查经验。",
            "artifacts": [
                {
                    "type": "analysis_note",
                    "title": "AG-703 发布风险检查",
                    "content": "发布风险检查要覆盖测试证据和回滚方案。",
                }
            ],
        },
    ).json()["artifacts"][0]
    first = client.post(
        "/harness/submit-skill-candidate",
        json={
            "session_id": started["session_id"],
            "slug": "release-risk-review",
            "name": "Release Risk Review",
            "summary": "第一次提交。",
            "triggers": ["release", "risk"],
            "instructions": "检查发布风险。",
            "artifact_ids": [first_artifact["id"]],
        },
    ).json()
    second = client.post(
        "/harness/submit-skill-candidate",
        json={
            "session_id": started["session_id"],
            "slug": "release-risk-review",
            "name": "Release Risk Review",
            "summary": "第二次提交补充回滚要求。",
            "triggers": ["release", "rollback"],
            "instructions": "检查发布风险和回滚方案。",
            "artifact_ids": [first_artifact["id"], "extra-artifact-id"],
        },
    )

    assert second.status_code == 201
    body = second.json()
    assert body["skill"]["id"] == first["skill"]["id"]
    assert body["deduplicated"] is True
    assert body["next_actions"][0]["type"] == "human_review_skill_candidate"
    assert body["skill"]["definition"]["triggers"] == ["release", "risk", "rollback"]
    assert body["skill"]["definition"]["evidence_artifact_ids"] == [first_artifact["id"], "extra-artifact-id"]

    skills = [skill for skill in client.get(f"/projects/{project['id']}/skills").json() if skill["slug"] == "release-risk-review"]
    assert len(skills) == 1


def test_ai_tool_gets_repeated_experience_skill_suggestions_from_work_artifacts():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={
            "org_id": "org_skill_suggestions",
            "name": "Skill Suggestions",
            "slug": "skill-suggestions",
            "git_remotes": [],
        },
    ).json()
    artifact_ids = []
    for task_id, title in [
        ("AG-704", "发布风险检查分析"),
        ("AG-705", "发布风险检查复盘"),
    ]:
        started = client.post(
            "/harness/start-work",
            json={
                "project_id": project["id"],
                "user_message": f"帮我做 {task_id}：发布风险检查",
                "agent_type": "codex",
            },
        ).json()
        completed = client.post(
            "/harness/complete-workflow-step",
            json={
                "session_id": started["session_id"],
                "step_key": "analysis",
                "summary": f"{task_id} 完成发布风险检查经验记录。",
                "artifacts": [
                    {
                        "type": "analysis_note",
                        "title": title,
                        "content": "发布前需要检查测试证据、回滚方案、配置开关和监控负责人。",
                    }
                ],
            },
        ).json()
        artifact_ids.append(completed["artifacts"][0]["id"])
        last_session_id = started["session_id"]

    response = client.post(
        "/harness/suggest-skills",
        json={
            "session_id": last_session_id,
            "query": "发布风险检查",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["operation"] == "suggest_skills"
    assert body["suggestions"][0]["slug"] == "release-risk-review"
    assert body["suggestions"][0]["name"] == "Release Risk Review"
    assert body["suggestions"][0]["evidence_artifact_ids"] == artifact_ids
    assert body["suggestions"][0]["reason"] == "Repeated project experience appeared in 2 work artifacts."
    assert body["next_actions"][0]["type"] == "submit_skill_candidate"


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
