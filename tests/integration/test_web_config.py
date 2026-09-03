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


def test_project_page_has_no_server_local_repository_or_initialization_ui():
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
    # C1: the project home no longer surfaces server-local initialization
    # state (jobs/status/history) to web users.
    assert "initialization-jobs" not in page
    assert "Initialization" not in page
    assert "initialization-history-row" not in page
    assert "latestInitializationJob" not in page
    # Redesigned home resolves labels through the bilingual i18n dictionary.
    i18n = Path("apps/web/lib/i18n.ts").read_text()
    assert "inFlight" in page
    assert "session.status !== \"closed\"" in page
    assert "进行中的会话" in i18n
    assert "In-flight sessions" in i18n
    assert not initialize_route.exists()
    assert not retry_route.exists()
    # The legacy stylesheet was retired by the UI redesign; the layout loads
    # the Tailwind theme only.
    layout = Path("apps/web/app/layout.tsx").read_text()
    assert "theme.css" in layout
    assert "styles.css" not in layout


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
        "migrate": ["production"],
        "api": ["production"],
        "web": ["production"],
        "local-connector": ["production"],
        "worker": ["production"],
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
        "infra/docker-compose.yml": ["production", "production", "production", "production", "production"],
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


def test_pr1b_web_login_page_and_session_routes_exist():
    login_page = Path("apps/web/app/login/page.tsx")
    login_route = Path("apps/web/app/login/submit/route.ts")
    logout_route = Path("apps/web/app/logout/route.ts")
    api_lib = Path("apps/web/lib/api.ts").read_text()

    assert login_page.exists()
    content = login_page.read_text()
    assert "username" in content
    assert "password" in content
    # Bilingual login: labels resolve through i18n; /login/submit handles auth.
    assert "makeT" in content
    assert "/login/submit" in content

    login_handler = login_route.read_text()
    assert "/auth/login" in login_handler
    assert "set-cookie" in login_handler
    assert "Location" in login_handler

    logout_handler = logout_route.read_text()
    assert "/auth/logout" in logout_handler
    assert "agora_session" in logout_handler
    assert "Max-Age=0" in logout_handler

    assert "apiGetWithSession" in api_lib
    assert "apiPostWithSession" in api_lib
    assert "agora_csrf" in api_lib
    assert "X-CSRF-Token" in api_lib


def test_pr1b_web_users_management_pages_exist():
    users_page = Path("apps/web/app/users/page.tsx")
    assert users_page.exists()
    content = users_page.read_text()
    assert "Create user" in content
    assert "username" in content
    assert "display_name" in content
    assert "Disable" in content
    assert "Reset password" in content
    assert "/users?org_id=local-org" in content
    assert "activation_token" in content
    assert "reset_token" in content

    for action in ("create", "disable", "enable", "reset"):
        route = Path(f"apps/web/app/users/{action}/route.ts")
        assert route.exists(), action
        handler = route.read_text()
        assert "apiPostWithSession" in handler, action


def test_pr1b_web_nav_links_to_users():
    nav = Path("apps/web/components/Nav.tsx").read_text()
    assert 'href="/users"' in nav


def test_pr1c_eslint_is_configured_and_non_interactive():
    config = Path("apps/web/eslint.config.mjs")
    package = Path("apps/web/package.json").read_text()

    assert config.exists()
    assert "FlatCompat" in config.read_text()
    assert "next/core-web-vitals" in config.read_text()
    assert '"lint": "eslint ."' in package
    assert "eslint" in package
    assert "eslint-config-next" in package


def test_pr2_compose_runs_migrate_worker_and_reverse_proxy():
    compose = Path("infra/docker-compose.yml").read_text()
    document = yaml.safe_load(compose)
    services = document["services"]

    assert "migrate" in services
    assert services["migrate"]["command"] == ["alembic", "upgrade", "head"]
    assert services["api"]["depends_on"]["migrate"]["condition"] == "service_completed_successfully"

    assert "worker" in services
    assert services["worker"]["command"] == ["python", "-m", "apps.workers.main", "outbox-loop"]

    assert "nginx" in services
    assert "agora.conf" in services["nginx"]["volumes"][0]


def test_pr2_nginx_reverse_proxy_enforces_limits():
    conf = Path("infra/nginx/agora.conf").read_text()

    assert "ssl_certificate" in conf
    assert "ssl_certificate_key" in conf
    assert "client_max_body_size 1m" in conf
    assert "client_body_timeout" in conf
    assert "proxy_read_timeout" in conf
    assert "limit_req_zone" in conf
    assert "limit_req" in conf
    assert "proxy_pass http://agora_api" in conf
    assert "return 301 https://" in conf


