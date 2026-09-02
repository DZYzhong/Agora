# Agora PR1B Human Sessions and Approval Grants

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace bootstrap-only identity with real human sessions and governed approvals: one-time Admin bootstrap with Argon2id local accounts, activation/reset/revoked credentials with full audit, secure Cookie sessions with CSRF and reauthentication, the credential-channel denial matrix, and a strict split between low-risk workflow acknowledgment and high-risk Approval via bound, short-lived, single-use grants.

**Architecture:** Identity and audit stay in `packages.core`; session and grant state are new relational tables; the API gateway (Web) authenticates via `Secure`/`HttpOnly`/`SameSite=Strict` cookie sessions while MCP/CI keep Bearer tokens; approval decisions bind to a reauthenticated Web human session or a grant issued by one. PR1A's temporary errors (`PR1_UPLOAD_POLICY_REQUIRED`, `PR1_APPROVAL_POLICY_REQUIRED`) remain until PR1C replaces them with typed policy; this plan makes the grant/session machinery available and enforced.

**Tech Stack:** Python 3.10, FastAPI, Pydantic, SQLAlchemy, Alembic, `argon2-cffi`, pytest.

**Design source:** `docs/superpowers/specs/2026-08-28-agora-production-readiness-design.zh-CN.md` §5.2-§5.4.

**Scope boundary:** PR1B covers identity, sessions, CSRF, reauthentication, credential denial matrix and approval grants. It does not implement PR1C upload policy, PR1A black-box, or PR2 deployment (worker, TLS, backup).

---

## Chunk 1: Local accounts and admin bootstrap

### Task 1: Argon2id password hashing and user model extensions

**Files:**

- Modify: `pyproject.toml` (add `argon2-cffi`)
- Create: `packages/core/passwords.py`
- Modify: `packages/core/models.py` (UserModel gains `username` unique, `password_hash`)
- Create: `alembic/versions/20260902_0013_pr1b_identity.py`
- Create: `tests/unit/core/test_passwords.py`
- Modify: `tests/unit/core/test_repositories.py`

- [x] **Step 1: Add failing password tests**

Hash/verify round-trip; wrong password fails; parameters embedded in the hash string; verify upgrades the hash when parameters differ; `None`/blank rejected; no plaintext retained.

- [x] **Step 2: Run RED** — `pytest tests/unit/core/test_passwords.py -q` fails on missing module.
- [x] **Step 3: Implement** `packages/core/passwords.py` using `argon2-cffi` (Argon2id, PHC string format, `verify_and_upgrade`).
- [x] **Step 4: Run GREEN**; add `argon2-cffi` to `pyproject.toml` dependencies; `pip install -e '.[test]'` re-links.
- [x] **Step 5: Commit** `feat: add argon2id password hashing`.

### Task 2: Admin bootstrap and user/credential lifecycle repository

**Files:**

- Modify: `packages/core/models.py` (UserModel `username` unique, `password_hash` nullable; activation/reset credential reuse with `kind=activation|reset` and `single_use`, `expires_at`)
- Modify: `packages/core/repositories/identities.py` (create user with activation credential, activate user, issue reset credential, revoke credential, revoke user credentials, single-use consumption helpers)
- Modify: `packages/core/services/auth_admin.py` (create — one-time admin bootstrap with org + admin user + audit; user CRUD helpers; reset/activate flows)
- Create: `tests/unit/core/test_auth_admin.py`
- Modify: `tests/unit/core/test_repositories.py`

- [x] **Step 1: Add failing admin/bootstrap tests** — one-time bootstrap succeeds once (unique constraint + lock), bootstrap secret unusable afterwards, activation credential single-use/expiring, reset credential 15-min single-use and revokes sessions, revocation makes credentials inactive, all actions audited.
- [x] **Step 2: Run RED** — missing module/columns.
- [x] **Step 3: Implement** repository + service + migration (`20260902_0013_pr1b_identity` adds `username`, `password_hash`; extends credential `single_use`, `kind` values).
- [x] **Step 4: Run GREEN** — focused unit tests + `alembic upgrade head` on a scratch DB.
- [x] **Step 5: Commit** `feat: add admin bootstrap and credential lifecycle`.

### Task 3: Admin bootstrap CLI and user management API

**Files:**

- Modify: `scripts/agora_admin.py` (bootstrap-admin command; one-time recovery code command)
- Create: `apps/api/routers/users.py` (create user -> activation credential, activate, disable, reset password, revoke credential; Admin-only; audit every action)
- Modify: `apps/api/main.py` (include users router)
- Create: `tests/integration/api/test_users_api.py`
- Modify: `tests/integration/test_admin_cli.py`

- [x] **Step 1: Add failing API/CLI tests** — non-admin denied; admin creates user and receives one-time activation secret only once; activate sets password; disabled user cannot authenticate; reset revokes sessions and issues 15-min credential; audit rows exist.
- [x] **Step 2: Run RED**.
- [x] **Step 3: Implement** router + CLI wiring (`require_admin` principal helper).
- [x] **Step 4: Run GREEN** — API tests + CLI test.
- [x] **Step 5: Commit** `feat: manage users and credentials via admin api`.

