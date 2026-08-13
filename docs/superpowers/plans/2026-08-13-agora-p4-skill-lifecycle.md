# Agora P4 Skill Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Agora skills from a static built-in list into reviewable, versioned workflow assets that can be created, approved, run, and inspected through API/Web.

**Architecture:** Use the existing `SkillModel` and `SkillRunModel` tables. Add repository/service/API layers for lifecycle actions, keep built-in skill seeding lazy and idempotent, and expose a project-scoped Web management page with forms for create/edit/approve/deprecate/run/history.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, Next.js App Router, pytest.

---

## Chunk 1: Skill Lifecycle API

### Task 1: Repository and Service

**Files:**
- Create: `packages/core/repositories/skills.py`
- Modify: `packages/core/services/runtime.py`
- Modify: `packages/core/services/skills.py`
- Test: `tests/integration/api/test_skills_api.py`

- [x] **Step 1: Write failing API test**

Cover project skill creation, list, update, approve, deprecate, run, and run history.

- [x] **Step 2: Add repository**

Implement skill CRUD, project-scoped listing with built-ins, status transitions, and skill run listing.

- [x] **Step 3: Add runtime/service methods**

Expose repository methods through CoreRuntime and helpers.

### Task 2: Skills API

**Files:**
- Create: `apps/api/routers/skills.py`
- Modify: `apps/api/main.py`
- Test: `tests/integration/api/test_skills_api.py`

- [x] **Step 1: Create router**

Add endpoints:

- `GET /projects/{project_id}/skills`
- `POST /projects/{project_id}/skills`
- `PATCH /projects/{project_id}/skills/{skill_id}`
- `POST /projects/{project_id}/skills/{skill_id}/approve`
- `POST /projects/{project_id}/skills/{skill_id}/deprecate`
- `POST /projects/{project_id}/skills/{skill_id}/run`
- `GET /projects/{project_id}/skill-runs`

- [x] **Step 2: Run API tests**

Run targeted test and full pytest.

## Chunk 2: Skill Lifecycle Web

### Task 3: Project Skills Page

**Files:**
- Modify: `apps/web/app/projects/[projectId]/skills/page.tsx`
- Create: `apps/web/app/projects/[projectId]/skills/create/route.ts`
- Create: `apps/web/app/projects/[projectId]/skills/[skillId]/update/route.ts`
- Create: `apps/web/app/projects/[projectId]/skills/[skillId]/approve/route.ts`
- Create: `apps/web/app/projects/[projectId]/skills/[skillId]/deprecate/route.ts`
- Create: `apps/web/app/projects/[projectId]/skills/[skillId]/run/route.ts`
- Modify: `apps/web/app/styles.css`

- [x] **Step 1: Render lifecycle controls**

Show built-in and project skills, status badges, definitions, run history, and create/update/approve/deprecate/run forms.

- [x] **Step 2: Add server action routes**

Wire form posts to the Skills API and revalidate the skills page.

- [x] **Step 3: Run Web build**

Run `cd apps/web && npm run build`.

## Chunk 3: P4 Log and Validation

### Task 4: Candidate Skills from Accepted Writebacks

**Files:**
- Modify: `packages/core/repositories/writebacks.py`
- Modify: `packages/core/services/runtime.py`
- Modify: `packages/harness/memory_writeback.py`
- Modify: `tests/integration/api/test_skills_api.py`

- [x] **Step 1: Write failing candidate creation test**

Accept two writebacks of the same type and assert a candidate project skill appears.

- [x] **Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/pytest tests/integration/api/test_skills_api.py::test_repeated_accepted_writebacks_create_candidate_skill -v
```

Expected: FAIL because accepted writebacks do not generate candidate skills yet.

- [x] **Step 3: Generate candidate skill on repeated accepted writebacks**

After accepting a writeback, if two or more accepted writebacks of the same project/type exist, create one candidate skill derived from that writeback type.

- [x] **Step 4: Run tests and build**

Run:

```bash
.venv/bin/pytest -q
cd apps/web && npm run build
```

Expected: PASS.

### Task 5: Verification and Roadmap

**Files:**
- Modify: `docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`
- Modify: `docs/superpowers/plans/2026-08-13-agora-p4-skill-lifecycle.md`

- [ ] **Step 1: Run full verification**

Run:

```bash
.venv/bin/pytest -q
cd apps/web && npm run build
```

- [ ] **Step 2: Update roadmap**

Record implementation scope, tests, commit, and black-box validation path.
