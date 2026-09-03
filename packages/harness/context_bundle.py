from __future__ import annotations

from typing import Any

from packages.core.models import ContextRevisionModel, SkillVersionModel
from packages.harness.token_budget import TokenBudgetTooSmall, trim_payload_to_budget
from packages.knowledge.context_engine import PlannedContextPack

PROTOCOL_VERSION = "1.0"


def build_context_bundle(
    *,
    session_id: str,
    query: str,
    token_budget: int,
    context_pack: PlannedContextPack,
    accepted_revision: ContextRevisionModel | None = None,
    skill_versions: list[SkillVersionModel] | None = None,
) -> dict[str, Any]:
    has_sources = bool(context_pack.source_refs)
    accepted_revision_id = accepted_revision.id if accepted_revision is not None else None
    applicable_skill_versions = skill_versions or []
    skill_version_ids = [version.id for version in applicable_skill_versions]
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
            "skill_version_id": skill_version_ids[0] if skill_version_ids else None,
            "skill_version_ids": skill_version_ids,
        },
        "skills": [serialize_skill_version(version) for version in applicable_skill_versions],
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


def serialize_skill_version(version: SkillVersionModel) -> dict[str, Any]:
    definition = version.definition or {}
    return {
        "skill_version_id": version.id,
        "skill_id": version.skill_id,
        "slug": definition.get("slug"),
        "name": definition.get("name"),
        "version": version.version,
        "summary": definition.get("summary"),
        "triggers": list(definition.get("triggers") or []),
        "input_schema": definition.get("input_schema") or {"type": "object"},
        "output_schema": definition.get("output_schema") or {"type": "object"},
        "instructions": definition.get("instructions"),
        "risk_constraints": list(definition.get("risk_constraints") or []),
    }


__all__ = ["TokenBudgetTooSmall", "build_context_bundle"]