## Chunk 2: Cookie sessions, CSRF and reauthentication

### Task 4: Session model, login/logout and CSRF

**Files:**

- Create: `alembic/versions/20260902_0014_pr1b_sessions.py` (SessionModel: id, user_id, token_hash, created/expires_at, idle_expires_at, revoked_at, csrf_secret_hash)
- Create: `packages/core/repositories/sessions_auth.py`
- Create: `apps/api/auth_session.py` (login, logout, current-session principal, CSRF token issuance/validation, Origin check, rate limiting)
- Create: `apps/api/routers/auth.py` (POST /auth/login, POST /auth/logout, GET /auth/session, POST /auth/reauth)
- Modify: `apps/api/main.py`, `apps/api/middleware.py` (CSRF + Origin enforcement on cookie-authenticated state changes)
- Create: `tests/integration/api/test_auth_sessions.py`

- [x] **Step 1: Add failing tests** — login sets Secure/HttpOnly/SameSite=Strict cookie; session id never returned in body; wrong password rate-limited; logout revokes; CSRF token required for state change; Origin mismatch rejected; idle 30min / max 12h expiry enforced; reauth verifies password and issues fresh grant session.
- [x] **Step 2: Run RED**.
- [x] **Step 3: Implement**.
- [x] **Step 4: Run GREEN**.
- [x] **Step 5: Commit** `feat: add cookie sessions and csrf protection`.

## Chunk 3: Approval grants and denial matrix

### Task 5: Approval grant model and enforcement

**Files:**

- Create: `alembic/versions/20260902_0015_pr1b_approval_grants.py` (ApprovalGrantModel: id, user_id, session_id, object_type, object_id, payload_digest, decision, policy_version, expires_at, consumed_at, created_at)
- Create: `packages/core/repositories/approval_grants.py`
- Create: `packages/core/services/approval_grants.py` (issue from reauthenticated Web session, consume single-use, verify binding)
- Modify: `apps/api/routers/context_governance.py`, `apps/api/routers/skills.py` (approval endpoints accept grant or reauthenticated session; Agent/CI/Personal denied)
- Modify: `apps/api/auth.py` (`require_approval_capability` denial matrix)
- Create: `tests/integration/api/test_approval_grants.py`

- [x] **Step 1: Add failing tests** — Agent token cannot approve; CI token cannot approve; Personal token cannot approve; Web human session can approve; grant is single-use, 5-min expiry, payload-digest bound; reuse/expired/mismatched digest rejected; low-risk workflow acknowledgment from Agent token remains allowed and is distinct from Approval.
- [x] **Step 2: Run RED**.
- [x] **Step 3: Implement** grant issuance/consumption + denial matrix.
- [x] **Step 4: Run GREEN**.
- [x] **Step 5: Commit** `feat: enforce approval grants and credential denial matrix`.

## Chunk 4: Web UI and verification

### Task 6: Web login and user management pages

**Files:**

- Create: `apps/web/app/login/page.tsx`, `apps/web/app/users/page.tsx`, route handlers for login/logout/users
- Modify: `apps/web/lib/api.ts` (cookie credentials for session routes, CSRF header)

- [x] **Step 1: Add failing web-config contract tests** — login page exists; cookie + CSRF usage; users page lists members.
- [x] **Step 2: Implement + GREEN.**
- [x] **Step 3: Commit** `feat: add web login and user management`.

### Task 7: PR1B verification and durable status

- [x] **Step 1: Full verification** — `pytest` full suite, `compileall`, `pip check`, `npx tsc --noEmit`, `next build`, `git diff --check`.
- [x] **Step 2: Update roadmap** (`2026-08-28-agora-production-readiness-implementation.md` PR1B state) honestly: `implemented` + `automated verified` only; black-box and PR1 exit remain pending.
- [x] **Step 3: Commit** `docs: record pr1b verification`.


## Execution records

### Task 1 (2026-09-02)

- Commit: `0c99a64` (feat: add argon2id password hashing).
- Implementation: `packages/core/passwords.py` with Argon2id PHC-string hashing, timing-uniform dummy hash for accounts without a password, and `verify_and_upgrade` for cost-parameter upgrades on login. `argon2-cffi>=25.1.0` added to `pyproject.toml`.
- GREEN: `tests/unit/core/test_passwords.py` `9 passed`; full suite `379 passed, 2 skipped` at commit time.
- State: `implemented` and `automated verified`.

### Task 2 (2026-09-02)

