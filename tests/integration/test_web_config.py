import re
from pathlib import Path

import pytest
import yaml

from packages.core.settings import SUPPORTED_ENVIRONMENTS


DOTENV_ENV_PATTERN = re.compile(r"^AGORA_ENV=([^\s#]+)\s*$", re.MULTILINE)
EXPORT_ENV_PATTERN = re.compile(r"^export AGORA_ENV=([^\s#]+)\s*$", re.MULTILINE)
EDITABLE_INSTALL_PATTERN = re.compile(r"^\.venv/bin/pip install -e (\S+)\s*$", re.MULTILINE)
UNRESOLVED_COMPOSE_ENVIRONMENT = "<unresolved>"


def _compose_service_environment_values(compose: str) -> dict[str, list[str]]:
    document = yaml.safe_load(compose) or {}
    if not isinstance(document, dict) or not isinstance(document.get("services"), dict):
        return {}

    discovered: dict[str, list[str]] = {}
    for service_name, service_config in document["services"].items():
        if not isinstance(service_config, dict):
            continue
        values = _normalize_compose_environment(service_config.get("environment"))
        if values:
            discovered[str(service_name)] = values

    return discovered


def _normalize_compose_environment(environment: object) -> list[str]:
    if isinstance(environment, dict):
        value = environment.get("AGORA_ENV")
        return [str(value)] if value is not None else []
    if isinstance(environment, list):
        values = []
        for item in environment:
            if not isinstance(item, str):
                continue
            if item == "AGORA_ENV":
                values.append(UNRESOLVED_COMPOSE_ENVIRONMENT)
                continue
            name, separator, value = item.partition("=")
            if name == "AGORA_ENV" and separator:
                values.append(value)
        return values
    return []


def _assert_supported_runtime_environments(discovered: dict[str, list[str]]) -> None:
    unsupported = sorted(
        value
        for values in discovered.values()
        for value in values
        if value not in SUPPORTED_ENVIRONMENTS
    )
    assert not unsupported, f"Unsupported AGORA_ENV values: {unsupported}"


def test_compose_environment_parser_supports_mapping_and_list_syntax():
    compose = """\
services:
  mapping-service:
    environment:
      AGORA_ENV: production
  list-service:
    environment:
      - AGORA_ENV=local
  unrelated-service:
    labels:
      AGORA_ENV: ignored
"""

    assert _compose_service_environment_values(compose) == {
        "mapping-service": ["production"],
        "list-service": ["local"],
    }


def test_compose_environment_parser_rejects_unsupported_list_value():
    compose = """\
services:
  api:
    environment:
      - AGORA_ENV=local
"""

    discovered = _compose_service_environment_values(compose)

    with pytest.raises(AssertionError, match="local"):
        _assert_supported_runtime_environments(discovered)


def test_compose_environment_parser_discovers_quoted_list_value():
    compose = """\
services:
  api:
    environment:
      - "AGORA_ENV=local"
"""

    discovered = _compose_service_environment_values(compose)

    assert discovered == {"api": ["local"]}
    with pytest.raises(AssertionError, match="local"):
        _assert_supported_runtime_environments(discovered)


def test_compose_environment_parser_supports_inline_list_syntax():
    compose = """\
services:
  api:
    environment: [AGORA_ENV=production]
"""

    assert _compose_service_environment_values(compose) == {"api": ["production"]}


def test_compose_environment_parser_supports_varied_indentation():
    compose = """\
services:
    api:
        environment:
            AGORA_ENV: production
"""

    assert _compose_service_environment_values(compose) == {"api": ["production"]}


def test_compose_environment_parser_rejects_key_only_value_with_supported_value():
    compose = """\
services:
  api:
    environment:
      - AGORA_ENV
      - AGORA_ENV=production
"""

    discovered = _compose_service_environment_values(compose)

    assert discovered == {"api": ["<unresolved>", "production"]}
    with pytest.raises(AssertionError, match="<unresolved>"):
        _assert_supported_runtime_environments(discovered)


def test_documented_test_setup_installs_test_extra():
    documented_installs = {
        "README.md": EDITABLE_INSTALL_PATTERN.findall(Path("README.md").read_text()),
        "docs/manual/agora-system-user-and-technical-manual.zh-CN.md": EDITABLE_INSTALL_PATTERN.findall(
            Path("docs/manual/agora-system-user-and-technical-manual.zh-CN.md").read_text()
        ),
    }

    assert documented_installs == {
        "README.md": ["'.[test]'"],
        "docs/manual/agora-system-user-and-technical-manual.zh-CN.md": ["'.[test]'"],
    }


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


def test_project_page_has_no_server_local_repository_controls():
    page_path = Path("apps/web/app/projects/[projectId]/page.tsx")
    initialize_route = Path("apps/web/app/projects/[projectId]/initialize/route.ts")
    retry_route = Path(
        "apps/web/app/projects/[projectId]/initialization-jobs/[jobId]/retry/route.ts"
    )

    page = page_path.read_text()

    assert "repo_path" not in page
    assert "Repository path" not in page
    assert "Initialize from local repository" not in page
    assert "Initialize from a local repository" not in page
    assert "/initialize" not in page
    assert "/retry" not in page
    assert "Retry" not in page
    assert "authorized AI tool" in page
    assert "string | { code: string; message: string }" in page
    assert "typeof warning === \"string\"" in page
    assert "<li key={warning}>{warning}</li>" not in page
    assert "initialization-history-row" in page
    assert not initialize_route.exists()
    assert not retry_route.exists()

    styles = Path("apps/web/app/styles.css").read_text()
    assert ".initialization-history-row" in styles
    assert "grid-template-columns: 120px 100px 100px minmax(180px, 1fr);" in styles


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
    assert "compatibility-check" in content
    assert "agora_get_protocol_manifest" in content
    assert "p9-blackbox-suite" in content
    assert "context-concurrency" in content
    assert "needs_rebase" in content
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
    assert DOTENV_ENV_PATTERN.findall(env_example) == ["production"]


