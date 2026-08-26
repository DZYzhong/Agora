# Agora P4 Workflow Harness Implementation Plan

**Goal:** Make project processes executable through AI tools while retaining human control and complete WorkItem-level audit.

## Task 1: Workflow persistence and start-work pinning

**Files:**

- Create: `alembic/versions/20260825_0005_p4_workflow_foundation.py`
- Create: `packages/core/repositories/workflows.py`
- Modify: `packages/core/models.py`
- Modify: `packages/core/repositories/work.py`
- Modify: `packages/core/services/runtime.py`
- Modify: `packages/harness/service.py`
- Modify: `packages/harness/session_recorder.py`
- Modify: `apps/api/routers/work_items.py`
- Test: `tests/integration/test_migrations.py`
- Test: `tests/integration/api/test_harness_api.py`
- Test: `tests/integration/api/test_work_items_api.py`
- Test: `tests/unit/harness/conftest.py`

- [x] Add WorkflowDefinition, immutable WorkflowVersion, WorkflowExecution and WorkflowStepRun schema.
- [x] Add a built-in standard AI development workflow: analysis, design, review, implementation, self_test, delivery.
- [x] Create one authoritative WorkflowExecution per WorkItem when work starts.
- [x] Initialize first WorkflowStepRun as `running` and later steps as `pending`.
- [x] Derive WorkItem stage from the current workflow step instead of leaving new work in backlog.
- [x] Pin WorkflowVersion on WorkSession and return it from `agora_start_work`.
- [x] Show workflow execution and step state in WorkItem API projections.
- [x] Keep the existing P0 e2e fake core compatible with workflow-pinned WorkSessions.

Verification:

```text
.venv/bin/pytest tests/integration/test_migrations.py::test_alembic_upgrade_head_creates_current_schema tests/integration/api/test_harness_api.py::test_start_work_endpoint_returns_session tests/integration/api/test_work_items_api.py::test_start_work_creates_listable_work_item_for_authorized_project
# 3 passed

.venv/bin/pytest tests/integration/api/test_harness_api.py tests/integration/api/test_work_items_api.py tests/unit/harness/test_harness_service.py tests/integration/test_migrations.py
# 33 passed

.venv/bin/pytest tests/e2e/test_p0_loop.py::test_p0_loop
# 1 passed

.venv/bin/pytest
# 189 passed, 2 skipped

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# Compiled successfully

git diff --check
# passed
```

## Next P4 tasks

- Wait for user black-box validation feedback before moving to P5.

## Task 2: Canonical workflow step completion

**Files:**

- Modify: `packages/core/repositories/work.py`
- Modify: `packages/core/repositories/workflows.py`
- Modify: `packages/core/services/runtime.py`
- Modify: `packages/harness/service.py`
- Modify: `apps/api/routers/harness.py`
- Modify: `apps/mcp/tools.py`
- Test: `tests/integration/api/test_harness_api.py`
- Test: `tests/unit/mcp/test_tools.py`

- [x] Add canonical `agora_complete_workflow_step` MCP tool delegation.
- [x] Add `/harness/complete-workflow-step` API endpoint.
- [x] Require authenticated project-session membership before workflow advancement.
- [x] Reject non-current step completion with `WORKFLOW_STEP_NOT_CURRENT`.
- [x] Advance the next step to `running` and synchronize WorkItem `stage`.
- [x] Record `workflow_step_completed` events with summary and actor metadata.

Verification:

```text
.venv/bin/pytest tests/integration/api/test_harness_api.py::test_complete_workflow_step_advances_current_step_and_work_item_stage tests/integration/api/test_harness_api.py::test_complete_workflow_step_rejects_non_current_step
# failed first with 404 before implementation, then 2 passed

.venv/bin/pytest tests/unit/mcp/test_tools.py::test_mcp_complete_workflow_step_delegates_to_harness
# failed first with missing agora_complete_workflow_step, then 1 passed

.venv/bin/pytest tests/integration/api/test_harness_api.py tests/integration/api/test_work_items_api.py tests/unit/mcp/test_tools.py tests/unit/harness/test_harness_service.py
# 34 passed

.venv/bin/pytest
# 192 passed, 2 skipped

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# Compiled successfully

git diff --check
# passed
```

## Task 5: P4 black-box validation guide

**Files:**

- Create: `docs/development/p4-workflow-audit-blackbox.zh-CN.md`
- Modify: `tests/integration/test_web_config.py`
- Modify: `docs/superpowers/plans/2026-08-25-agora-p4-workflow-harness.md`
- Modify: `docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`

