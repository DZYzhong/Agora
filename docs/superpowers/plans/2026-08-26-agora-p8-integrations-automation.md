# Agora P8 Integrations and Quiet Automation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect Agora to repository, CI, task and PR signals so context and project status stay current with minimal user interruption.

**Architecture:** Start with a provider-neutral CI QualitySignal ingestion path secured by a CI service credential. Reuse P2 identity, P6 QualityEvidence and P7 SecurityAudit instead of inventing a separate integration store. CI can report a WorkItem key, commit and branch; Agora resolves or creates the WorkItem and records evidence so project status updates automatically.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic-managed schema, existing WorkItem and QualityEvidence repositories, Next.js Web, pytest.

---

## Chunk 1: CI QualitySignal Ingestion

### Task 1: CI service credential

**Files:**

- Modify: `packages/core/auth.py`
- Modify: `apps/api/auth.py`
- Test: `tests/integration/api/test_auth.py`

- [x] Add optional `AGORA_BOOTSTRAP_CI_TOKEN`.
- [x] Resolve CI bearer tokens as `credential_kind = ci`.
- [x] Reject non-CI callers from CI signal endpoints with `CI_CREDENTIAL_REQUIRED`.

### Task 2: CI QualitySignal API

**Files:**

- Create: `apps/api/routers/integrations.py`
- Modify: `apps/api/main.py`
- Modify: `packages/core/services/runtime.py`
- Test: `tests/integration/api/test_integrations_api.py`

- [x] Add `POST /integrations/ci/quality-signal`.
- [x] Require CI credential and project membership.
- [x] Resolve existing WorkItem by `work_item_key`; create it when missing.
- [x] Store CI result as P6 `QualityEvidence` with source `ci`.
- [x] Return project status so PM/QA dashboards update without manual work.

### Task 3: Web/docs validation

**Files:**

- Create: `docs/development/p8-ci-quality-signal-blackbox.zh-CN.md`
- Modify: `tests/integration/test_web_config.py`
- Modify: `docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`

- [x] Add black-box guide using a real CI-like command/script, not manual API calls from the user.
- [x] Document how AI tools and Web observe the automatically imported CI evidence.
- [x] Update roadmap execution log.

## Execution Notes

```text
.venv/bin/pytest tests/integration/api/test_auth.py::test_ci_bootstrap_token_is_service_scoped_and_cannot_create_projects
# failed first because CI token was not bootstrapped, then 1 passed

.venv/bin/pytest tests/integration/api/test_integrations_api.py
# failed first because /integrations/ci/quality-signal did not exist and exposed an existing get-project-status UoW boundary issue, then 2 passed

.venv/bin/pytest tests/integration/test_web_config.py::test_p8_ci_quality_signal_blackbox_guide_exists
# failed first because the guide did not exist, then 1 passed
```

## Chunk 2: Repository RevisionSignal and automatic refresh proposal

### Task 1: Repository signal persistence

**Files:**

- Create: `alembic/versions/20260826_0010_p8_repository_revision_signals.py`
- Create: `packages/core/repositories/integrations.py`
- Modify: `packages/core/models.py`
- Modify: `packages/core/services/runtime.py`
- Test: `tests/integration/test_migrations.py`

- [x] Add `repository_revision_signals` linked to Project, optional WorkItem and reporting User.
- [x] Store provider, repository identity, branch, observed/previous head, signal type and status.

### Task 2: Repository RevisionSignal API

**Files:**

- Modify: `apps/api/routers/integrations.py`
- Test: `tests/integration/api/test_integrations_api.py`

- [x] Add `POST /integrations/repository/revision-signal`.
- [x] Require CI service credential.
- [x] Resolve or create WorkItem by `work_item_key`.
- [x] Compare observed branch head against accepted ContextRevision commit.
- [x] Mark freshness as stale/current/missing.
- [x] Create a submitted refresh ContextProposal when accepted context is stale.

### Task 3: Black-box guide expansion

**Files:**

- Modify: `docs/development/p8-ci-quality-signal-blackbox.zh-CN.md`
- Test: `tests/integration/test_web_config.py`

- [x] Add repository RevisionSignal validation path.
- [x] Explain that Web Context should show the generated refresh ContextProposal.

Verification:

```text
.venv/bin/pytest tests/integration/test_migrations.py::test_p8_repository_revision_signal_schema_links_project_and_work_item tests/integration/test_migrations.py::test_create_app_engine_upgrades_empty_in_memory_database_on_same_engine
# failed first because repository_revision_signals did not exist, then 3 passed

.venv/bin/pytest tests/integration/api/test_integrations_api.py::test_repository_revision_signal_marks_context_stale_and_creates_refresh_proposal
# failed first because /integrations/repository/revision-signal did not exist, then 1 passed

.venv/bin/pytest tests/integration/test_web_config.py::test_p8_ci_quality_signal_blackbox_guide_exists
# failed first because the guide did not mention repository RevisionSignal, then 1 passed
```

