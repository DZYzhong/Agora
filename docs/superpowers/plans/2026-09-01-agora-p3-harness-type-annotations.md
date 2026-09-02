# Agora P3 Harness Type Annotation Pass

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add accurate parameter and return type annotations to the Harness product core (`packages/harness/`) and the `CoreRuntime` facade it depends on (`packages/core/services/runtime.py`), without changing runtime behavior.

**Architecture:** Annotate the facade first, then the Harness layer, so method calls resolve against typed surfaces. Data-class result types already annotated in `packages/harness/service.py` are the return contract for the service methods.

**Tech Stack:** Python 3.10, pytest.

**Design source:** `docs/reviews/2026-08-28-agora-p0-p9-code-review.zh-CN.md` (type-annotation quality finding), PR1A registry types (`packages/core/services/mcp_tools.py`).

**Scope boundary:** This pass annotates `packages/harness/*.py` and `packages/core/services/runtime.py`. It does not refactor behavior, does not introduce new dependencies (no mypy install), and does not touch the web app or MCP transport beyond what type signatures require.

---

## Task 1: Annotate CoreRuntime facade

**Files:**

- Modify: `packages/core/services/runtime.py`

- [x] **Step 1: Add `from __future__ import annotations` and annotate every method**

Every `def` in `CoreRuntime` gets parameter and return annotations. Repository methods return SQLAlchemy model objects; where the repository layer is untyped, use the narrowest concrete type available (model class imported from `packages.core.models` or `object` only as a last resort).

- [x] **Step 2: Verify import and focused tests**

```bash
.venv/bin/python -c "import packages.core.services.runtime"
.venv/bin/pytest tests/unit/harness -q
```

Expected: PASS.

## Task 2: Annotate Harness package

**Files:**

- Modify: `packages/harness/*.py` (context_bundle.py, context_planner.py, development_capture.py, memory_writeback.py, project_resolver.py, service.py, session_recorder.py, skill_orchestrator.py, task_resolver.py, token_budget.py, work_resolver.py)

- [x] **Step 3: Annotate module-level functions and helpers first**

Functions that do not depend on `self.core` (pure helpers, parsers, formatters) get exact annotations.

- [x] **Step 4: Annotate methods against the typed facade**

Service methods return the annotated result dataclasses (`WorkStartResult`, `ContextRefResult`, `WorkflowStepCompletionResult`, etc.). Harness component methods (`ContextPlanner.prepare`, `SessionRecorder.record_event`, ...) annotate against `CoreRuntime` + `ContextEngine` + dataclass results. Use `dict[str, ...]`/`list[...]`/`Any` where the payload is genuinely dynamic (event payloads, structured metadata).

- [x] **Step 5: Verify no behavior change**

```bash
.venv/bin/python -m compileall -q packages
.venv/bin/pytest -q
cd apps/web && npx tsc --noEmit
```

Expected: full Python suite green (`379 passed, 2 skipped`), compileall and tsc pass.

- [x] **Step 6: Commit**

```bash
git add packages/harness packages/core/services/runtime.py docs/superpowers/plans/2026-09-01-agora-p3-harness-type-annotations.md
git commit -m "refactor: annotate harness core types"
```

---

## Execution record (2026-09-01)

- Commit: `b7503f3` (refactor: annotate harness core types; single commit covers Steps 1-6).
- Implementation: `CoreRuntime` facade (74 defs) annotated with concrete SQLAlchemy model return types; the Harness package (76 defs across service.py, context_planner.py, context_bundle.py, development_capture.py, memory_writeback.py, project_resolver.py, session_recorder.py, skill_orchestrator.py, task_resolver.py, work_resolver.py, token_budget.py) annotated against the typed facade and the pre-existing result dataclasses. `from __future__ import annotations` added where needed. Variadic facade pass-throughs kept as `**kwargs: Any`; genuinely dynamic payloads typed as `dict[str, Any]` — no invented concrete types.
- Verification: AST pass confirms all 156 defs in scope have return annotations; `compileall` passes; full Python suite `379 passed, 2 skipped`; `npx tsc --noEmit` passes; `git diff --check` passes.
- State: `implemented` and `automated verified`.

## Exit criteria

- Every `def` in `packages/harness/` and `packages/core/services/runtime.py` has parameter and return annotations.
- No runtime behavior change: full test suite passes, compileall and tsc pass.
- No new dependencies introduced.
