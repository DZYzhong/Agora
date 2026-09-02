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

- [ ] **Step 1: Add failing tests** — low-tier classification for structured summaries/anchors/hashes without excerpts; high-tier for source/document excerpts, secret-rule exceptions, forbidden paths/types, over-limit content, policy overrides and quality waivers; revalidation rejects absolute paths, `..`, credentialized remotes, unknown kinds, control characters, oversized fields and secret patterns; tier cannot be downgraded by client-claimed metadata.
- [ ] **Step 2: Run RED.**
- [ ] **Step 3: Implement** classifier + revalidator with a stable `policy_version`.
- [ ] **Step 4: Run GREEN.**
- [ ] **Step 5: Commit** `feat: add upload policy and risk classifier`.

### Task 2: Server-side revalidation of Harness uploads and tier/grant matching

**Files:**

- Modify: `apps/api/routers/harness.py` (revalidate `development_update`; require high-tier uploads to carry a valid approval grant or reauthenticated Web session; low-tier workflow acknowledgment requires step ID, prompt digest, choice, interaction ID, payload digest, policy version, time)
- Modify: `apps/api/routers/context_governance.py` (revalidate proposal content/source anchors)
- Create: `tests/integration/api/test_upload_policy_api.py`

- [ ] **Step 1: Add failing tests** — high-tier upload without grant denied; low-tier acknowledgment with required fields accepted from Agent; downgrade attempt (client claims low for excerpt payload) rejected with audit; oversized upload rejected with stable code.
- [ ] **Step 2: Run RED.**
- [ ] **Step 3: Implement** enforcement in the Harness and context routers.
- [ ] **Step 4: Run GREEN.**
- [ ] **Step 5: Commit** `feat: enforce server-side upload policy and tier matching`.

## Chunk 2: Request limits, stable errors, redaction, CORS

### Task 3: Request-size limits and stable error codes

**Files:**

- Modify: `apps/api/middleware.py` (body-size limit middleware; stable `PAYLOAD_TOO_LARGE`/`PAYLOAD_INVALID` errors; log redaction of Authorization/cookie/remote credentials/secrets)
- Create: `tests/integration/api/test_request_limits.py`

- [ ] **Step 1: Add failing tests** — oversized JSON body rejected with `PAYLOAD_TOO_LARGE`; oversized upload field rejected; error responses never contain tracebacks/SQL/local paths; logs redact Authorization, cookie, credential-bearing remotes and secret patterns.
- [ ] **Step 2: Run RED.**
- [ ] **Step 3: Implement** middleware + redaction helper.
- [ ] **Step 4: Run GREEN.**
- [ ] **Step 5: Commit** `feat: enforce request limits and log redaction`.

### Task 4: CORS for the configured Web origin

**Files:**

- Modify: `apps/api/main.py` or `middleware.py` (CORS allow-list from `AGORA_ALLOWED_ORIGINS`, no wildcard)
- Modify: `tests/integration/test_web_config.py`

- [ ] **Step 1: Add failing tests** — preflight from allowed origin passes; from disallowed origin rejected; no `*` in any CORS header.
- [ ] **Step 2: Run RED.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run GREEN.**
- [ ] **Step 5: Commit** `feat: restrict cors to configured origins`.

## Chunk 3: Dependency and lint baseline

### Task 5: Python, Node and container-image dependency audit

**Files:**

- Modify: `pyproject.toml` / `apps/web/package.json` (versions pinned/upgraded to clear High/Critical)
- Modify: `infra/Dockerfile.*` (pin known-good base image digests/tags)
- Create: `scripts/dependency_audit.py` (runs `pip-audit` and `npm audit --omit=dev` and reports open High/Critical)
- Create: `tests/integration/test_dependency_audit.py` (contract test: audit script exists and documents the command; versions pinned)

- [ ] **Step 1: Run `pip-audit` and `npm audit`** and record findings.
- [ ] **Step 2: Fix or pin** every open High/Critical (upgrade Next.js to a patched release for postcss/sharp; pin base images).
- [ ] **Step 3: Re-run audits** until zero open High/Critical; record exact commands and versions.
- [ ] **Step 4: Commit** `fix: clear production dependency high/critical findings`.

### Task 6: ESLint configuration (PR1A gap)

**Files:**

- Modify: `apps/web/package.json` (add eslint, eslint-config-next devDependencies; wire `lint` script)
- Create: `apps/web/eslint.config.mjs`

- [ ] **Step 1: Add failing web-config test** — `lint` script exists and does not require interactive setup; eslint config file present.
- [ ] **Step 2: Implement** ESLint flat config with `eslint-config-next`.
- [ ] **Step 3: Run `npm run lint`** green; `next build` still passes.
- [ ] **Step 4: Commit** `feat: configure eslint for the web app`.

## Chunk 4: Verification and durable status

### Task 7: PR1C verification and roadmap update

- [ ] **Step 1: Full verification** — `pytest`, `compileall`, `pip check`, `pip-audit`, `npm audit`, `tsc --noEmit`, `next build`, `git diff --check`.
- [ ] **Step 2: Update roadmap** PR1C state honestly: `implemented` + `automated verified` only; black-box and PR1 exit remain pending.
- [ ] **Step 3: Commit** `docs: record pr1c verification`.

---

## Exit criteria

- Upload policy is server-authoritative: every upload is revalidated, risk tier is computed server-side and cannot be downgraded by the client, high-tier uploads require a valid grant/reauthenticated session, low-tier acknowledgment carries the required evidence fields.
- Request-size limits and stable error codes are enforced; logs redact credentials and secrets; CORS allows only configured origins.
- `pip-audit` and `npm audit --omit=dev` report zero open High/Critical; container base images are pinned; `npm run lint` is configured and green.
- Full test suite green; roadmap records `implemented` + `automated verified` only.
