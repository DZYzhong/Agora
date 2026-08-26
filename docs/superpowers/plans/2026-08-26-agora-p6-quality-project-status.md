# Agora P6 Quality and Project Management Implementation Plan

**Goal:** Give quality personnel and project managers trustworthy project status through AI tools and Web UI.

This P6 plan follows the realigned Agent-first, Harness-first architecture. Quality status must be evidence-backed: failed evidence remains failing, missing evidence remains unverified, and AI summaries or workflow progress cannot be converted into passed quality.

## Task 1: QualityEvidence and project status foundation

**Files:**

- Create: `alembic/versions/20260826_0008_p6_quality_evidence.py`
- Create: `packages/core/repositories/quality.py`
- Create: `apps/web/app/projects/[projectId]/status/page.tsx`
- Modify: `packages/core/models.py`
- Modify: `packages/core/services/runtime.py`
- Modify: `packages/harness/service.py`
- Modify: `apps/api/routers/harness.py`
- Modify: `apps/mcp/tools.py`
- Modify: `apps/mcp/server.py`
- Modify: `apps/web/app/projects/[projectId]/page.tsx`
- Test: `tests/integration/test_migrations.py`
- Test: `tests/integration/api/test_harness_api.py`
- Test: `tests/unit/mcp/test_tools.py`
- Test: `tests/unit/mcp/test_stdio_server.py`
- Test: `tests/integration/test_web_config.py`

- [x] Add structured `quality_evidence` schema linked to Project, WorkItem, WorkSession and User.
- [x] Add repository/runtime support for creating and listing quality evidence by WorkItem or Project.
- [x] Add `agora_record_evidence` Harness/API/MCP capability for local tests, CI, review and risk findings.
- [x] Add `agora_get_quality_status` Harness/API/MCP capability with explicit evidence, gaps and unverified claims.
- [x] Add `agora_get_project_status` Harness/API/MCP capability for project-manager summaries across WorkItems, quality states and pending approvals.
- [x] Add Web project status page linked from project detail.
- [x] Preserve the rule that failed or missing evidence is never treated as passed quality.

Verification:

```text
.venv/bin/pytest tests/integration/test_migrations.py tests/integration/api/test_harness_api.py tests/unit/mcp/test_tools.py tests/unit/mcp/test_stdio_server.py tests/integration/test_web_config.py
# failed first before P6 schema/API/MCP/Web implementation, then 60 passed
```

## Task 2: Delivery readiness, blockers and evidence drill-down

**Files:**

- Modify: `packages/harness/service.py`
- Modify: `apps/web/app/projects/[projectId]/status/page.tsx`
- Test: `tests/integration/api/test_harness_api.py`
- Test: `tests/integration/test_web_config.py`

- [x] Add top-level `delivery_readiness` so project managers can see whether the project is ready, at risk, needs evidence or blocked.
- [x] Add top-level `blockers` derived from blocked WorkItems and failed quality evidence.
- [x] Add `quality_dimensions` grouped by evidence type and status.
- [x] Include latest per-WorkItem `quality_evidence` records in project status.
- [x] Render delivery readiness, blockers, quality dimensions and latest evidence in the Web project status page.

Verification:

```text
.venv/bin/pytest tests/integration/api/test_harness_api.py::test_project_status_aggregates_work_items_quality_and_pending_approvals
# failed first because delivery_readiness was missing, then 1 passed

.venv/bin/pytest tests/integration/test_web_config.py::test_project_status_page_is_available_and_linked_from_project_home
# failed first because the Web page did not render Delivery readiness, Blockers or Latest evidence, then 1 passed
```

## Remaining P6 tasks

- Add black-box guide after the project-manager and quality-user journey is broad enough to validate in one batch.
- Consider richer WorkItem owner/user display after role and membership UI is expanded.
