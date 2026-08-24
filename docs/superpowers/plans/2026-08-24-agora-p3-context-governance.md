# Agora P3 Context Governance Implementation Plan

> Current P3 plan. The older `2026-08-13-agora-p3-context-quality.md` is historical evidence for retrieval/source-ref work and is not the current P3 phase.

**Goal:** Establish trusted, versioned team context for real AI-tool collaboration: AI tools submit ContextProposals, humans approve them into immutable ContextRevisions, and later AI tools can reuse accepted team context.

## Task 1: Context governance persistence and acceptance API

**Files:**

- Create: `alembic/versions/20260824_0003_p3_context_governance.py`
- Create: `packages/core/repositories/context_governance.py`
- Create: `apps/api/routers/context_governance.py`
- Modify: `packages/core/models.py`
- Modify: `packages/core/services/runtime.py`
- Modify: `packages/harness/context_bundle.py`
- Modify: `packages/harness/context_planner.py`
- Modify: `apps/api/main.py`
- Modify: `apps/web/app/projects/[projectId]/context/page.tsx`
- Test: `tests/integration/api/test_context_governance_api.py`
- Test: `tests/integration/test_p3_context_governance_migration.py`
- Test: `tests/integration/test_web_config.py`

- [x] Add ContextStream, immutable ContextRevision, ContextProposal, ApprovalDecision and OutboxEvent schema.
- [x] Allow authenticated project members to submit ContextProposal without creating accepted context directly.
- [x] Allow human reviewers to approve a proposal with expected head and RevisionSignal evidence.
- [x] Mark stale proposals as `needs_rebase` instead of overwriting the current stream head.
- [x] Write `context_head_changed` outbox event during the same transaction as stream head update.
- [x] Make `prepare-context` pin and mark accepted ContextRevision as fresh when one exists.
- [x] Show ContextStreams and ContextProposals in the read-only Context state Web page.

Verification:

```text
.venv/bin/pytest tests/integration/api/test_context_governance_api.py tests/integration/test_p3_context_governance_migration.py -q
# 3 passed

.venv/bin/pytest tests/integration/api/test_context_governance_api.py tests/unit/harness/test_context_bundle.py tests/unit/harness/test_harness_service.py tests/integration/api/test_harness_api.py -q
# 28 passed

.venv/bin/pytest
# 178 passed, 2 skipped

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# compiled successfully

Browser validation
# Context page checked at 1440x900 and 390x844 against local API/Web.
# Context streams and Context proposals visible, accepted proposal visible, no old Context Tester text, no horizontal overflow.
```

## Next P3 tasks

- Add Harness/MCP `agora_submit_context_proposal` for AI tools.
- Add Web proposal detail and review workflow with explicit RevisionSignal display.
- Add outbox consumer retry semantics and idempotent projection updates.
- Add branch-stream rules for feature branch proposals and merge reachability signals.