def test_runtime_environment_examples_use_supported_values():
    env_example = Path(".env.example").read_text()
    compose = Path("infra/docker-compose.yml").read_text()
    p9_guide = Path("docs/development/p9-operations-readiness-blackbox.zh-CN.md").read_text()
    manual = Path("docs/manual/agora-system-user-and-technical-manual.zh-CN.md").read_text()

    compose_environments = _compose_service_environment_values(compose)
    assert compose_environments == {
        "api": ["production"],
        "web": ["production"],
        "local-connector": ["production"],
    }

    discovered_values = {
        ".env.example": DOTENV_ENV_PATTERN.findall(env_example),
        "infra/docker-compose.yml": [
            value
            for values in compose_environments.values()
            for value in values
        ],
        "docs/development/p9-operations-readiness-blackbox.zh-CN.md": EXPORT_ENV_PATTERN.findall(p9_guide),
        "docs/manual/agora-system-user-and-technical-manual.zh-CN.md": EXPORT_ENV_PATTERN.findall(manual),
    }

    assert discovered_values == {
        ".env.example": ["production"],
        "infra/docker-compose.yml": ["production", "production", "production"],
        "docs/development/p9-operations-readiness-blackbox.zh-CN.md": ["production"],
        "docs/manual/agora-system-user-and-technical-manual.zh-CN.md": ["development"],
    }
    _assert_supported_runtime_environments(discovered_values)

    for production_source in (env_example, compose, p9_guide):
        assert "AGORA_LOCAL_INIT_ROOT" not in production_source


def _compose_service_environment_map(compose: str) -> dict[str, dict[str, str]]:
    document = yaml.safe_load(compose) or {}
    if not isinstance(document, dict) or not isinstance(document.get("services"), dict):
        return {}

    discovered: dict[str, dict[str, str]] = {}
    for service_name, service_config in document["services"].items():
        if not isinstance(service_config, dict):
            continue
        environment = service_config.get("environment")
        values: dict[str, str] = {}
        if isinstance(environment, dict):
            for name, value in environment.items():
                if isinstance(name, str) and value is not None:
                    values[name] = str(value)
        elif isinstance(environment, list):
            for item in environment:
                if not isinstance(item, str):
                    continue
                name, separator, value = item.partition("=")
                if separator and name:
                    values[name] = value
        if values:
            discovered[str(service_name)] = values
    return discovered


def test_compose_web_and_connector_set_single_runtime_api_url():
    compose = Path("infra/docker-compose.yml").read_text()
    environments = _compose_service_environment_map(compose)

    assert environments["web"].get("AGORA_API_URL") == "http://api:8000"
    assert environments["local-connector"].get("AGORA_API_URL") == "http://api:8000"
    assert "AGORA_API_BASE_URL" not in compose
    for service, env in environments.items():
        assert "AGORA_API_BASE_URL" not in env, service


def test_web_api_client_reads_runtime_api_url_variable():
    api_path = Path("apps/web/lib/api.ts")
    api = api_path.read_text()

    assert "AGORA_API_URL" in api
    assert "NEXT_PUBLIC_AGORA_API_URL" not in api
    assert "AGORA_API_BASE_URL" not in api


def test_local_development_docs_and_scripts_use_single_api_url_variable():
    candidates = [
        *Path("docs/development").glob("*.md"),
        *Path("docs/manual").glob("*.md"),
        *Path("scripts").glob("*.py"),
    ]
    offenders = [
        str(path)
        for path in candidates
        if "NEXT_PUBLIC_AGORA_API_URL" in path.read_text()
    ]
    assert offenders == []


def test_compose_postgres_persists_data_with_named_volume():
    compose_text = Path("infra/docker-compose.yml").read_text()
    document = yaml.safe_load(compose_text)

    postgres = document["services"]["postgres"]
    volumes = postgres.get("volumes", [])
    assert "agora-postgres-data:/var/lib/postgresql/data" in volumes

    declared = document.get("volumes", {})
    assert "agora-postgres-data" in declared


def test_pr1a_blackbox_guide_exists():
    guide = Path("docs/development/pr1a-runtime-mcp-blackbox.zh-CN.md")
    content = guide.read_text()

    assert "PR1A Runtime and MCP Hardening 黑盒验证步骤" in content
    assert "不是" in content
    assert "生产" in content
    assert "敏感" in content
    assert "AI 工具" in content
    assert "Web" in content
    assert '"1.1"' in content
    assert "agora_complete_workflow_step" in content
    assert "idempotency_key" in content
    assert "step_key" in content
    assert "summary" in content
    assert "agora_close_work" in content
    assert "start -> complete -> close" in content
    assert "agora_start_work" in content
    assert "PR1_UPLOAD_POLICY_REQUIRED" in content
    assert "PR1_APPROVAL_POLICY_REQUIRED" in content
    assert "PR1B" in content
    assert "PR1C" in content
    assert "repo_path" in content
    assert "不包含" in content
    assert "Initialize from local repository" in content
    assert "Retry" in content
    assert "用户是否通过 AI 工具完成" in content
    assert "未手动调用 HTTP API" in content
