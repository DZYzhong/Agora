# Agora PR1C Upload Policy and Security Baseline

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make client-side sanitization non-authoritative: the server enforces upload policy, revalidates every upload, computes the risk tier itself (no client self-reported downgrade), bounds request sizes, redacts sensitive values, and clears the production dependency baseline (Python, Node, container images) of open High/Critical issues, including the ESLint gap recorded in PR1A.

**Architecture:** Policy lives in `packages.core` (org/project upload policy + risk classifier); enforcement happens at the API gateway (size limits, CORS, redaction) and in the Harness/integration routers (payload revalidation, tier/grant matching). PR1B grants gate high-risk uploads; PR1A temporary errors remain until this plan's typed policy replaces them.

**Tech Stack:** Python 3.10, FastAPI, Pydantic, pytest, `pip-audit`, npm, Docker.

**Design source:** `docs/superpowers/specs/2026-08-28-agora-production-readiness-design.zh-CN.md` §7.2-§7.3.

**Scope boundary:** PR1C covers upload policy, revalidation, risk tiering, request limits, redaction, CORS and dependency audits. It does not implement PR2 deployment (worker, TLS, backup) and does not run the real-AI-tool black-box (needs a human with a configured AI tool).

---

## Chunk 1: Upload policy and server-side risk tiering

### Task 1: Upload policy model and classifier

**Files:**

- Create: `packages/core/upload_policy.py` (UploadPolicy dataclass: allowed kinds, path patterns, max sizes, secret rules, policy version; `classify_upload()` computing the risk tier from the actual payload; `revalidate_upload()` with path/content-type/size/control-char/secret checks)
- Create: `tests/unit/core/test_upload_policy.py`

- [x] **Step 1: Add failing tests** — low-tier classification for structured summaries/anchors/hashes without excerpts; high-tier for source/document excerpts, secret-rule exceptions, forbidden paths/types, over-limit content, policy overrides and quality waivers; revalidation rejects absolute paths, `..`, credentialized remotes, unknown kinds, control characters, oversized fields and secret patterns; tier cannot be downgraded by client-claimed metadata.
- [x] **Step 2: Run RED.**
- [x] **Step 3: Implement** classifier + revalidator with a stable `policy_version`.
- [x] **Step 4: Run GREEN.**
- [x] **Step 5: Commit** `feat: add upload policy and risk classifier`.

### Task 2: Server-side revalidation of Harness uploads and tier/grant matching

**Files:**

- Modify: `apps/api/routers/harness.py` (revalidate `development_update`; require high-tier uploads to carry a valid approval grant or reauthenticated Web session; low-tier workflow acknowledgment requires step ID, prompt digest, choice, interaction ID, payload digest, policy version, time)
- Modify: `apps/api/routers/context_governance.py` (revalidate proposal content/source anchors)
- Create: `tests/integration/api/test_upload_policy_api.py`

- [x] **Step 1: Add failing tests** — high-tier upload without grant denied; low-tier acknowledgment with required fields accepted from Agent; downgrade attempt (client claims low for excerpt payload) rejected with audit; oversized upload rejected with stable code.
- [x] **Step 2: Run RED.**
- [x] **Step 3: Implement** enforcement in the Harness and context routers.
- [x] **Step 4: Run GREEN.**
- [x] **Step 5: Commit** `feat: enforce server-side upload policy and tier matching`.

## Chunk 2: Request limits, stable errors, redaction, CORS

### Task 3: Request-size limits and stable error codes

**Files:**

- Modify: `apps/api/middleware.py` (body-size limit middleware; stable `PAYLOAD_TOO_LARGE`/`PAYLOAD_INVALID` errors; log redaction of Authorization/cookie/remote credentials/secrets)
- Create: `tests/integration/api/test_request_limits.py`

- [x] **Step 1: Add failing tests** — oversized JSON body rejected with `PAYLOAD_TOO_LARGE`; oversized upload field rejected; error responses never contain tracebacks/SQL/local paths; logs redact Authorization, cookie, credential-bearing remotes and secret patterns.
- [x] **Step 2: Run RED.**
- [x] **Step 3: Implement** middleware + redaction helper.
- [x] **Step 4: Run GREEN.**
- [x] **Step 5: Commit** `feat: enforce request limits and log redaction`.

### Task 4: CORS for the configured Web origin

**Files:**

- Modify: `apps/api/main.py` or `middleware.py` (CORS allow-list from `AGORA_ALLOWED_ORIGINS`, no wildcard)
- Modify: `tests/integration/test_web_config.py`

- [x] **Step 1: Add failing tests** — preflight from allowed origin passes; from disallowed origin rejected; no `*` in any CORS header.
- [x] **Step 2: Run RED.**
- [x] **Step 3: Implement.**
- [x] **Step 4: Run GREEN.**
- [x] **Step 5: Commit** `feat: restrict cors to configured origins`.

## Chunk 3: Dependency and lint baseline

### Task 5: Python, Node and container-image dependency audit

**Files:**

- Modify: `pyproject.toml` / `apps/web/package.json` (versions pinned/upgraded to clear High/Critical)
- Modify: `infra/Dockerfile.*` (pin known-good base image digests/tags)
- Create: `scripts/dependency_audit.py` (runs `pip-audit` and `npm audit --omit=dev` and reports open High/Critical)
- Create: `tests/integration/test_dependency_audit.py` (contract test: audit script exists and documents the command; versions pinned)

