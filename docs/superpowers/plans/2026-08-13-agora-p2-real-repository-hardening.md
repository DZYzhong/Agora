# Agora P2 Real Repository Trial Hardening Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make repository initialization safe to run repeatedly on real repositories without duplicate knowledge pollution, while recording useful diagnostics about skipped files and initialization results.

**Architecture:** Keep the current synchronous local initialization path. Add deterministic analyzer diagnostics, content hashes, and repository-level upsert semantics before introducing background queues or production index services.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite, Pydantic, pytest.

---

## Chunk 1: Idempotent Repository Initialization

### Task 1: Asset Upsert by Project and Source URI

**Files:**
- Modify: `packages/core/repositories/assets.py`
- Test: `tests/unit/core/test_repositories.py`

- [x] **Step 1: Write failing repository test**

Add a test proving that `AssetRepository.upsert_by_source_uri` updates an existing project asset instead of creating a duplicate.

- [x] **Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/pytest tests/unit/core/test_repositories.py -v
```

Expected: FAIL because `upsert_by_source_uri` does not exist.

- [x] **Step 3: Implement asset upsert**

Add `find_by_project_source_uri` and `upsert_by_source_uri` methods. Matching key is `project_id + source_uri`. Updated fields should include type, source, title, content, summary, metadata, and content_hash.

- [x] **Step 4: Run test**

Run:

```bash
.venv/bin/pytest tests/unit/core/test_repositories.py -v
```

Expected: PASS.

### Task 2: Use Upsert During Project Initialization

**Files:**
- Modify: `apps/api/routers/projects.py`
- Test: `tests/integration/api/test_initialization_jobs.py`

- [x] **Step 1: Write failing API test**

Add a test that initializes the same project twice and asserts the project asset count remains stable.

- [x] **Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/pytest tests/integration/api/test_initialization_jobs.py -v
```

Expected: FAIL because initialization currently creates duplicate assets.

- [x] **Step 3: Replace create with upsert**

Use `AssetRepository.upsert_by_source_uri` in `initialize_local_project`. Re-index the returned stored asset after upsert.

- [x] **Step 4: Run targeted tests**

Run:

```bash
.venv/bin/pytest tests/integration/api/test_initialization_jobs.py -v
```

Expected: PASS.

---

## Chunk 2: Real Repository Skip Rules and Diagnostics

### Task 3: Analyzer Diagnostics

**Files:**
- Modify: `packages/integrations/git/analyzer.py`
- Modify: `apps/workers/workflows/initialize_project.py`
- Test: `tests/unit/integrations/test_git_analyzer.py`
- Test: `tests/integration/workers/test_initialize_project.py`

- [x] **Step 1: Write failing analyzer tests**

Add fixture files for generated, large, hidden, and binary-like content. Assert that analysis reports skipped file count and warnings while excluding skipped files from `source_files`.

- [x] **Step 2: Run tests to verify failure**

Run:

```bash
.venv/bin/pytest tests/unit/integrations/test_git_analyzer.py tests/integration/workers/test_initialize_project.py -v
```

Expected: FAIL because diagnostics are not implemented.

- [x] **Step 3: Implement diagnostics**

Extend `RepositoryAnalysis` with:

- `scanned_file_count`
- `skipped_file_count`
- `warnings`

Skip files when:

- path contains ignored directories
- file is larger than a conservative local threshold
- file extension is not a supported source extension
- file cannot be read as UTF-8 when ingestion attempts to read it

- [x] **Step 4: Propagate warnings**

Return analyzer warnings from `InitializeProjectResult.warnings`.

- [x] **Step 5: Run targeted tests**

Run:

```bash
.venv/bin/pytest tests/unit/integrations/test_git_analyzer.py tests/integration/workers/test_initialize_project.py -v
```

Expected: PASS.

### Task 4: Persist Initialization Diagnostics

**Files:**
- Modify: `packages/core/models.py`
- Modify: `packages/core/repositories/initialization_jobs.py`
- Modify: `apps/api/routers/projects.py`
- Test: `tests/integration/api/test_initialization_jobs.py`

