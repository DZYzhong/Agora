# Agora P9 Operations Readiness Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Agora deployable and observable enough for a small software team to run production-like black-box validation.

**Architecture:** Add lightweight operational endpoints and container runtime assets around the existing FastAPI, Next.js and MCP boundaries. Keep readiness tied to real database/schema/config checks, and keep role acceptance anchored in the existing AI-tool/Web black-box journey.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Docker Compose, Next.js, pytest.

---

## Chunk 1: Health, readiness and metrics

### Task 1: API operational probes

**Files:**

- Modify: `apps/api/routers/health.py`
- Test: `tests/unit/test_health.py`

- [x] Add `GET /ready`.
- [x] Verify database connectivity.
- [x] Report Alembic schema revision.
- [x] Report missing required runtime configuration.
- [x] Add `GET /metrics` with Prometheus-style text counters.

Verification:

```text
.venv/bin/pytest tests/unit/test_health.py::test_readiness_endpoint_reports_database_schema_and_configuration tests/unit/test_health.py::test_metrics_endpoint_exposes_prometheus_style_operational_counters
# failed first because /ready and /metrics did not exist, then 2 passed
```

## Chunk 2: Container runtime assets

### Task 1: Docker Compose production-like runtime

**Files:**

- Create: `infra/Dockerfile.api`
- Create: `infra/Dockerfile.web`
- Create: `infra/Dockerfile.local-connector`
- Modify: `infra/docker-compose.yml`
- Modify: `.env.example`
- Test: `tests/integration/test_web_config.py`

- [x] Add API container entrypoint.
- [x] Add Web build/runtime container entrypoint.
- [x] Add Local Connector/MCP stdio container entrypoint.
- [x] Add Compose services for API, Web and Local Connector.
- [x] Add API and Postgres health checks.
- [x] Add CI token and production-like env defaults to `.env.example`.

Verification:

```text
.venv/bin/pytest tests/integration/test_web_config.py::test_p9_container_runtime_assets_exist
# failed first because container runtime assets did not exist, then 1 passed
```

## Chunk 3: Operations black-box guide

### Task 1: P9 black-box runbook

**Files:**

- Create: `docs/development/p9-operations-readiness-blackbox.zh-CN.md`
- Test: `tests/integration/test_web_config.py`

- [x] Document `/health`, `/ready` and `/metrics`.
- [x] Document production-like `AGORA_DATABASE_URL` and token configuration.
- [x] Document backup and recovery validation.
- [x] Document Developer, Reviewer, Project Manager and Quality role smoke tests.

Verification:

```text
.venv/bin/pytest tests/integration/test_web_config.py::test_p9_operations_blackbox_guide_exists
# failed first because the guide did not exist, then 1 passed
```

## Chunk 4: SQLite backup and recovery commands

### Task 1: Admin CLI backup/restore

**Files:**

- Modify: `scripts/agora_admin.py`
- Modify: `docs/development/p9-operations-readiness-blackbox.zh-CN.md`
- Test: `tests/integration/test_admin_cli.py`

- [x] Add `backup-sqlite` using SQLite online backup API.
- [x] Add `restore-sqlite` with explicit `--yes` replacement confirmation.
- [x] Verify restored database keeps persisted project data.
- [x] Document SQLite and PostgreSQL recovery paths separately.

Verification:

```text
.venv/bin/pytest tests/integration/test_admin_cli.py::test_admin_cli_backup_and_restore_sqlite_database
# failed first because backup-sqlite and restore-sqlite did not exist, then 1 passed
```

## Chunk 5: Project governance export archive

### Task 1: Admin CLI project export

**Files:**

- Modify: `scripts/agora_admin.py`
- Modify: `docs/development/p9-operations-readiness-blackbox.zh-CN.md`
- Test: `tests/integration/test_admin_cli.py`

- [x] Add `export-project` command.
- [x] Resolve project by slug.
- [x] Export project governance tables as JSONL.
- [x] Write `manifest.json` with schema revision, project identity and file counts.
- [x] Document project archive validation for audit and migration dry-runs.

