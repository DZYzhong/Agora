# Agora Production Readiness Program Roadmap and Plan Index

> This file is a program roadmap and child-plan index, not an executable task plan. Only linked child plans with checkbox TDD steps may be executed.

**Goal:** Move Agora from a controlled team-trial build to the approved enterprise-intranet, single-organization Docker Compose production standard.

**Architecture:** Preserve the existing modular monolith and Harness boundary. Harden it in dependency order: close remote attack paths and protocol gaps first, then introduce real identity/session governance, recoverable infrastructure, consistent context storage, and finally operational acceptance.

**Tech Stack:** Python 3.10, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, Next.js 15, MCP stdio, Docker Compose, pytest.

**Design source:** `docs/superpowers/specs/2026-08-28-agora-production-readiness-design.zh-CN.md`

---

## Phase state model

Each phase tracks four independent states:

- `implemented`
- `automated verified`
- `black-box passed`
- `exit criteria passed`

No phase is described as complete until all four are true and the roadmap contains test evidence.

## Chunk 1: PR1 Core security and MCP closure

### PR1A: Runtime boundaries and protocol closure

Plan: `docs/superpowers/plans/2026-08-28-agora-pr1a-runtime-mcp-hardening.md`

Current execution state (2026-09-01): Tasks 1-10 are implemented and automated-verified (`378 passed, 2 skipped`, `tsc --noEmit` and `next build` pass; `npm run lint` remains unconfigured — recorded gap for PR1C). PR1A black-box and exit criteria remain pending; a black-box guide is available at `docs/development/pr1a-runtime-mcp-blackbox.zh-CN.md`.

Outcomes:

- Test bypass is impossible outside isolated `AGORA_ENV=test`.
- Production rejects legacy server-side local repository scanning.
- Web no longer asks for a server-local repository path.
- MCP protocol 1.1 advertises and dispatches `agora_complete_workflow_step`.
- Tool schema, manifest and dispatch cannot silently drift.
- A real MCP stdio process can perform start -> complete step -> close.

PR1A is not suitable for shared or real-data deployment. Agent artifacts and HumanConfirmation remain blocked until PR1B/PR1C implement the approved typed policy.

### PR1B: Human sessions and approval grants

Separate plan required after PR1A verification.

Outcomes:

- One-time Admin bootstrap and Argon2id local accounts.
- Activation/reset credentials, revocation and audit.
- Secure Cookie session, CSRF and reauthentication.
- Personal/Agent/CI credential-channel denial matrix.
- Low-risk workflow acknowledgment is distinct from Approval.
- High-risk approval grant is bound, short-lived and one-time.

### PR1C: Upload policy and security baseline

Separate plan required after PR1B verification.

Outcomes:

- Organization/project upload policy and server-side payload revalidation.
- Server-computed low/high risk tier and downgrade rejection.
- Request-size limits, sensitive-value log redaction and stable errors.
- Python, Node and container-image production dependency audits have no open High/Critical issue.
- Real AI-tool PR1 black-box passes.

PR1 exit gate:

- `PR1-MCP-*`, `PR1-AUTH-*` and `PR1-UPLOAD-*` evidence recorded.
- No production local-path scan, auth bypass or credential-channel approval path.
- No production dependency High/Critical vulnerability.
- User completes real AI-tool black-box without direct HTTP calls.

## Chunk 2: PR2 Recoverable deployment

Separate implementation plan required after PR1 exit.

### PR2A: Compose deployability fixes (HIGH-2, HIGH-3)

Plan: `docs/superpowers/plans/2026-09-01-agora-pr2a-compose-deployability.md`

Current execution state (2026-09-01): Tasks 1-2 implemented and automated-verified; PR2A exit criteria pending black-box on a real Compose host.

Outcomes covered:

- Compose variables match API, Web and Connector runtime variables (`AGORA_API_URL` single convention).
- PostgreSQL data persists across container recreation via named volume.

