from pathlib import Path


def test_next_dev_and_build_use_separate_dist_dirs():
    config_path = Path("apps/web/next.config.mjs")
    config = config_path.read_text()

    assert "process.env.NODE_ENV === \"development\"" in config
    assert "\".next-dev\"" in config
    assert "\".next\"" in config


def test_server_fetches_attach_configured_human_token():
    api_path = Path("apps/web/lib/api.ts")
    api = api_path.read_text()

    assert "AGORA_WEB_HUMAN_TOKEN" in api
    assert "Authorization" in api
    assert "Bearer" in api


def test_session_pages_render_work_item_details():
    list_page = Path("apps/web/app/projects/[projectId]/sessions/page.tsx").read_text()
    detail_page = Path("apps/web/app/projects/[projectId]/sessions/[sessionId]/page.tsx").read_text()

    assert "work_item" in list_page
    assert "Work item" in list_page
    assert "work_item" in detail_page
    assert "Work item" in detail_page


def test_product_context_page_is_read_only_audit_view():
    context_page = Path("apps/web/app/projects/[projectId]/context/page.tsx").read_text()

    assert "Context state" in context_page
    assert "Context streams" in context_page
    assert "Context proposals" in context_page
    assert "/context/proposals/" in context_page
    assert "Context Tester" not in context_page
    assert "Run context query" not in context_page
    assert "/harness/plan-context" not in context_page
    assert "/harness/start-work" not in context_page


def test_context_proposal_review_pages_are_available():
    detail_page = Path("apps/web/app/projects/[projectId]/context/proposals/[proposalId]/page.tsx")
    approve_route = Path("apps/web/app/projects/[projectId]/context/proposals/[proposalId]/approve/route.ts")

    assert detail_page.exists()
    assert approve_route.exists()

    detail = detail_page.read_text()
    route = approve_route.read_text()
    assert "Revision signal" in detail
    assert "observed_head_sha" in detail
    assert "contains_to_commit" in detail
    assert "merge_target_branch" in detail
    assert "merged_to_target" in detail
    assert "source_anchors" in detail
    assert "/approve" in detail
    assert "/context/proposals" in route
    assert "/approve" in route


def test_web_does_not_ship_agent_simulation_routes():
    assert not Path("apps/web/app/projects/[projectId]/context/submit/route.ts").exists()
    assert not Path("apps/web/app/projects/[projectId]/development-capture/route.ts").exists()


def test_work_item_pages_are_available_and_linked_from_project_home():
    list_page = Path("apps/web/app/projects/[projectId]/work-items/page.tsx")
    detail_page = Path("apps/web/app/projects/[projectId]/work-items/[workItemId]/page.tsx")
    project_page = Path("apps/web/app/projects/[projectId]/page.tsx").read_text()

    assert list_page.exists()
    assert detail_page.exists()
    assert "/work-items" in project_page


def test_project_status_page_is_available_and_linked_from_project_home():
    status_page = Path("apps/web/app/projects/[projectId]/status/page.tsx")
    project_page = Path("apps/web/app/projects/[projectId]/page.tsx").read_text()

    assert status_page.exists()
    content = status_page.read_text()
    assert "/status" in project_page
    assert "Project status" in content
    assert "Quality evidence" in content
    assert "Pending approvals" in content
    assert "quality_state" in content


def test_work_item_detail_page_renders_workflow_audit_evidence():
    detail_page = Path("apps/web/app/projects/[projectId]/work-items/[workItemId]/page.tsx").read_text()

    assert "Workflow audit" in detail_page
    assert "Step outputs" in detail_page
    assert "Human confirmations" in detail_page
    assert "workflow_execution" in detail_page
    assert "human_confirmations" in detail_page


def test_p4_workflow_audit_blackbox_guide_exists():
    guide = Path("docs/development/p4-workflow-audit-blackbox.zh-CN.md")
    content = guide.read_text()

    assert "P4 Workflow Audit 黑盒验证步骤" in content
    assert "agora_start_work" in content
    assert "agora_complete_workflow_step" in content
    assert "Workflow audit" in content
    assert "WORKFLOW_STEP_NOT_CURRENT" in content
    assert "用户只通过 AI 工具和 Web 页面完成验证" in content


def test_skills_page_renders_current_skill_version():
    skills_page = Path("apps/web/app/projects/[projectId]/skills/page.tsx").read_text()

    assert "Current version" in skills_page
    assert "current_version" in skills_page


def test_p5_skill_governance_blackbox_guide_exists():
    guide = Path("docs/development/p5-skill-governance-blackbox.zh-CN.md")
    content = guide.read_text()

    assert "P5 Skill Governance 黑盒验证步骤" in content
    assert "agora_suggest_skills" in content
    assert "agora_submit_skill_candidate" in content
    assert "deduplicated = true" in content
    assert "Publish approved version" in content
    assert "agora_prepare_context" in content
    assert "capability_pins.skill_version_ids" in content
    assert "用户不需要手动调用任何 HTTP API" in content
