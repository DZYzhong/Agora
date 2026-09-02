# Agora PR2 Recoverable Deployment

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Agora deployable and recoverable: a persistent outbox Worker with cross-process lease locking, retry/backoff and dead-lettering; a one-time migration job before API/Worker startup; truthful `/ready` (503 on failure); a reverse proxy (TLS, payload limits, timeouts, rate limits); and encrypted backups that leave the database host and restore cleanly.

**Architecture:** The Worker uses lease-based outbox claiming (atomic status claim + lease timeout reclaim), runs a loop with backoff and graceful SIGTERM shutdown, and is a first-class Compose service. `alembic upgrade head` runs once via a Compose `migrate` job before API/Worker start. An nginx reverse proxy terminates TLS and enforces payload/timeout/rate limits. Backup/restore gain passphrase encryption (openssl, no new dependencies).

**Tech Stack:** Python 3.10, SQLAlchemy, Alembic, Docker Compose, nginx, pytest.

**Design source:** `docs/superpowers/specs/2026-08-28-agora-production-readiness-design.zh-CN.md` §7-§8, `docs/superpowers/plans/2026-08-28-agora-production-readiness-implementation.md` Chunk 2.

**Scope boundary:** PR2 covers worker, migration job, `/ready` truthfulness (already fixed in PR1A — verify and test), reverse proxy and encrypted backup. Measured RPO/RTO, TLS certificate management and on-clean-host DR drills require a real environment and remain gated.

---

## Chunk 1: Persistent outbox worker

### Task 1: Lease-based outbox claiming

**Files:**

- Create: `alembic/versions/20260902_0016_pr2_outbox_leases.py` (`outbox_events.processing_started_at` nullable)
- Modify: `packages/core/models.py`
- Modify: `packages/core/services/outbox.py` (atomic claim `pending -> processing` with lease timestamp; lease-timeout reclaim of stale `processing` events; commit per event)
- Modify: `tests/unit/core/test_outbox.py` (or new `tests/unit/core/test_outbox_leases.py`)

- [ ] **Step 1: Add failing tests** — two processors claiming concurrently never process the same event; a crashed (stale) processing event is reclaimed after the lease timeout; retries and dead-lettering still work; per-event commit means one failure does not roll back other completions.
- [ ] **Step 2: Run RED.**
- [ ] **Step 3: Implement** lease claim + reclaim + per-event commit.
- [ ] **Step 4: Run GREEN.**
- [ ] **Step 5: Commit** `feat: add lease-based outbox claiming`.

### Task 2: Persistent worker loop with graceful shutdown

**Files:**

- Modify: `apps/workers/main.py` (`outbox-loop` command: loop with backoff, batch processing, SIGTERM/SIGINT graceful shutdown, `--once` for tests)
- Modify: `apps/workers/workflows/outbox.py` (expose `run_worker_loop` reusable by tests)
- Create: `tests/integration/workers/test_outbox_loop.py`

- [ ] **Step 1: Add failing tests** — `--once` processes a batch and exits 0; SIGTERM during the loop stops cleanly; backoff delay is honored (configurable for tests).
- [ ] **Step 2: Run RED.**
- [ ] **Step 3: Implement** the loop.
- [ ] **Step 4: Run GREEN.**
- [ ] **Step 5: Commit** `feat: add persistent outbox worker loop`.

## Chunk 2: Deployment topology

### Task 3: Compose migrate job, worker service and reverse proxy

**Files:**

- Modify: `infra/docker-compose.yml` (one-shot `migrate` job; `worker` service; `nginx` reverse proxy with TLS/payload/timeout/rate limits)
- Create: `infra/nginx/agora.conf` (TLS termination, `client_max_body_size`, timeouts, `limit_req`)
- Modify: `tests/integration/test_web_config.py` (compose contract: migrate/worker/nginx services exist; nginx config has payload limit/timeout/rate limit; TLS cert paths referenced)

- [ ] **Step 1: Add failing contract tests.**
- [ ] **Step 2: Run RED.**
- [ ] **Step 3: Implement** compose + nginx config.
- [ ] **Step 4: Run GREEN** (PyYAML compose validation).
- [ ] **Step 5: Commit** `feat: add migrate job, worker and reverse proxy to compose`.

### Task 4: `/ready` returns 503 on failure (verify PR1A fix)

**Files:**

- Modify: `tests/integration/api/test_health.py` (assert 503 + `not_ready` when database is unreachable / configuration invalid; 200 only when fully ready)

- [ ] **Step 1: Add failing/verification tests** (the PR1A fix already returns 503; add regression coverage).
- [ ] **Step 2: Run GREEN.**
- [ ] **Step 3: Commit** `test: verify readiness returns 503 on failure`.

## Chunk 3: Encrypted backup and restore

### Task 5: Encrypted backup leaving the database host

**Files:**

- Modify: `scripts/agora_admin.py` (`backup-sqlite --passphrase` / env `AGORA_BACKUP_PASSPHRASE`; `restore-sqlite` with same; openssl AES-256-CBC, no plaintext on disk)
- Modify: `tests/integration/test_admin_cli.py` (backup-encrypt-restore round-trip; wrong passphrase fails; plaintext secrets not in the backup file)

- [ ] **Step 1: Add failing tests.**
- [ ] **Step 2: Run RED.**
- [ ] **Step 3: Implement** openssl-backed encryption.
- [ ] **Step 4: Run GREEN.**
- [ ] **Step 5: Commit** `feat: encrypt sqlite backups at rest`.

## Chunk 4: Verification and durable status

### Task 6: PR2 verification and roadmap update

- [ ] **Step 1: Full verification** — `pytest`, `compileall`, `pip check`, `tsc --noEmit`, `next build`, `git diff --check`, PyYAML compose validation.
- [ ] **Step 2: Update roadmap** PR2 state honestly: `implemented` + `automated verified`; DR drills, RPO/RTO measurement, TLS cert ops and PR1 black-box remain pending in a real environment.
- [ ] **Step 3: Commit** `docs: record pr2 verification`.

---

## Exit criteria

- Outbox events are claimed with a lease; concurrent workers never double-process; stale leases are reclaimed; retries/dead-lettering preserved; the persistent loop shuts down gracefully on SIGTERM.
- Compose runs `migrate` once before API/Worker, runs a `worker` service, and fronts everything with an nginx proxy enforcing TLS, payload size, timeouts and rate limits.
- `/ready` returns 503 whenever not ready.
- Backups are encrypted and restore cleanly with the correct passphrase; wrong passphrase fails loudly.
- Full test suite green; roadmap records `implemented` + `automated verified`; DR/RPO/RTO remain gated on real environment.