PR2A does not claim the full PR2 exit gate (TLS, worker, DR, measured RPO/RTO), which remains open and gated behind PR1 exit.

Outcomes:

- Compose variables match API, Web and Connector runtime variables.
- PostgreSQL uses encrypted persistent storage.
- Migration job runs once before API/Worker startup.
- Persistent Worker supports locking, retry, dead-letter and SIGTERM.
- `/ready` returns 503 on database/schema/config failure.
- Reverse proxy provides TLS, payload limits, timeouts and baseline rate limits.
- Encrypted backup leaves the database host.
- Full restore succeeds on a clean host without deleted-data resurrection.

PR2 exit gate:

- `PR2-COMPOSE-*`, `PR2-WORKER-*`, `PR2-DR-*` evidence recorded.
- Measured RPO <= 24 hours and RTO <= 4 hours.

## Chunk 3: PR3 Team identity and authorization

Separate implementation plan required after PR2 exit.

Outcomes:

- Admin manages users, organization membership and project membership.
- Developer, Reviewer, PM, Quality, Admin and Viewer are product-operable roles.
- Personal/Agent/CI Tokens support issue, scope, expiry, rotate and revoke.
- Disabled users immediately lose sessions and credentials.
- Every sensitive identity/role/credential action is audited.

PR3 exit gate:

- `PR3-RBAC-*` matrix passes for every principal/action pair.
- Distinct real identities complete role-specific black-box paths.

## Chunk 4: PR4 Context consistency and PostgreSQL retrieval

Separate implementation plan required after PR3 exit.

Outcomes:

- Connector uploads sanitized observations and proposals only.
- ContextRevision and observed head are stream/branch scoped.
- Signed RevisionSignal evidence handles source priority and compare-and-set.
- Multi-branch, multi-source, replay, force-push and conflict behavior is deterministic.
- PostgreSQL FTS replaces runtime Fake indexes and can rebuild projections.
- Encrypted offline queue enforces identity binding, expiry and reauthorization.

PR4 exit gate:

- `PR4-FRESH-*` and `PR4-CONFLICT-*` evidence recorded.
- Internal real-data trial gate may open only after PR1-PR3 and PR4 main consistency path pass.

## Chunk 5: PR5 Operations and defense-in-depth

Separate implementation plan required after PR4 exit.

Outcomes:

- Structured logs, Prometheus metrics and alert rules cover API, database and Worker.
- Security headers and hostile-request regression suite pass.
- Retention, deletion ledger and recovery controls are operational.
- Expand/contract upgrade and rollback runbooks are exercised.
- Performance target passes at fixed dataset and 50 concurrent clients for 30 minutes.

PR5 exit gate:

- `PR5-PERF-*` and `PR5-OPS-*` evidence recorded.
- Operations and Security owners sign the runbooks and drills.

## Chunk 6: PR6 Production acceptance

Separate acceptance plan required after PR5 exit.

Outcomes:

- Real PostgreSQL, Compose and AI tool environment.
- Three developer identities work on concurrent WorkItems.
- Reviewer, PM and Quality complete governance paths.
- Restart, network loss, Worker backlog, Token revocation and clean-host recovery drills pass.
- Production readiness report records image digest, schema revision and all evidence.

Production release gate:

- PR1-PR6 exit criteria passed.
- Open Critical/High defects: zero.
- PostgreSQL recovery and multi-role black-box passed.
- Deployment, monitoring, backup and incident owners approve release.

## Required batch discipline

For every implementation batch:

1. Add one behavior-focused failing test and run it to prove RED.
2. Add the minimum production implementation and run targeted GREEN tests.
3. Run affected integration/process tests.
4. Run the full Python suite and Web production build when the batch touches shared runtime behavior.
5. Update this plan, the P1-P9 roadmap and the relevant black-box guide.
6. Commit code and evidence together.
7. Start user black-box only after self-test passes and all required services are running.
