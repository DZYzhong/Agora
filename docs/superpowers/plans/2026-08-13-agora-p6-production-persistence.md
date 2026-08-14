# Agora P6 Production Persistence Implementation Plan

> Historical pre-realignment plan. Its delivered work remains valid implementation evidence, but it does not define the current P6 phase. See `2026-08-13-agora-p1-p9-roadmap.md`.

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare Agora persistence for a production-like deployment path while keeping local SQLite development fast and reversible.

**Architecture:** Add Alembic as the schema authority, keep `AGORA_DATABASE_URL` as the runtime database switch, and expose local admin commands for index rebuild and SQLite reset. Real Qdrant/OpenSearch adapters remain behind future P6 chunks.

**Tech Stack:** Alembic, SQLAlchemy, SQLite, optional Postgres URL configuration, pytest.

---

## Chunk 1: Migration and Local Admin Baseline

### Task 1: Alembic Schema Baseline

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`
- Create: `alembic/versions/20260813_0001_initial_schema.py`
- Test: `tests/integration/test_migrations.py`

- [x] **Step 1: Write failing migration test**

Assert `alembic upgrade head` creates all current model tables on a fresh temporary SQLite database.

- [x] **Step 2: Add Alembic environment and initial revision**

Create the migration environment and first revision matching the current SQLAlchemy models.

- [x] **Step 3: Preserve runtime override behavior**

Allow `AGORA_DATABASE_URL` to drive default migrations while still letting tests override `sqlalchemy.url` explicitly.

### Task 2: Local Admin CLI

**Files:**
- Create: `scripts/agora_admin.py`
- Test: `tests/integration/test_admin_cli.py`

- [x] **Step 1: Write failing CLI tests**

Assert `rebuild-indexes` reports persisted asset count and `reset-local` recreates an empty SQLite schema.

- [x] **Step 2: Implement rebuild command**

Load persisted assets and rebuild fake keyword/vector indexes through the existing index rebuilder.

- [x] **Step 3: Implement guarded local reset**

Support only file-backed SQLite URLs and require `--yes` for destructive reset.

### Task 3: Documentation and Runtime Configuration

**Files:**
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`

- [x] **Step 1: Align environment docs**

Document `AGORA_DATABASE_URL` instead of the unused `DATABASE_URL`.

- [x] **Step 2: Record execution log**

Append scope, tests, commit, and black-box validation notes to the durable roadmap.

## Next Chunks

- Add repository test matrix helpers for SQLite plus optional Postgres.
- Add real Qdrant/OpenSearch adapter interfaces behind config flags.
- Add richer rebuild diagnostics and production health checks.
