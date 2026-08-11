# Agora P1 Team Trial Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move Agora from a local P0 demo into a team-trial build where project data survives restarts, initialization is trackable, and AI tools can reliably reuse project context.

**Architecture:** Keep the current FastAPI + SQLAlchemy + Next.js shape. Replace volatile runtime state first, then add task state and richer project overview APIs without introducing production-only infrastructure too early. Use file SQLite and local fake indexes as the P1 baseline, with repository APIs isolated so Postgres/Qdrant/OpenSearch can replace them later.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite file database, Next.js App Router, stdio MCP, pytest.

---

## Chunk 1: Persistent Local Runtime

### Task 1: File SQLite Database

**Files:**
- Modify: `apps/api/dependencies.py`
- Create: `tests/integration/api/test_persistence.py`
- Modify: `docs/development/p0-usage-guide.zh-CN.md`

- [x] **Step 1: Write failing persistence test**

```python
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import create_app_engine
from packages.core.database import Base
import packages.core.models  # noqa: F401
from packages.core.repositories.projects import ProjectRepository


def test_file_sqlite_engine_persists_projects_across_engine_recreation(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"
    first_engine = create_app_engine(database_url)
    Base.metadata.create_all(first_engine)
    first_session = sessionmaker(bind=first_engine)()
    project = ProjectRepository(first_session).create(
        org_id="org_1",
        name="Persisted",
        slug="persisted",
        git_remotes=["git@example.com:persisted.git"],
    )
    first_session.close()
    first_engine.dispose()

    second_engine = create_app_engine(database_url)
    Base.metadata.create_all(second_engine)
    second_session = sessionmaker(bind=second_engine)()
    loaded = ProjectRepository(second_session).get(project.id)

    assert loaded is not None
    assert loaded.slug == "persisted"
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/integration/api/test_persistence.py -v`

- [x] **Step 3: Implement configurable database URL**

Add:
- `AGORA_DATABASE_URL` support.
- Default file DB at `.agora/agora.db`.
- `create_app_engine(database_url)` helper.
- `StaticPool` only for explicit in-memory SQLite.

- [x] **Step 4: Run persistence and full tests**

Run:
- `.venv/bin/pytest tests/integration/api/test_persistence.py -v`
- `.venv/bin/pytest -v`

- [x] **Step 5: Update docs**

Document:
- default DB file path
- how to reset local state by deleting `.agora/agora.db`
- how to override with `AGORA_DATABASE_URL`

- [x] **Step 6: Commit**

```bash
git add apps/api/dependencies.py tests/integration/api/test_persistence.py docs/development/p0-usage-guide.zh-CN.md
git commit -m "feat: persist Agora local database"
```

### Task 2: Rehydrate In-Memory Search Indexes

**Files:**
- Modify: `apps/api/dependencies.py`
- Create: `packages/knowledge/index_rebuilder.py`
- Create: `tests/integration/api/test_index_rehydration.py`

- [x] Write a failing test proving assets persisted in DB can be found by `plan_context` after fake indexes are recreated.
- [x] Implement `rebuild_indexes_from_assets(session, keyword_index, vector_index)`.
- [x] Call it once after engine initialization for local fake indexes.
- [x] Run targeted and full tests.
- [x] Commit.

## Chunk 2: Initialization Jobs

### Task 3: Initialization Job Model

**Files:**
- Modify: `packages/core/models.py`
- Create: `packages/core/repositories/initialization_jobs.py`
- Modify: `apps/api/routers/projects.py`
- Create: `tests/integration/api/test_initialization_jobs.py`

- [x] Add `ProjectInitializationJobModel` with status, repo_path, git_remote, asset_count, error, timestamps.
- [x] Make initialize API create and update a job.
- [x] Return `job_id` and status from initialize endpoint.
- [x] Add `GET /projects/{project_id}/initialization-jobs`.
- [x] Commit.

### Task 4: Web Initialization Status

**Files:**
- Modify: `apps/web/app/projects/[projectId]/page.tsx`
- Create/modify route handlers as needed.
- Modify: `apps/web/app/styles.css`

- [x] Show latest initialization status on project detail.
- [x] Link to assets after success.
- [x] Show clone/analyze errors in page.
- [x] Run `npm run build`.
- [x] Commit.

## Chunk 3: Project Overview and Agent Usability

### Task 5: Project Overview Asset

**Files:**
- Create: `packages/knowledge/project_overview.py`
- Modify: `apps/workers/workflows/initialize_project.py`
- Create: `tests/unit/knowledge/test_project_overview.py`

- [x] Generate a concise overview from modules, dependency files, source paths, and test paths.
- [x] Store overview as a `project_overview` asset.
- [x] Prefer overview in broad query fallback.
- [x] Commit.

### Task 6: Web Context Tester

**Files:**
- Create: `apps/web/app/projects/[projectId]/context/page.tsx`
- Create: `apps/web/app/projects/[projectId]/context/route.ts`
- Modify: `apps/web/app/projects/[projectId]/page.tsx`

- [x] Add a simple query form.
- [x] Call `/harness/start-work` and `/harness/plan-context`.
- [x] Show summary and source refs.
- [x] Commit.

## Chunk 4: Writeback Review

### Task 7: Web Accept/Reject Writebacks

**Files:**
- Modify: `apps/web/app/projects/[projectId]/writebacks/page.tsx`
- Add route handlers for accept/reject.

- [x] Add accept/reject buttons.
- [x] Show accepted asset id.
- [x] Verify accepted writeback becomes searchable.
- [x] Commit.

## Verification

Before marking P1 complete:

```bash
.venv/bin/pytest -v
cd apps/web && npm run build
.venv/bin/python scripts/run_p0_demo.py
```

Manual smoke:

1. Start API with default DB.
2. Create and initialize a project.
3. Stop API and restart.
4. Confirm project and assets still exist.
5. Ask an AI tool to call Agora by project name.
6. Confirm plan context returns source refs.
