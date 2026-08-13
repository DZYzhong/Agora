# Agora P3 Context Quality Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve Agora's context quality and traceability so users and AI agents can inspect source references instead of only receiving summaries.

**Architecture:** Keep the current fake keyword/vector indexes and persisted SQLite assets. Add a focused source-reference retrieval path first, then use it from API, MCP, and Web without introducing new index infrastructure.

**Tech Stack:** FastAPI, SQLAlchemy, Next.js App Router, pytest, stdio MCP.

---

## Chunk 1: Fetch Context Source References

### Task 1: Backend Source Reference Fetch

**Files:**
- Modify: `packages/core/services/runtime.py`
- Modify: `packages/harness/service.py`
- Modify: `apps/api/routers/harness.py`
- Test: `tests/integration/api/test_harness_api.py`

- [x] **Step 1: Write failing API test**

Add a test that starts a session, plans context, takes a source `asset_id`, calls `POST /harness/fetch-context-ref`, and asserts the returned content matches the source asset.

- [x] **Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/pytest tests/integration/api/test_harness_api.py -v
```

Expected: FAIL because fetch-context-ref endpoint does not exist.

- [x] **Step 3: Implement harness method**

Add `HarnessService.fetch_context_ref(session_id, asset_id, max_tokens)`:

- Validate the session exists.
- Load the asset by ID.
- Ensure asset belongs to the session project.
- Return asset metadata, title, source URI, and truncated content.

- [x] **Step 4: Expose API endpoint**

Add `POST /harness/fetch-context-ref`.

- [x] **Step 5: Run targeted test**

Run:

```bash
.venv/bin/pytest tests/integration/api/test_harness_api.py -v
```

Expected: PASS.

### Task 2: MCP Source Reference Fetch

**Files:**
- Modify: `apps/mcp/server.py`
- Modify: `apps/mcp/tools.py`
- Test: `tests/unit/mcp/test_tools.py`
- Test: `tests/unit/mcp/test_stdio_server.py`

- [x] **Step 1: Write failing MCP tests**

Assert MCP dispatch calls `/harness/fetch-context-ref`, and local `AgoraMcpTools.agora_fetch_context_ref` delegates to harness when available.

- [x] **Step 2: Run tests to verify failure**

Run:

```bash
.venv/bin/pytest tests/unit/mcp/test_tools.py tests/unit/mcp/test_stdio_server.py -v
```

Expected: FAIL because current fetch returns placeholder content.

- [x] **Step 3: Implement MCP fetch**

Update MCP schema to use `asset_id` and call the API endpoint.

- [x] **Step 4: Run MCP tests**

Run:

```bash
.venv/bin/pytest tests/unit/mcp/test_tools.py tests/unit/mcp/test_stdio_server.py -v
```

Expected: PASS.

### Task 3: Web Source Reference Detail

**Files:**
- Modify: `apps/web/app/projects/[projectId]/context/page.tsx`
- Create: `apps/web/app/projects/[projectId]/context/source/[assetId]/page.tsx`
- Modify: `apps/web/app/styles.css`

- [x] **Step 1: Add source detail page**

Create a page that starts from `session_id`, calls `/harness/fetch-context-ref`, and shows source title, URI, asset ID, and content.

- [x] **Step 2: Link source refs**

Context Tester source rows should link to the detail page with current `session_id`.

- [x] **Step 3: Run Web build**

Run:

```bash
cd apps/web && npm run build
```

Expected: PASS.

### Task 4: Source Reference Previews

**Files:**
- Modify: `packages/knowledge/context_engine.py`
- Modify: `tests/unit/knowledge/test_context_engine.py`
- Modify: `apps/web/app/projects/[projectId]/context/page.tsx`
- Modify: `apps/web/app/styles.css`

- [x] **Step 1: Write failing preview test**

Assert every ContextPack source ref includes a short `preview` field.

- [x] **Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/pytest tests/unit/knowledge/test_context_engine.py::test_context_engine_generates_traceable_context_pack -v
```

Expected: FAIL because source refs do not include previews.

- [x] **Step 3: Add preview generation**

Use the first sentence of source content, truncated to a short preview length.

- [x] **Step 4: Render previews in Web**

Show preview text in Context Tester source rows.

- [x] **Step 5: Run tests and build**

Run:

```bash
.venv/bin/pytest -q
cd apps/web && npm run build
```

Expected: PASS.

### Task 5: Source Reference Chunk Spans

**Files:**
- Modify: `packages/knowledge/context_engine.py`
- Modify: `tests/unit/knowledge/test_context_engine.py`
- Modify: `apps/web/app/projects/[projectId]/context/page.tsx`
- Modify: `apps/web/app/styles.css`

