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
    assert "Delivery readiness" in content
    assert "Blockers" in content
    assert "Latest evidence" in content
    assert "Task links" in content
    assert "task_links" in content
    assert "delivery_readiness" in content
    assert "quality_state" in content


def test_p9_operations_summary_page_is_available_and_linked_from_project_home():
    operations_page = Path("apps/web/app/projects/[projectId]/operations/page.tsx")
    project_page = Path("apps/web/app/projects/[projectId]/page.tsx").read_text()

    assert operations_page.exists()
    content = operations_page.read_text()
    assert "/operations" in project_page
    assert "Operations summary" in content
    assert "operations-summary" in content
    assert "Context governance" in content
    assert "Quality evidence" in content
    assert "Repository signals" in content
    assert "Security audit" in content


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


def test_p6_quality_project_status_blackbox_guide_exists():
    guide = Path("docs/development/p6-quality-project-status-blackbox.zh-CN.md")
    content = guide.read_text()

    assert "P6 Quality and Project Status 黑盒验证步骤" in content
    assert "agora_record_evidence" in content
    assert "agora_get_quality_status" in content
    assert "agora_get_project_status" in content
    assert "Delivery readiness" in content
    assert "FAILING_QUALITY_EVIDENCE" in content
    assert "用户不需要手动调用任何 HTTP API" in content
    assert "agora_prepare_context" in content
    assert "capability_pins.skill_version_ids" in content
    assert "用户不需要手动调用任何 HTTP API" in content


def test_p7_security_audit_page_is_available_and_linked_from_project_home():
    security_page = Path("apps/web/app/projects/[projectId]/security/page.tsx")
    project_page = Path("apps/web/app/projects/[projectId]/page.tsx").read_text()

    assert security_page.exists()
    content = security_page.read_text()
    assert "/security" in project_page
    assert "Security audit" in content
    assert "actor_credential_kind" in content
    assert "decision" in content
    assert "reason" in content


def test_p7_governance_security_blackbox_guide_exists():
    guide = Path("docs/development/p7-governance-security-blackbox.zh-CN.md")
    content = guide.read_text()

    assert "P7 Governance and Security 黑盒验证步骤" in content
    assert "HUMAN_CREDENTIAL_REQUIRED" in content
    assert "PROJECT_ROLE_REQUIRED" in content
    assert "Security audit" in content
    assert "AI 凭证不能审批" in content


def test_p8_ci_quality_signal_blackbox_guide_exists():
    guide = Path("docs/development/p8-ci-quality-signal-blackbox.zh-CN.md")
    content = guide.read_text()

    assert "P8 CI QualitySignal 黑盒验证步骤" in content
    assert "AGORA_BOOTSTRAP_CI_TOKEN" in content
    assert "/integrations/ci/quality-signal" in content
    assert "/integrations/repository/revision-signal" in content
    assert "/integrations/repository/pull-request-signal" in content
    assert "task_provider" in content
    assert "task_url" in content
    assert "WorkItem mapping" in content
    assert "PR/MR" in content
    assert "ContextProposal" in content
    assert "CI_CREDENTIAL_REQUIRED" in content
    assert "Project status" in content
    assert "用户不需要手动调用 HTTP API" in content


def test_p9_operations_blackbox_guide_exists():
    guide = Path("docs/development/p9-operations-readiness-blackbox.zh-CN.md")
    content = guide.read_text()

    assert "P9 Production and Operations Readiness 黑盒验证步骤" in content
    assert "/ready" in content
    assert "/metrics" in content
    assert "X-Request-ID" in content
    assert "AGORA_DATABASE_URL" in content
    assert "PostgreSQL" in content
    assert "备份" in content
    assert "恢复" in content
    assert "export-project" in content
    assert "project-summary" in content
    assert "outbox-summary" in content
    assert "retention-summary" in content
    assert "cleanup-retention" in content
    assert "agora_outbox_events_total" in content
    assert "agora_outbox_retryable_total" in content
    assert "Operations summary" in content
    assert "operations-summary" in content
    assert "scripts.agora_admin smoke" in content
    assert "manifest.json" in content
    assert "JSONL" in content
    assert "Developer" in content
    assert "Reviewer" in content
    assert "Project Manager" in content
    assert "Quality" in content


def test_p9_container_runtime_assets_exist():
    api_dockerfile = Path("infra/Dockerfile.api")
    web_dockerfile = Path("infra/Dockerfile.web")
    connector_dockerfile = Path("infra/Dockerfile.local-connector")
    compose = Path("infra/docker-compose.yml").read_text()
    env_example = Path(".env.example").read_text()

    assert api_dockerfile.exists()
    assert web_dockerfile.exists()
    assert connector_dockerfile.exists()
    assert "uvicorn" in api_dockerfile.read_text()
    assert "npm run build" in web_dockerfile.read_text()
    assert "python -m apps.mcp.server" in connector_dockerfile.read_text()
    assert "api:" in compose
    assert "web:" in compose
    assert "local-connector:" in compose
    assert "healthcheck:" in compose
    assert "http://127.0.0.1:8000/ready" in compose
    assert "AGORA_BOOTSTRAP_CI_TOKEN" in env_example
    assert "AGORA_ENV=production-like" in env_example