- [x] **Step 1: Run `pip-audit` and `npm audit`** and record findings.
- [x] **Step 2: Fix or pin** every open High/Critical (upgrade Next.js to a patched release for postcss/sharp; pin base images).
- [x] **Step 3: Re-run audits** until zero open High/Critical; record exact commands and versions.
- [x] **Step 4: Commit** `fix: clear production dependency high/critical findings`.

### Task 6: ESLint configuration (PR1A gap)

**Files:**

- Modify: `apps/web/package.json` (add eslint, eslint-config-next devDependencies; wire `lint` script)
- Create: `apps/web/eslint.config.mjs`

- [x] **Step 1: Add failing web-config test** — `lint` script exists and does not require interactive setup; eslint config file present.
- [x] **Step 2: Implement** ESLint flat config with `eslint-config-next`.
- [x] **Step 3: Run `npm run lint`** green; `next build` still passes.
- [x] **Step 4: Commit** `feat: configure eslint for the web app`.

## Chunk 4: Verification and durable status

### Task 7: PR1C verification and roadmap update

- [x] **Step 1: Full verification** — `pytest`, `compileall`, `pip check`, `pip-audit`, `npm audit`, `tsc --noEmit`, `next build`, `git diff --check`.
- [x] **Step 2: Update roadmap** PR1C state honestly: `implemented` + `automated verified` only; black-box and PR1 exit remain pending.
- [x] **Step 3: Commit** `docs: record pr1c verification`.

## Execution records

### Task 1 (2026-09-02)

- Commit: `12b3142` (feat: add upload policy and risk classifier). `packages/core/upload_policy.py`: `UploadPolicy`, `classify_upload` (server-computed LOW/HIGH tier; client cannot downgrade), `revalidate_upload`/`revalidate_path`/`revalidate_remote` (absolute/backslash paths, traversal, control chars, credential patterns, size limits), `contains_secret`, `redact_sensitive`. Unit suite `12 passed`.

### Task 2 (2026-09-02)

- Commit: `8f6695c` (feat: enforce server-side upload policy and tier matching). `close-work` revalidates `development_update` and rejects high-tier (secret-bearing) updates from non-grant principals with `HIGH_RISK_UPLOAD_REQUIRES_GRANT`; `CompleteWorkflowStepRequest.acknowledgment` (low-risk workflow acknowledgment evidence: step_id, prompt_digest, choice, local_interaction_id, payload_digest, policy_version, acknowledged_at) validated and recorded as a session event, distinct from Approval. API suite `5 passed`.

### Task 3 (2026-09-02)

- Commit: `3820de1` (feat: enforce request limits, log redaction and cors). `BodyLimitMiddleware` (413 `PAYLOAD_TOO_LARGE`), `stable_error_response` with `redact_sensitive`, CORS allow-list via `AGORA_ALLOWED_ORIGINS` + localhost dev origins (no wildcard). Suite `8 passed`.

### Task 4 (2026-09-02)

- Covered by `3820de1` (CORS). Preflight from allowed origin passes; disallowed origin gets no ACAO header; never `*`.

### Task 5 (2026-09-02)

- Commit: `20db4b2` (fix: clear production dependency high/critical findings). Upgraded venv setuptools to 84.0.0 (pip-audit clean); next 15.5.25 with `overrides` for postcss ^8.4.32 and sharp ^0.35.0 (official-registry `npm audit --omit=dev` now 0 high/critical); pinned `qdrant/qdrant:v1.19.0` (was `:latest`); added `scripts/dependency_audit.py` + contract tests (`3 passed`). Container image digest-pinning and Trivy scanning remain deployment-CI (PR2) items, recorded.

### Task 6 (2026-09-02)

- Commit: `186242a` (feat: configure eslint for the web app). `eslint.config.mjs` (FlatCompat + next/core-web-vitals + next/typescript), `lint` script `eslint .`, eslint + eslint-config-next devDependencies. `npm run lint` green (0 errors, 0 warnings) — closes the PR1A lint gap. Web-config contract test `1 passed`; `next build` passes.

### Task 7 (2026-09-02)

- Verification: full Python suite `461 passed, 2 skipped`; `compileall` OK; `pip check` OK; `pip-audit` 0 findings; `npm audit --omit=dev` 0 High/Critical; `tsc --noEmit` OK; `next build` OK; `git diff --check` OK.
- Durable status: PR1C `implemented` + `automated verified`. PR1C black-box (real AI tool), PR1 exit gate and production readiness remain open and gated behind PR2 and real-AI-tool black-box runs.

---

## Exit criteria

- Upload policy is server-authoritative: every upload is revalidated, risk tier is computed server-side and cannot be downgraded by the client, high-tier uploads require a valid grant/reauthenticated session, low-tier acknowledgment carries the required evidence fields.
- Request-size limits and stable error codes are enforced; logs redact credentials and secrets; CORS allows only configured origins.
- `pip-audit` and `npm audit --omit=dev` report zero open High/Critical; container base images are pinned; `npm run lint` is configured and green.
- Full test suite green; roadmap records `implemented` + `automated verified` only.