- [x] **Step 1: Write failing chunk/span test**

Assert each ContextPack source ref includes a stable `chunk_id` and `source_span`.

- [x] **Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/pytest tests/unit/knowledge/test_context_engine.py::test_context_engine_generates_traceable_context_pack -v
```

Expected: FAIL because source refs do not include chunk/span fields.

- [x] **Step 3: Add asset-level chunk/span metadata**

Generate stable `asset_id:chunk:0` chunk IDs and source spans with line and character ranges.

- [x] **Step 4: Render chunk/span metadata in Web**

Show chunk ID and source line range in Context Tester source rows.

- [x] **Step 5: Run tests and build**

Run:

```bash
.venv/bin/pytest -q
cd apps/web && npm run build
```

Expected: PASS.

### Task 6: Intent-Aware Retrieval Boosts

**Files:**
- Modify: `packages/knowledge/context_engine.py`
- Modify: `packages/knowledge/retrieval.py`
- Modify: `packages/storage/opensearch/fake.py`
- Modify: `packages/storage/qdrant/fake.py`
- Modify: `tests/unit/knowledge/test_context_engine.py`
- Modify: `apps/web/app/projects/[projectId]/context/page.tsx`

- [x] **Step 1: Write failing intent ranking test**

Assert implementation intent ranks a matching `code_file` before a matching `writeback`, while risk intent ranks a matching `writeback` first.

- [x] **Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/pytest tests/unit/knowledge/test_context_engine.py::test_context_engine_boosts_sources_by_intent -v
```

Expected: FAIL because writeback's fixed score boost wins for implementation intent.

- [x] **Step 3: Carry asset type through retrieval**

Add `asset_type` to fake keyword/vector results and merged `SearchCandidate`.

- [x] **Step 4: Re-rank by intent**

Apply lightweight ContextEngine boosts for implementation, review, testing, docs, risk, and analysis intents.

- [x] **Step 5: Render asset type in Web**

Show asset type next to retrieval source labels in Context Tester source rows.

- [x] **Step 6: Run tests and build**

Run:

```bash
.venv/bin/pytest -q
cd apps/web && npm run build
```

Expected: PASS.

### Task 7: Matching Chunk Source References

**Files:**
- Modify: `packages/knowledge/context_engine.py`
- Modify: `tests/unit/knowledge/test_context_engine.py`

- [x] **Step 1: Write failing matching chunk test**

Assert a query that matches a later paragraph returns `chunk:1`, that paragraph's line/character span, and that paragraph's preview.

