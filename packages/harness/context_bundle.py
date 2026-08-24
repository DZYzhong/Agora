from __future__ import annotations

from typing import Any

from packages.harness.token_budget import TokenBudgetTooSmall, trim_payload_to_budget

PROTOCOL_VERSION = "1.0"


def build_context_bundle(
    *,
    session_id: str,
    query: str,
    token_budget: int,
    context_pack,
) -> dict[str, Any]:
    has_sources = bool(context_pack.source_refs)
    payload = {
        "protocol_version": PROTOCOL_VERSION,
        "operation": "prepare_context",
        "session_id": session_id,
        "id": context_pack.id,
        "context_pack_id": context_pack.id,
        "org_id": context_pack.org_id,
        "project_id": context_pack.project_id,
        "level": context_pack.level,
        "intent": context_pack.intent,
        "query": query,
        "provisional": True,
        "freshness": {
            "repository_relation": "unknown",
            "workspace_state": "unknown",
            "context_coverage": "potentially_stale" if has_sources else "missing",
            "proposal_state": "none",
            "accepted_revision_id": None,
            "observed_commit_sha": None,
            "recommended_action": "use_provisional_context" if has_sources else "analyze_local_project",
        },
        "summary": context_pack.summary,
        "key_facts": list(context_pack.key_facts),
        "source_refs": list(context_pack.source_refs),
        "budget": {},
        "next_actions": [
            {
                "type": "fetch_context_ref" if has_sources else "analyze_local_project",
                "reason": "Use provisional project context pending accepted ContextRevision."
                if has_sources
                else "No reusable Agora context exists for this request.",
            }
        ],
    }
    return trim_payload_to_budget(payload, budget_limit=token_budget)


__all__ = ["TokenBudgetTooSmall", "build_context_bundle"]