Verification:

```text
.venv/bin/pytest tests/integration/test_admin_cli.py::test_admin_cli_export_project_archive_writes_manifest_and_jsonl_assets
# failed first because export-project did not exist, then 1 passed
```

## Chunk 6: Deployment smoke command

### Task 1: HTTP smoke checks

**Files:**

- Modify: `scripts/agora_admin.py`
- Modify: `docs/development/p9-operations-readiness-blackbox.zh-CN.md`
- Modify: `tests/integration/test_web_config.py`
- Test: `tests/integration/test_admin_cli.py`

- [x] Add `smoke` admin CLI command.
- [x] Check API `/ready` and require `status = ready`.
- [x] Check API `/metrics` and require `agora_ready 1`.
- [x] Check optional Web base URL.
- [x] Return non-zero on failed deployment checks.

Verification:

```text
.venv/bin/pytest tests/integration/test_admin_cli.py::test_admin_cli_smoke_checks_api_readiness_metrics_and_web
# failed first because smoke did not exist, then 1 passed
```

## Chunk 7: Request tracing headers

### Task 1: Request ID middleware

**Files:**

- Create: `apps/api/middleware.py`
- Modify: `apps/api/main.py`
- Modify: `docs/development/p9-operations-readiness-blackbox.zh-CN.md`
- Modify: `tests/integration/test_web_config.py`
- Test: `tests/unit/test_health.py`

- [x] Generate `X-Request-ID` for requests that do not provide one.
- [x] Preserve incoming `X-Request-ID` for caller correlation.
- [x] Attach `X-Request-ID` to error responses.
- [x] Document request id validation in the P9 black-box guide.

Verification:

```text
.venv/bin/pytest tests/unit/test_health.py::test_api_generates_request_id_for_every_response tests/unit/test_health.py::test_api_preserves_incoming_request_id tests/unit/test_health.py::test_api_adds_request_id_to_error_responses tests/integration/test_web_config.py::test_p9_operations_blackbox_guide_exists
# failed first because X-Request-ID was not emitted, then passed
```

## Chunk 8: Project operations summary

### Task 1: Shared governance summary for CLI, API and Web

**Files:**

- Create: `packages/core/services/project_summary.py`
- Modify: `scripts/agora_admin.py`
- Modify: `apps/api/routers/projects.py`
- Create: `apps/web/app/projects/[projectId]/operations/page.tsx`
- Modify: `apps/web/app/projects/[projectId]/page.tsx`
- Modify: `docs/development/p9-operations-readiness-blackbox.zh-CN.md`
- Modify: `tests/integration/test_admin_cli.py`
- Modify: `tests/integration/api/test_projects_api.py`
- Modify: `tests/integration/test_web_config.py`

- [x] Add `project-summary` admin CLI command.
- [x] Build project governance summary from real persisted tables.
- [x] Include assets, work items, context, quality, skills, approvals, security audit, repository signals and PR/MR signals.
- [x] Add `GET /projects/{project_id}/operations-summary`.
- [x] Add Web `Operations summary` page and project-home entry.
- [x] Document black-box validation steps.

Verification:

```text
.venv/bin/pytest tests/integration/test_admin_cli.py::test_admin_cli_project_summary_reports_governance_and_delivery_state tests/integration/api/test_projects_api.py::test_project_operations_summary_api_reports_project_governance_state tests/integration/test_web_config.py::test_p9_operations_summary_page_is_available_and_linked_from_project_home tests/integration/test_web_config.py::test_p9_operations_blackbox_guide_exists
# failed first because the CLI/API/Web/documentation did not expose the summary, then passed
```

## Verification

Run:

```bash
.venv/bin/pytest tests/unit/test_health.py tests/integration/test_web_config.py tests/integration/test_migrations.py tests/integration/api/test_integrations_api.py
.venv/bin/pytest
cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
git diff --check
```