- [x] **Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/pytest tests/unit/knowledge/test_context_engine.py::test_context_engine_source_ref_points_to_matching_chunk -v
```

Expected: FAIL because source refs still use asset-level `chunk:0` spans.

- [x] **Step 3: Add query-matched chunk selection**

Split source content into paragraph chunks, compute chunk spans, and choose the chunk with the highest query token overlap.

- [x] **Step 4: Keep existing source ref contract**

Continue returning `asset_id`, `asset_type`, `chunk_id`, `source_span`, `preview`, `relevance`, and `retrieval_sources`.

- [x] **Step 5: Run tests and build**

Run:

```bash
.venv/bin/pytest -q
cd apps/web && npm run build
```

Expected: PASS.

### Task 8: Context Levels and Chunk Facts

**Files:**
- Modify: `packages/knowledge/context_engine.py`
- Modify: `tests/unit/knowledge/test_context_engine.py`
- Modify: `apps/web/app/projects/[projectId]/context/page.tsx`
- Modify: `apps/web/app/projects/[projectId]/context/source/[assetId]/page.tsx`
- Modify: `apps/web/app/styles.css`

- [x] **Step 1: Write failing level/key-fact tests**

Assert ContextPack `level` reflects the top source type and key facts reference chunk IDs.

- [x] **Step 2: Run tests to verify failure**

Run:

```bash
.venv/bin/pytest tests/unit/knowledge/test_context_engine.py -v
```

Expected: FAIL because ContextPack level is fixed and key facts still reference raw asset IDs.

- [x] **Step 3: Implement semantic levels and chunk facts**

Infer `overview`, `module`, `source`, `memory`, or `empty` from ranked candidates and build key facts from source ref previews/chunk IDs.

- [x] **Step 4: Expose level and key facts in Web**

Show Context level and Key facts on Context Tester.

- [x] **Step 5: Carry chunk/span into source detail links**

Add `chunk_id`, `start_line`, and `end_line` query params to `View source` links and display them on the source detail page.

- [x] **Step 6: Run tests and build**

Run:

```bash
.venv/bin/pytest -q
cd apps/web && npm run build
```

Expected: PASS.

### Task 9: Retrieval Evaluation Fixture

**Files:**
- Create: `tests/unit/knowledge/test_context_retrieval_eval.py`

- [x] **Step 1: Add retrieval evaluation fixture**

Create a focused evaluation-style test covering overview, source, memory, and chunk fact behavior with one indexed project fixture.

- [x] **Step 2: Run evaluation test**

Run:

```bash
.venv/bin/pytest tests/unit/knowledge/test_context_retrieval_eval.py -v
```

Expected: PASS.

- [x] **Step 3: Run full verification**

Run:

```bash
.venv/bin/pytest -q
cd apps/web && npm run build
```

Expected: PASS.

### Task 10: Overview Query Intent Fix

**Files:**
- Modify: `packages/harness/task_resolver.py`
- Modify: `tests/unit/harness/test_harness_service.py`
- Modify: `tests/unit/knowledge/test_context_engine.py`

- [x] **Step 1: Reproduce with failing tests**

Assert `介绍一下这个项目` starts work with `analysis` intent and broad overview queries rank Project Overview first even when docs/code files match.

- [x] **Step 2: Run target tests**

Run:

```bash
.venv/bin/pytest tests/unit/harness/test_harness_service.py::test_start_work_infers_analysis_intent_for_project_overview_request tests/unit/knowledge/test_context_engine.py::test_context_engine_prefers_project_overview_for_broad_query_even_with_matching_files -v
```

Expected: FAIL for intent inference before the fix.

- [x] **Step 3: Fix intent inference**

Classify English overview/summarize/analyze requests and Chinese introduction/overview/core-module/business-flow requests as `analysis`.

- [x] **Step 4: Run related and full verification**

Run:

```bash
.venv/bin/pytest tests/unit/harness/test_harness_service.py tests/unit/knowledge/test_context_engine.py tests/unit/knowledge/test_context_retrieval_eval.py -v
.venv/bin/pytest -q
cd apps/web && npm run build
```

Expected: PASS.

### Task 11: Persisted ContextPack Session Timeline

**Files:**
- Create: `packages/core/repositories/context_packs.py`
- Modify: `packages/core/services/runtime.py`
- Modify: `packages/harness/context_planner.py`
- Modify: `apps/api/routers/sessions.py`
- Modify: `apps/web/app/projects/[projectId]/sessions/page.tsx`
- Modify: `apps/web/app/styles.css`
- Modify: `tests/integration/api/test_harness_api.py`

- [x] **Step 1: Write failing API timeline test**

Assert `POST /harness/plan-context` persists a ContextPack and `/projects/{project_id}/sessions` returns it under the session with a `context_planned` event.

- [x] **Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/pytest tests/integration/api/test_harness_api.py::test_plan_context_persists_context_pack_on_session_timeline -v
```

Expected: FAIL because sessions do not expose context packs yet.

- [x] **Step 3: Add ContextPack repository/runtime methods**

Persist generated ContextPacks using their generated IDs and load packs by event IDs.

- [x] **Step 4: Persist and record during planning**

After ContextEngine returns a pack, save it and record `context_planned` with pack ID, level, and source count.

- [x] **Step 5: Expose timeline in API/Web**

Return context packs from the sessions API and render level, summary, key facts, and source count on the Sessions page.

- [x] **Step 6: Run tests and build**

Run:

```bash
.venv/bin/pytest -q
cd apps/web && npm run build
```

Expected: PASS.

---

## Chunk 2: Verification and Roadmap Log

### Task 12: Final Verification

**Files:**
- Modify: `docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`

- [x] **Step 1: Run full tests**

Run:

```bash
.venv/bin/pytest -q
cd apps/web && npm run build
```

Expected: PASS.

- [x] **Step 2: Update roadmap**

Record implementation, tests, commit, and black-box validation steps.

- [x] **Step 3: Commit**

```bash
git add apps/web/app/projects/[projectId]/context/page.tsx apps/web/app/styles.css packages/knowledge/context_engine.py tests/unit/knowledge/test_context_engine.py docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md docs/superpowers/plans/2026-08-13-agora-p3-context-quality.md
git commit -m "feat: add context source spans"

git add apps/web/app/projects/[projectId]/context/page.tsx packages/knowledge/context_engine.py packages/knowledge/retrieval.py packages/storage/opensearch/fake.py packages/storage/qdrant/fake.py tests/unit/knowledge/test_context_engine.py docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md docs/superpowers/plans/2026-08-13-agora-p3-context-quality.md
git commit -m "feat: rank context sources by intent"
```
