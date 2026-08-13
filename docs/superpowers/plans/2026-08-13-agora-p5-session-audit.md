# Agora P5 Session Audit Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make each AI work session auditable from the Web UI, including context used, skill runs, writebacks produced, lifecycle events, and reviewer-friendly filters.

**Architecture:** Extend the existing session repository/API instead of adding new tables. Session list responses stay compact but include audit counters; session detail responses include the full timeline and linked artifacts. Web adds project-scoped filters plus a dedicated session detail page for black-box review.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, Next.js App Router, pytest.

---

## Chunk 1: Session Audit API

### Task 1: Repository Query Support

**Files:**
- Modify: `packages/core/repositories/sessions.py`
- Modify: `packages/core/repositories/skills.py`
- Modify: `packages/core/repositories/writebacks.py`
- Modify: `packages/core/services/runtime.py`
- Test: `tests/integration/api/test_sessions_api.py`

- [x] **Step 1: Write failing API test**

Create project sessions with different intents/statuses, context packs, skill runs, writebacks, and events. Assert list filters and detail audit payloads return the expected linked artifacts.

- [x] **Step 2: Add repository methods**

Add session filtering by intent/status, session lookup scoped to project, skill runs by session, writebacks by session, and existing ordered event/context pack loading.

- [x] **Step 3: Expose runtime methods**

Expose repository methods through `CoreRuntime`.

### Task 2: Sessions API Responses

**Files:**
- Modify: `apps/api/routers/sessions.py`
- Test: `tests/integration/api/test_sessions_api.py`

- [x] **Step 1: Add query filters**

Support `GET /projects/{project_id}/sessions?intent=&status=&q=` for reviewer filtering.

- [x] **Step 2: Add session detail endpoint**

Add `GET /projects/{project_id}/sessions/{session_id}` returning session metadata, context packs, events, skill runs, writebacks, and audit counters.

- [x] **Step 3: Run targeted API tests**

Run `./.venv/bin/pytest tests/integration/api/test_sessions_api.py -v`.

## Chunk 2: Session Audit Web

### Task 3: Session List Filters

**Files:**
- Modify: `apps/web/app/projects/[projectId]/sessions/page.tsx`
- Modify: `apps/web/app/styles.css`

- [x] **Step 1: Add filter form**

Render intent/status/query filter inputs that submit as URL query params.

- [x] **Step 2: Render audit counters and detail links**

Show event/context/skill/writeback counts and a link to each detail page.

### Task 4: Session Detail Page

**Files:**
- Create: `apps/web/app/projects/[projectId]/sessions/[sessionId]/page.tsx`
- Modify: `apps/web/app/styles.css`

- [x] **Step 1: Render detail header and counters**

Show session identity, status, intent, task, dates, and audit counters.

- [x] **Step 2: Render linked audit sections**

Show context packs, skill runs, writebacks, and event timeline in one page.

- [x] **Step 3: Run Web build**

Run `cd apps/web && npm run build`.

## Chunk 3: Roadmap and Black-box Validation

### Task 5: Durable Log

**Files:**
- Modify: `docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`
- Modify: `docs/superpowers/plans/2026-08-13-agora-p5-session-audit.md`

- [x] **Step 1: Run full verification**

Run:

```bash
.venv/bin/pytest -q
cd apps/web && npm run build
```

- [x] **Step 2: Prepare black-box fixture**

Create a project with multiple sessions, context planning, a skill run, and writebacks so the user can verify the full audit page from the browser.

- [x] **Step 3: Update roadmap**

Record implementation scope, tests, commit, and black-box validation path.