def test_pr_web_approval_loop_uses_session_and_reauth():
    api_lib = Path("apps/web/lib/api.ts").read_text()
    assert "AgoraApiError" in api_lib
    assert "APPROVAL_CREDENTIAL_REQUIRED" in api_lib or "apiError" in api_lib

    skill_route = Path("apps/web/app/projects/[projectId]/skills/[skillId]/approve/route.ts").read_text()
    assert "apiPostWithSession" in skill_route
    assert "hasSessionCookie" in skill_route
    assert "APPROVAL_CREDENTIAL_REQUIRED" in skill_route
    assert "/reauth" in skill_route

    proposal_route = Path(
        "apps/web/app/projects/[projectId]/context/proposals/[proposalId]/approve/route.ts"
    ).read_text()
    assert "apiPostWithSession" in proposal_route
    assert "hasSessionCookie" in proposal_route
    assert "APPROVAL_CREDENTIAL_REQUIRED" in proposal_route
    assert "/reauth" in proposal_route


def test_pr_web_reauth_page_and_login_next_exist():
    reauth_page = Path("apps/web/app/reauth/page.tsx")
    reauth_submit = Path("apps/web/app/reauth/submit/route.ts")
    content = reauth_page.read_text()
    assert reauth_page.exists()
    assert "password" in content
    assert "/reauth/submit" in content
    assert "/auth/reauth" in reauth_submit.read_text()
    i18n = Path("apps/web/lib/i18n.ts").read_text()
    assert "重新认证" in i18n
    assert "Reauthenticate" in i18n
    assert "apiPostWithSession" in reauth_submit.read_text()

    login_submit = Path("apps/web/app/login/submit/route.ts").read_text()
    login_page = Path("apps/web/app/login/page.tsx").read_text()
    assert "next" in login_submit
    assert "next" in login_page


def test_pr_web_nav_shows_sign_in_out_and_middleware_guards_production():
    nav = Path("apps/web/components/Nav.tsx").read_text()
    assert 'cookies()' in nav or 'cookieStore' in nav
    assert "agora_session" in nav
    # Bilingual nav: sign-in/out labels resolve through the i18n dictionary;
    # both languages must be defined and the logout action present.
    assert "signOut" in nav
    assert "signIn" in nav
    assert "退出登录" in Path("apps/web/lib/i18n.ts").read_text()
    assert "Sign out" in Path("apps/web/lib/i18n.ts").read_text()
    assert '/logout' in nav
    assert 'agora_lang' in nav or 'lang?' in nav

    middleware = Path("apps/web/middleware.ts").read_text()
    assert "AGORA_ENV" in middleware
    assert '"/login"' in middleware
    assert "next" in middleware
    assert "/projects" in middleware


def test_pr_web_knowledge_overview_page_exists_and_is_linked():
    page = Path("apps/web/app/projects/[projectId]/knowledge/page.tsx")
    assert page.exists()
    content = page.read_text()
    assert "Knowledge" in content
    assert "/projects/${projectId}/assets" in content
    assert "/projects/${projectId}/writebacks" in content
    assert "Recently accumulated" in content
    assert "Context revisions" in content
    assert "accepted_revision_id" in content

    home = Path("apps/web/app/projects/[projectId]/page.tsx").read_text()
    assert '/knowledge' in home


def test_asset_and_writeback_lists_expose_created_at_for_timelines():
    assets_router = Path("apps/api/routers/assets.py").read_text()
    writebacks_router = Path("apps/api/routers/writebacks.py").read_text()
    assert '"created_at": asset.created_at' in assets_router
    assert '"created_at": writeback.created_at' in writebacks_router


def test_pr_web_context_revision_history_exists_and_is_linked():
    page = Path("apps/web/app/projects/[projectId]/context/streams/[streamId]/page.tsx")
    assert page.exists()
    content = page.read_text()
    assert "Revision history" in content or "revision history" in content
    assert "is_head" in content
    assert "source_anchors" in content
    assert "Content by version" in content

    context_page = Path("apps/web/app/projects/[projectId]/context/page.tsx").read_text()
    assert "context/streams/" in context_page


def test_pr_web_pending_queue_page_exists_and_is_linked():
    page = Path("apps/web/app/projects/[projectId]/pending/page.tsx")
    assert page.exists()
    content = page.read_text()
    assert "Pending actions" in content
    assert "Context proposals awaiting approval" in content
    assert "Skill candidates awaiting approval" in content
    assert "Active work items" in content
    assert 'status === "submitted"' in content
    assert 'status === "candidate"' in content

    status_page = Path("apps/web/app/projects/[projectId]/status/page.tsx").read_text()
    assert "/pending" in status_page
    home = Path("apps/web/app/projects/[projectId]/page.tsx").read_text()
    assert '/pending' in home


def test_pr_web_workflow_stepper_visualizes_steps():
    page = Path("apps/web/app/projects/[projectId]/work-items/[workItemId]/page.tsx").read_text()
    assert 'aria-label="Workflow progress"' in page
    assert "order_index" in page
    assert "stepStatusClass" in page
    assert "stepMarker" in page