- Commit: `5072f2e` (feat: add admin bootstrap and credential lifecycle).
- Implementation: migration `20260902_0013_pr1b_identity` adds `users.username`/`users.password_hash`, `credentials.single_use`/`consumed_at`, makes `security_audit_events.project_id` nullable, creates `organization_memberships` with a partial unique index enforcing one admin per org. `IdentityRepository` gained user/credential/org-membership lifecycle helpers. `packages/core/auth_admin.py` (moved out of services to match `auth.py`'s own-uow pattern) implements one-time `bootstrap_admin`, `create_user_with_activation` (30-min single-use hashed-only token), `activate_user`, `issue_reset_credential` (15-min), `reset_password`, `set_user_enabled` (disabling revokes all credentials) and `revoke_credential`, each audited via `SecurityRepository` with `project_id=None` for org-scoped events.
- GREEN: `test_auth_admin.py` + `test_passwords.py` `22 passed`; migration/core/repository suites `31 passed`; full suite `401 passed, 2 skipped`.
- State: `implemented` and `automated verified`.

### Task 3 (2026-09-02)

- Commit: `8d11551` (feat: manage users and credentials via admin api).
- Implementation: `scripts.agora_admin bootstrap-admin` (one-time, deterministic `ADMIN_ALREADY_BOOTSTRAPPED` on repeat); `apps/api/routers/users.py` with admin-only create-user -> one-time activation token, activate, admin-issued 15-min reset credential, reset-password, disable/enable (disable revokes all credentials), credential revoke, and user listing. Org-admin denial returns 403 `ORG_ADMIN_REQUIRED`; every action is audited via `SecurityRepository` (org-scoped events use `project_id=None`).
- GREEN: `test_users_api.py` `8 passed`; CLI bootstrap test `1 passed`; full suite `410 passed, 2 skipped`.
- Note: API-level org-admin denial is covered at unit level (`test_create_user_requires_org_admin`); HTTP-session-based denial testing lands with Task 4.
- State: `implemented` and `automated verified`.

### Task 4 (2026-09-02)

- Commit: `40a4366` (feat: add cookie sessions and csrf protection).
- Implementation: `web_sessions` table + `WebSessionRepository`; `apps/api/auth_session.py` with Argon2id login, sliding 30-min idle / 12-hour max session, double-submit CSRF cookie (`agora_csrf`, hash stored on the session), in-memory per-user+source login/reauth rate limiting, and reauthentication (5-min window). `apps/api/routers/auth.py` provides `/auth/login|logout|session|reauth`; `CsrfProtectionMiddleware` enforces Origin + `X-CSRF-Token` for cookie-authenticated state changes (bearer requests exempt). `get_current_principal` now falls back to the session cookie when no bearer token is present.
- GREEN: `test_auth_sessions.py` `10 passed`; full suite `420 passed, 2 skipped`.

### Task 5 (2026-09-02)

- Commit: `e47d5c3` (feat: enforce approval grants and credential denial matrix).
- Implementation: `approval_grants` table + repository + `packages/core/services/approval_grants.py`: grants bound to human user, object type/id, payload digest, decision, policy version, 5-minute expiry, single-use; `require_approval_capability` enforces the denial matrix — Agent/CI/Personal bearer tokens denied (`APPROVAL_CREDENTIAL_REQUIRED`), reauthenticated Web human sessions approve directly, grants consumed with full binding checks. `/approval-grants` issues grants from reauthenticated sessions; `approve_context_proposal` and `approve_skill` enforce capability before the project-role check. Existing production-auth approval tests converted to the Web-session flow.
- GREEN: `test_approval_grants.py` `9 passed`; full suite `429 passed, 2 skipped`.

### Task 6 (2026-09-02)

- Commit: `9cb89f7` (feat: add web login and user management).
- Implementation: `/login` page + `/login/submit` route handler (forwards the API's session/CSRF cookies to the browser and redirects), `/logout` route (revokes via the API and clears cookies), `/users` page (lists users, create form, disable/enable/reset forms, one-time activation/reset token delivery boxes), `/users/{create,disable,enable,reset}` route handlers using the session-cookie + CSRF helpers added to `lib/api.ts` (`apiGetWithSession`/`apiPostWithSession`, `agora_csrf` → `X-CSRF-Token`).
- GREEN: 3 new web-config contract tests; `npx tsc --noEmit` and `next build` pass; full suite `432 passed, 2 skipped`.

### Task 7 (2026-09-02)

- Commit: `docs: record pr1b verification` (this record).
- Verification: full Python suite `432 passed, 2 skipped` (PostgreSQL skips remain partial evidence until PR2); `compileall` OK; `pip check` OK; `npx tsc --noEmit` OK; `next build` OK; `git diff --check` OK.
- Durable status: PR1B Tasks 1-7 are `implemented` and `automated verified`. PR1B `black-box passed`, PR1 exit gate and production readiness remain open and gated behind PR1C and real-AI-tool black-box runs.

---

## Exit criteria

- Admin bootstrap is one-time; activation/reset credentials are single-use and expiring; revocation and audit cover every identity/credential action.
- Web sessions use Secure/HttpOnly/SameSite=Strict cookies with CSRF + Origin checks and rate-limited login/reset; reauthentication gates high-risk actions.
- Approval and high-risk HumanConfirmation are impossible for Agent/CI/Personal credentials; only reauthenticated Web human sessions or bound single-use grants can approve; low-risk workflow acknowledgment stays distinct.
- Full test suite green; no production dependency High/Critical introduced.
