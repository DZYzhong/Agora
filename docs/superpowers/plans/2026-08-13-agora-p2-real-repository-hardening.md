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

- [ ] **Step 1: Write failing repository test**

Add a test proving that `AssetRepository.upsert_by_source_uri` updates an existing project asset instead of creating a duplicate.

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/pytest tests/unit/core/test_repositories.py -v
```

Expected: FAIL because `upsert_by_source_uri` does not exist.

- [ ] **Step 3: Implement asset upsert**

Add `find_by_project_source_uri` and `upsert_by_source_uri` methods. Matching key is `project_id + source_uri`. Updated fields should include type, source, title, content, summary, metadata, and content_hash.

- [ ] **Step 4: Run test**

Run:

```bash
.venv/bin/pytest tests/unit/core/test_repositories.py -v
```

Expected: PASS.

### Task 2: Use Upsert During Project Initialization

**Files:**
- Modify: `apps/api/routers/projects.py`
- Test: `tests/integration/api/test_initialization_jobs.py`

- [ ] **Step 1: Write failing API test**

Add a test that initializes the same project twice and asserts the project asset count remains stable.

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/pytest tests/integration/api/test_initialization_jobs.py -v
```

Expected: FAIL because initialization currently creates duplicate assets.

- [ ] **Step 3: Replace create with upsert**

Use `AssetRepository.upsert_by_source_uri` in `initialize_local_project`. Re-index the returned stored asset after upsert.

- [ ] **Step 4: Run targeted tests**

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

- [ ] **Step 1: Write failing analyzer tests**

Add fixture files for generated, large, hidden, and binary-like content. Assert that analysis reports skipped file count and warnings while excluding skipped files from `source_files`.

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
.venv/bin/pytest tests/unit/integrations/test_git_analyzer.py tests/integration/workers/test_initialize_project.py -v
```

Expected: FAIL because diagnostics are not implemented.

- [ ] **Step 3: Implement diagnostics**

Extend `RepositoryAnalysis` with:

- `scanned_file_count`
- `skipped_file_count`
- `warnings`

Skip files when:

- path contains ignored directories
- file is larger than a conservative local threshold
- file extension is not a supported source extension
- file cannot be read as UTF-8 when ingestion attempts to read it

- [ ] **Step 4: Propagate warnings**

Return analyzer warnings from `InitializeProjectResult.warnings`.

- [ ] **Step 5: Run targeted tests**

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

- [ ] **Step 1: Write failing diagnostics test**

Assert initialization job responses include warnings from repository analysis.

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/pytest tests/integration/api/test_initialization_jobs.py -v
```

Expected: FAIL because job diagnostics are incomplete.

- [ ] **Step 3: Persist warnings and counts**

Use existing `warnings` and `asset_count` job fields for P2. Defer schema expansion for scanned/skipped counts until Alembic is introduced, but include counts in warnings text and initialization response.

- [ ] **Step 4: Run targeted tests**

Run:

```bash
.venv/bin/pytest tests/integration/api/test_initialization_jobs.py -v
```

Expected: PASS.

---

## Chunk 3: Verification and Roadmap Log

### Task 5: Final Verification and Roadmap Update

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