- [x] Add black-box steps for production-style local API/Web startup.
- [x] Require AI tool operation through `agora_start_work` and `agora_complete_workflow_step`.
- [x] Document Web-only verification for WorkItem list and WorkItem `Workflow audit`.
- [x] Include jump-protection validation for `WORKFLOW_STEP_NOT_CURRENT`.
- [x] Add a regression check that the P4 black-box guide keeps the key workflow audit acceptance points.

Verification:

```text
.venv/bin/pytest tests/integration/test_web_config.py::test_p4_workflow_audit_blackbox_guide_exists
# 1 passed

.venv/bin/pytest tests/integration/test_web_config.py
# 9 passed

.venv/bin/pytest
# 197 passed, 2 skipped

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# Compiled successfully

git diff --check
# passed
```

## Task 4: Web workflow audit detail

**Files:**

- Modify: `packages/core/repositories/workflows.py`
- Modify: `packages/core/services/runtime.py`
- Modify: `apps/api/routers/work_items.py`
- Modify: `apps/web/app/projects/[projectId]/work-items/[workItemId]/page.tsx`
- Test: `tests/integration/api/test_work_items_api.py`
- Test: `tests/integration/test_web_config.py`

- [x] Add read projections for WorkArtifact and HumanConfirmation records by WorkflowExecution.
- [x] Include per-step `artifacts` and `human_confirmations` in WorkItem detail API.
- [x] Render a Web `Workflow audit` section on WorkItem detail.
- [x] Show each workflow step status, required outputs, submitted step outputs and human confirmations.
- [x] Verify the page through a real local API/Web SSR request using production-style tokens and a temporary database.

Verification:

```text
.venv/bin/pytest tests/integration/api/test_work_items_api.py::test_work_item_detail_includes_workflow_artifacts_and_confirmations
# failed first before API returned artifacts, then 1 passed

.venv/bin/pytest tests/integration/test_web_config.py::test_work_item_detail_page_renders_workflow_audit_evidence
# failed first before page rendered Workflow audit, then 1 passed

.venv/bin/pytest tests/integration/api/test_work_items_api.py tests/integration/api/test_harness_api.py tests/integration/test_web_config.py tests/unit/harness/test_harness_service.py
# 38 passed

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# Compiled successfully

.venv/bin/pytest
# 196 passed, 2 skipped

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# Compiled successfully

Production-style local SSR check:
# API: 127.0.0.1:18110, Web: 127.0.0.1:13110, temporary database /tmp/agora-p4-web-audit.db
# HTML contained Workflow audit, Step outputs, Human confirmations, AG-888 分析记录 and 人工确认文本.

git diff --check
# passed
```

## Task 3: Work artifacts and human confirmations

**Files:**

- Create: `alembic/versions/20260825_0006_p4_work_artifacts.py`
- Modify: `packages/core/models.py`
- Modify: `packages/core/repositories/workflows.py`
- Modify: `packages/core/services/runtime.py`
- Modify: `packages/harness/service.py`
- Modify: `apps/api/routers/harness.py`
- Modify: `apps/mcp/tools.py`
- Test: `tests/integration/test_migrations.py`
- Test: `tests/integration/api/test_harness_api.py`
- Test: `tests/unit/mcp/test_tools.py`

- [x] Add persistent WorkArtifact records linked to WorkItem, WorkSession, WorkflowExecution and WorkflowStepRun.
- [x] Add persistent HumanConfirmation records linked to the same workflow audit chain.
- [x] Extend `agora_complete_workflow_step` to accept artifacts and human confirmation payloads.
- [x] Return created artifact and confirmation IDs to the AI tool caller.
- [x] Include artifact and confirmation IDs in `workflow_step_completed` event payloads.

Verification:

```text
.venv/bin/pytest tests/integration/test_migrations.py::test_alembic_upgrade_head_creates_current_schema tests/integration/test_migrations.py::test_create_app_engine_upgrades_empty_in_memory_database_on_same_engine
# failed first before 0006 migration, then 3 passed

.venv/bin/pytest tests/integration/api/test_harness_api.py::test_complete_workflow_step_captures_artifacts_and_human_confirmation
# failed first before models existed, then 1 passed

.venv/bin/pytest tests/unit/mcp/test_tools.py::test_mcp_complete_workflow_step_delegates_to_harness tests/unit/mcp/test_tools.py::test_mcp_complete_workflow_step_passes_artifacts_and_human_confirmation
# failed first before MCP accepted artifacts, then 2 passed

.venv/bin/pytest tests/integration/test_migrations.py tests/integration/api/test_harness_api.py tests/integration/api/test_work_items_api.py tests/unit/mcp/test_tools.py tests/unit/harness/test_harness_service.py
# 43 passed

.venv/bin/pytest
# 194 passed, 2 skipped

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# Compiled successfully

git diff --check
# passed
```
