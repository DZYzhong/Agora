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

- Add `agora_complete_workflow_step` with prerequisite and role checks.
- Add WorkArtifact and HumanConfirmation capture.
- Extend Web WorkItem detail to show workflow steps, artifacts and confirmations.