- [x] **Step 1: Write failing diagnostics test**

Assert initialization job responses include warnings from repository analysis.

- [x] **Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/pytest tests/integration/api/test_initialization_jobs.py -v
```

Expected: FAIL because job diagnostics are incomplete.

- [x] **Step 3: Persist warnings and counts**

Use existing `warnings` and `asset_count` job fields for P2. Defer schema expansion for scanned/skipped counts until Alembic is introduced, but include counts in warnings text and initialization response.

- [x] **Step 4: Run targeted tests**

Run:

```bash
.venv/bin/pytest tests/integration/api/test_initialization_jobs.py -v
```

Expected: PASS.

### Task 5: Retry Failed Initialization Jobs

**Files:**
- Modify: `apps/api/routers/projects.py`
- Modify: `packages/core/repositories/initialization_jobs.py`
- Modify: `apps/web/app/projects/[projectId]/page.tsx`
- Modify: `apps/web/app/styles.css`
- Create: `apps/web/app/projects/[projectId]/initialization-jobs/[jobId]/retry/route.ts`
- Test: `tests/integration/api/test_initialization_jobs.py`

- [x] **Step 1: Write failing retry API test**

Add a test that creates a failed initialization job, fixes the repository path, retries the failed job, and asserts a new completed job appears above the failed job.

- [x] **Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/pytest tests/integration/api/test_initialization_jobs.py -v
```

Expected: FAIL because retry endpoint does not exist.

- [x] **Step 3: Implement retry API**

Add `POST /projects/{project_id}/initialization-jobs/{job_id}/retry`, only allowing retries for failed jobs. Retry creates a new job using the failed job's original repository path.

- [x] **Step 4: Add Web retry action**

Show a `Retry` button for failed initialization history rows. The route handler calls the retry API and redirects back to project detail.

- [x] **Step 5: Run targeted and full tests**

Run:

```bash
.venv/bin/pytest tests/integration/api/test_initialization_jobs.py -v
.venv/bin/pytest -q
cd apps/web && npm run build
```

Expected: PASS.

### Task 6: Prune Stale Repository Assets

**Files:**
- Modify: `apps/api/routers/projects.py`
- Modify: `packages/core/repositories/assets.py`
- Test: `tests/integration/api/test_initialization_jobs.py`

- [x] **Step 1: Write failing stale asset test**

Add a test that initializes a temporary repository, deletes one source file, re-initializes the same project, and asserts the deleted file no longer appears in project assets.

- [x] **Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/pytest tests/integration/api/test_initialization_jobs.py::test_reinitialize_prunes_git_assets_removed_from_repository -v
```

Expected: FAIL because stale git assets are not pruned.

- [x] **Step 3: Implement pruning**

Add `AssetRepository.prune_project_sources(project_id, managed_source_uris)`. After successful upsert during initialization, delete initialization-managed assets whose source URI is no longer present.

- [x] **Step 4: Run targeted and full tests**

Run:

```bash
.venv/bin/pytest tests/integration/api/test_initialization_jobs.py::test_reinitialize_prunes_git_assets_removed_from_repository -v
.venv/bin/pytest -q
cd apps/web && npm run build
```

Expected: PASS.

---

## Chunk 3: Verification and Roadmap Log

### Task 7: Final Verification and Roadmap Update

**Files:**
- Modify: `docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`

- [ ] **Step 1: Run full Python tests**

Run:

```bash
.venv/bin/pytest -q
```

Expected: PASS.

- [ ] **Step 2: Run Web build**

Run:

```bash
cd apps/web && npm run build
```

Expected: PASS.

- [ ] **Step 3: Update roadmap execution log**

Append the P2 work summary, changed files, tests, and commit status to `docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`.

- [ ] **Step 4: Commit**

```bash
git add apps packages tests docs/superpowers/plans
git commit -m "feat: harden repository initialization"
```