## Chunk 3: External task WorkItem mapping

### Task 1: Task link persistence

**Files:**

- Create: `alembic/versions/20260826_0011_p8_work_item_links.py`
- Modify: `packages/core/models.py`
- Modify: `packages/core/repositories/work.py`
- Modify: `packages/core/services/runtime.py`
- Test: `tests/integration/test_migrations.py`

- [x] Add `work_item_links` linked to Project, WorkItem and reporting User.
- [x] Enforce one canonical external task identity per project, provider and external key.
- [x] Expose idempotent upsert and WorkItem-scoped list operations through CoreRuntime.

### Task 2: CI/repository task link ingestion

**Files:**

- Modify: `apps/api/routers/integrations.py`
- Test: `tests/integration/api/test_integrations_api.py`

- [x] Accept `task_provider`, `task_key` and `task_url` on CI QualitySignal.
- [x] Accept `task_provider`, `task_key` and `task_url` on repository RevisionSignal.
- [x] Return `task_link` from both integration endpoints.
- [x] Reuse the same WorkItem and task link when subsequent provider signals reference the same external task.

### Task 3: Project status and black-box guide

**Files:**

- Modify: `packages/harness/service.py`
- Modify: `apps/web/app/projects/[projectId]/status/page.tsx`
- Modify: `docs/development/p8-ci-quality-signal-blackbox.zh-CN.md`
- Test: `tests/integration/test_web_config.py`

- [x] Include `task_links` under each WorkItem in `agora_get_project_status`.
- [x] Render external task links in Web `Project status`.
- [x] Document the AI/CI-driven WorkItem mapping black-box path without requiring manual HTTP calls.

Verification:

```text
.venv/bin/pytest tests/integration/test_migrations.py::test_p8_work_item_links_schema_enforces_project_provider_key_identity tests/integration/api/test_integrations_api.py::test_ci_quality_signal_records_evidence_and_updates_project_status tests/integration/api/test_integrations_api.py::test_repository_revision_signal_reuses_existing_task_link_work_item tests/integration/test_web_config.py::test_project_status_page_is_available_and_linked_from_project_home tests/integration/test_web_config.py::test_p8_ci_quality_signal_blackbox_guide_exists
# failed first because work_item_links/task_link/task_links documentation did not exist, then 5 passed
```

## Chunk 4: PR/MR signal automation

### Task 1: Pull request signal persistence

**Files:**

- Create: `alembic/versions/20260826_0012_p8_pull_request_signals.py`
- Modify: `packages/core/models.py`
- Modify: `packages/core/repositories/integrations.py`
- Modify: `packages/core/services/runtime.py`
- Test: `tests/integration/test_migrations.py`

- [x] Add `pull_request_signals` linked to Project, optional WorkItem and reporting User.
- [x] Store provider, repository identity, PR/MR id/url/title, action, branches and commit SHAs.

### Task 2: Pull request signal API

**Files:**

- Modify: `apps/api/routers/integrations.py`
- Test: `tests/integration/api/test_integrations_api.py`

- [x] Add `POST /integrations/repository/pull-request-signal`.
- [x] Resolve Project from `project_id` when supplied, otherwise from `repository_identity`.
- [x] Resolve WorkItem from explicit key, task URL, branch name or PR/MR title.
- [x] Upsert external task WorkItem mapping when `task_provider` and task identity are present.
- [x] Create a submitted refresh ContextProposal when a merged PR/MR advances the target branch beyond accepted context.

### Task 3: Black-box guide expansion

**Files:**

- Modify: `docs/development/p8-ci-quality-signal-blackbox.zh-CN.md`
- Test: `tests/integration/test_web_config.py`

- [x] Add PR/MR signal validation path.
- [x] Explain that PR/MR merge signals can be quiet unless context refresh requires human review.

Verification:

```text
.venv/bin/pytest tests/integration/test_migrations.py::test_p8_pull_request_signals_schema_links_project_work_item_and_actor tests/integration/api/test_integrations_api.py::test_pull_request_signal_resolves_project_from_repository_and_creates_refresh_proposal tests/integration/test_web_config.py::test_p8_ci_quality_signal_blackbox_guide_exists
# failed first because pull_request_signals and /integrations/repository/pull-request-signal did not exist, then 3 passed
```

### Verification

Run:

```bash
.venv/bin/pytest tests/integration/api/test_auth.py tests/integration/api/test_integrations_api.py tests/integration/api/test_harness_api.py tests/integration/test_web_config.py
.venv/bin/pytest
cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
git diff --check
```
