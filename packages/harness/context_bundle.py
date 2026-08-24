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
    accepted_revision=None,
) -> dict[str, Any]:
    has_sources = bool(context_pack.source_refs)
    accepted_revision_id = accepted_revision.id if accepted_revision is not None else None
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
        "provisional": accepted_revision is None,
        "freshness": {
            "repository_relation": "same_project" if accepted_revision is not None else "unknown",
            "workspace_state": "unknown",
            "context_coverage": "fresh" if accepted_revision is not None else "potentially_stale" if has_sources else "missing",
            "proposal_state": "none",
            "accepted_revision_id": accepted_revision_id,
            "observed_commit_sha": accepted_revision.commit_sha if accepted_revision is not None else None,
            "recommended_action": "use_accepted_context"
            if accepted_revision is not None
            else "use_provisional_context" if has_sources else "analyze_local_project",
        },
        "capability_pins": {
            "context_revision_id": accepted_revision_id,
            "workflow_version_id": None,
            "skill_version_id": None,
        },
        "summary": context_pack.summary,
        "key_facts": list(context_pack.key_facts),
        "source_refs": list(context_pack.source_refs),
        "budget": {},
        "next_actions": [
            {
                "type": "fetch_context_ref" if has_sources else "analyze_local_project",
                "reason": "Use accepted team ContextRevision."
                if accepted_revision is not None
                else "Use provisional project context pending accepted ContextRevision."
                if has_sources
                else "No reusable Agora context exists for this request.",
            }
        ],
    }
    return trim_payload_to_budget(payload, budget_limit=token_budget)


__all__ = ["TokenBudgetTooSmall", "build_context_bundle"]