def test_pr_web_asset_content_view_and_filters_exist():
    detail = Path("apps/web/app/projects/[projectId]/assets/[assetId]/page.tsx")
    assert detail.exists()
    content = detail.read_text()
    assert "Content" in content
    assert "assets/${assetId}" in content or "assetId" in content

    list_page = Path("apps/web/app/projects/[projectId]/assets/page.tsx").read_text()
    assert "searchParams" in list_page
    assert "filtered" in list_page
    assert "assets/${asset.id}" in list_page
    assert '?type=' in list_page

    assets_router = Path("apps/api/routers/assets.py").read_text()
    assert '"/{asset_id}"' in assets_router
    assert "with_content" in assets_router


def test_pr_web_inflight_sessions_shown_on_project_home():
    home = Path("apps/web/app/projects/[projectId]/page.tsx").read_text()
    assert "inFlight" in home
    assert "status !== \"closed\"" in home
    assert "sessions/${session.id}" in home
    i18n = Path("apps/web/lib/i18n.ts").read_text()
    assert "In-flight sessions" in i18n
    assert "进行中的会话" in i18n


def test_pr_compose_excludes_unused_search_containers():
    document = yaml.safe_load(Path("infra/docker-compose.yml").read_text())
    services = document["services"]
    assert "qdrant" not in services
    assert "opensearch" not in services
    assert "neo4j" not in services
    assert "api" in services and "worker" in services and "nginx" in services


def test_pr3_web_credential_management_ui_exists():
    page = Path("apps/web/app/users/[userId]/credentials/page.tsx")
    assert page.exists()
    content = page.read_text()
    assert "/users/${userId}/credentials" in content
    assert "credentials/issue" in content
    assert "credentials/${credential.id}/rotate" in content
    assert "credentials/${credential.id}/revoke" in content
    issue = Path("apps/web/app/users/[userId]/credentials/issue/route.ts").read_text()
    assert "apiPostWithSession" in issue
    assert "token=" in issue


def test_pr3_web_org_and_project_member_management_ui_exist():
    org_page = Path("apps/web/app/members/page.tsx").read_text()
    assert "/organizations/local-org/members" in org_page
    assert "/members/add" in org_page
    assert "/members/${member.user.id}/role" in org_page

    proj_page = Path("apps/web/app/projects/[projectId]/members/page.tsx").read_text()
    assert "/projects/${projectId}/members" in proj_page
    assert "PROJECT_ROLES" in proj_page

    home = Path("apps/web/app/projects/[projectId]/page.tsx").read_text()
    assert "/members" in home
    i18n = Path("apps/web/lib/i18n.ts").read_text()
    assert "membersHint" in i18n
    assert "项目成员与角色" in i18n


def test_pr3_web_patch_and_delete_session_helpers_exist():
    api = Path("apps/web/lib/api.ts").read_text()
    assert "apiPatchWithSession" in api
    assert "apiDeleteWithSession" in api
    assert 'method: "PATCH"' in api
    assert 'method: "DELETE"' in api


def test_pr5_nginx_and_api_security_headers_configured():
    nginx = Path("infra/nginx/agora.conf").read_text()
    assert "X-Content-Type-Options nosniff" in nginx
    assert "X-Frame-Options DENY" in nginx
    assert "frame-ancestors 'none'" in nginx

    middleware = Path("apps/api/middleware.py").read_text()
    assert "class SecurityHeadersMiddleware" in middleware
    assert "Permissions-Policy" in middleware
    main = Path("apps/api/main.py").read_text()
    assert "SecurityHeadersMiddleware" in main


def test_ops_release_artifacts_are_present_and_pinned():
    import yaml

    compose = yaml.safe_load(Path("infra/docker-compose.yml").read_text())
    services = compose["services"]
    for name in ("api", "web", "nginx", "postgres", "redis", "prometheus", "local-connector", "worker", "migrate"):
        assert name in services, name
    for name in ("api", "web", "nginx", "postgres", "redis", "prometheus", "local-connector", "worker"):
        assert services[name].get("restart") == "unless-stopped", name
    assert services["prometheus"]["ports"] == ["9091:9090"]

    monitoring = Path("infra/monitoring")
    assert (monitoring / "prometheus.yml").exists()
    assert (monitoring / "agora-alerts.yml").exists()
    assert (monitoring / "alertmanager.yml").exists()
    alerts = (monitoring / "agora-alerts.yml").read_text()
    assert "AgoraNotReady" in alerts and "AgoraSchemaStale" in alerts

    scripts = Path("scripts")
    for name in ("deploy_local.sh", "verify_production.sh", "backup_db.sh", "install_backup_cron.sh", "perf_smoke.py"):
        assert (scripts / name).exists(), name
    assert (scripts / "deploy_local.sh").read_text().count("docker compose") >= 1

    docs = Path("docs/development")
    assert (docs / "deployment-manual.zh-CN.md").exists()
    assert (docs / "local-production-runbook.zh-CN.md").exists()
    manual = (docs / "deployment-manual.zh-CN.md").read_text()
    assert "postgres:16" in manual and "nginx:1.27-alpine" in manual and "prom/prometheus:v2.54.1" in manual
