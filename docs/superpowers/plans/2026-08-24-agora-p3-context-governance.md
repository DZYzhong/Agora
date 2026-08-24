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

- [x] Add Harness/MCP `agora_submit_context_proposal` for AI tools.
- [x] Add Web proposal detail and review workflow with explicit RevisionSignal display.
- Add outbox consumer retry semantics and idempotent projection updates.
- Add branch-stream rules for feature branch proposals and merge reachability signals.

## Task 2: Real AI-tool ContextProposal upload path

**Files:**

- Modify: `packages/harness/service.py`
- Modify: `apps/api/routers/harness.py`
- Modify: `apps/mcp/server.py`
- Modify: `apps/mcp/tools.py`
- Test: `tests/integration/api/test_context_governance_api.py`
- Test: `tests/unit/mcp/test_stdio_server.py`
- Test: `tests/unit/mcp/test_tools.py`

- [x] Add canonical `/harness/submit-context-proposal` for authenticated AI tools.
- [x] Bind proposal creation to the active WorkSession and WorkItem instead of requiring Web/API callers to pass project internals.
- [x] Keep ContextProposal as review-only state; submitting through Harness does not create accepted ContextRevision.
- [x] Return a protocol envelope with `operation=submit_context_proposal`, current stream head pin and a human review next action.
- [x] Advertise `agora_submit_context_proposal` through the stdio MCP server.
- [x] Add local `AgoraMcpTools.agora_submit_context_proposal` delegation for in-process harness integrations.
- [x] Update start-work capability advertisement so AI tools can see `context_revisions=true` once this P3 path exists.

Verification:

```text
.venv/bin/pytest tests/integration/api/test_context_governance_api.py::test_ai_tool_submits_context_proposal_through_harness_session tests/unit/mcp/test_stdio_server.py::test_stdio_mcp_server_lists_agora_tools tests/unit/mcp/test_stdio_server.py::test_stdio_submit_context_proposal_dispatches_to_harness tests/unit/mcp/test_tools.py::test_mcp_submit_context_proposal_delegates_to_harness
# 4 passed

.venv/bin/pytest tests/integration/api/test_context_governance_api.py tests/unit/mcp/test_stdio_server.py tests/unit/mcp/test_tools.py
# 13 passed

.venv/bin/pytest
# 181 passed, 2 skipped

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# compiled successfully

git diff --check
# passed
```

## Remaining P3 tasks

- Add outbox consumer retry semantics and idempotent projection updates.
- Add branch-stream rules for feature branch proposals and merge reachability signals.

## Task 3: Web ContextProposal review workflow

**Files:**

- Modify: `apps/web/app/projects/[projectId]/context/page.tsx`
- Create: `apps/web/app/projects/[projectId]/context/proposals/[proposalId]/page.tsx`
- Create: `apps/web/app/projects/[projectId]/context/proposals/[proposalId]/approve/route.ts`
- Modify: `apps/web/app/styles.css`
- Test: `tests/integration/test_web_config.py`

- [x] Add a proposal detail link from the Context state page.
- [x] Add proposal detail page with summary, status, stream head, content, `source_anchors` and provenance.
- [x] Add human review form with `Revision signal`, expected head, observed head SHA, `contains_to_commit` and comment fields.
- [x] Add Next route that posts approval to `/projects/{project_id}/context/proposals/{proposal_id}/approve`.
- [x] Surface approval errors back on the proposal detail page.
- [x] Hide the approval form once a proposal is approved.

Verification:

```text
.venv/bin/pytest tests/integration/test_web_config.py::test_product_context_page_is_read_only_audit_view tests/integration/test_web_config.py::test_context_proposal_review_pages_are_available
# 2 passed

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# compiled successfully

Browser validation with temporary SQLite database, local API :18100 and Web :13100
# Context page showed AI-submitted PAY-318 proposal and View proposal link.
# Proposal detail showed Human review, Revision signal, source anchor and default target commit signal.
# Browser approval POST returned to detail page with approved status, accepted revision present and approval form hidden.
# 390x844 mobile viewport showed proposal detail without horizontal overflow.

.venv/bin/pytest
# 182 passed, 2 skipped

cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build
# compiled successfully

git diff --check
# passed
```
