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

---

## Chunk 2: Verification and Roadmap Log

### Task 6: Final Verification

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

- [ ] **Step 3: Commit**

```bash
git add apps packages tests docs/superpowers/plans
git commit -m "feat: fetch context source references"
```
