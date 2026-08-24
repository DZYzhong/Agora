from __future__ import annotations

import copy
import json
from math import ceil
from typing import Any

ESTIMATOR_VERSION = "chars_div_4_v1"


class TokenBudgetTooSmall(ValueError):
    code = "TOKEN_BUDGET_TOO_SMALL"

    def __init__(self, *, budget_limit: int, minimum_tokens: int):
        self.budget_limit = budget_limit
        self.minimum_tokens = minimum_tokens
        super().__init__(f"Token budget {budget_limit} is too small; minimum is {minimum_tokens}")


def stable_json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def estimate_tokens(payload: Any) -> int:
    return ceil(len(stable_json_dumps(payload)) / 4)


def trim_payload_to_budget(payload: dict[str, Any], *, budget_limit: int) -> dict[str, Any]:
    budgeted = copy.deepcopy(payload)
    truncation = {
        "key_facts_dropped": 0,
        "source_refs_dropped": 0,
        "source_metadata_dropped": 0,
        "summary_truncated": False,
    }
    budgeted["budget"] = _budget_metadata(budget_limit=budget_limit, estimated_tokens=0, truncation=truncation)
    _ensure_minimum_viable(budgeted, budget_limit=budget_limit)

    while estimate_tokens(budgeted) > budget_limit and budgeted.get("key_facts"):
        budgeted["key_facts"].pop()
        truncation["key_facts_dropped"] += 1
        budgeted["budget"] = _budget_metadata(budget_limit=budget_limit, estimated_tokens=0, truncation=truncation)

    for source_ref in budgeted.get("source_refs", []):
        if estimate_tokens(budgeted) <= budget_limit:
            break
        for key in ("preview", "source_span", "retrieval_sources", "relevance"):
            if key in source_ref:
                source_ref.pop(key, None)
                truncation["source_metadata_dropped"] += 1
                budgeted["budget"] = _budget_metadata(budget_limit=budget_limit, estimated_tokens=0, truncation=truncation)
                if estimate_tokens(budgeted) <= budget_limit:
                    break

    while estimate_tokens(budgeted) > budget_limit and budgeted.get("source_refs"):
        budgeted["source_refs"].pop()
        truncation["source_refs_dropped"] += 1
        budgeted["budget"] = _budget_metadata(budget_limit=budget_limit, estimated_tokens=0, truncation=truncation)

    summary = budgeted.get("summary") or ""
    while estimate_tokens(budgeted) > budget_limit and summary:
        trim_by = max(16, (estimate_tokens(budgeted) - budget_limit) * 4)
        summary = summary[:-trim_by].rstrip()
        budgeted["summary"] = summary
        truncation["summary_truncated"] = True
        budgeted["budget"] = _budget_metadata(budget_limit=budget_limit, estimated_tokens=0, truncation=truncation)

    estimated_tokens = estimate_tokens({**budgeted, "budget": _budget_metadata(budget_limit=budget_limit, estimated_tokens=0, truncation=truncation)})
    budgeted["budget"] = _budget_metadata(
        budget_limit=budget_limit,
        estimated_tokens=estimated_tokens,
        truncation=truncation,
    )
    if estimate_tokens(budgeted) > budget_limit:
        raise TokenBudgetTooSmall(budget_limit=budget_limit, minimum_tokens=estimate_tokens(budgeted))
    return budgeted


def _ensure_minimum_viable(payload: dict[str, Any], *, budget_limit: int) -> None:
    minimum = copy.deepcopy(payload)
    minimum["summary"] = ""
    minimum["key_facts"] = []
    minimum["source_refs"] = []
    minimum_tokens = estimate_tokens(minimum)
    if minimum_tokens > budget_limit:
        raise TokenBudgetTooSmall(budget_limit=budget_limit, minimum_tokens=minimum_tokens)


def _budget_metadata(*, budget_limit: int, estimated_tokens: int, truncation: dict[str, Any]) -> dict[str, Any]:
    return {
        "budget_limit": budget_limit,
        "estimated_tokens": estimated_tokens,
        "estimator_version": ESTIMATOR_VERSION,
        "truncation": dict(truncation),
    }
