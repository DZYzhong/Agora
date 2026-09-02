"""Canonical, immutable MCP tool registry.

Single source of truth for tool advertisement (schemas), remote API paths,
minimum protocol versions and payload adapters. The stdio server and the
protocol manifest derive everything from here, so schema, manifest and
dispatch cannot silently drift.

Local tools (no remote path) have ``api_path=None`` and no adapter.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Callable

PayloadAdapter = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class McpToolDefinition:
    name: str
    description: str
    properties: tuple[tuple[str, dict[str, Any]], ...]
    required: tuple[str, ...]
    api_path: str | None = None
    minimum_protocol_version: str = "1.0"
    deprecated: bool = False
    canonical_tool: str | None = None
    adapter: PayloadAdapter | None = None


def _str(
    name: str,
    description: str | None = None,
    default: Any = None,
    enum: tuple[str, ...] | None = None,
) -> tuple[str, dict[str, Any]]:
    schema: dict[str, Any] = {"type": "string"}
    if description:
        schema["description"] = description
    if default is not None:
        schema["default"] = default
    if enum:
        schema["enum"] = list(enum)
    return (name, schema)


def _int(name: str, default: int | None = None, description: str | None = None) -> tuple[str, dict[str, Any]]:
    schema: dict[str, Any] = {"type": "integer"}
    if default is not None:
        schema["default"] = default
    if description:
        schema["description"] = description
    return (name, schema)


def _obj(name: str, description: str | None = None) -> tuple[str, dict[str, Any]]:
    schema: dict[str, Any] = {"type": "object"}
    if description:
        schema["description"] = description
    return (name, schema)


def _arr(name: str, item_type: str, description: str | None = None) -> tuple[str, dict[str, Any]]:
    schema: dict[str, Any] = {"type": "array", "items": {"type": item_type}}
    if description:
        schema["description"] = description
    return (name, schema)


def _adapter(builder: PayloadAdapter) -> PayloadAdapter:
    return builder


# --- Payload adapters -------------------------------------------------------


@_adapter
def _start_work_payload(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_message": arguments["user_message"],
        "repo_remote": arguments.get("repo_remote"),
        "branch_name": arguments.get("branch_name"),
        "local_observation": arguments.get("local_observation"),
        "agent_type": arguments.get("agent_type", "codex"),
    }


@_adapter
def _prepare_context_payload(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": arguments["session_id"],
        "query": arguments.get("query"),
        "token_budget": arguments.get("token_budget", 4000),
    }


@_adapter
def _fetch_context_ref_payload(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": arguments["session_id"],
        "asset_id": arguments["asset_id"],
        "max_tokens": arguments.get("max_tokens", 2000),
    }


@_adapter
def _submit_context_proposal_payload(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": arguments["session_id"],
        "type": arguments.get("type", "task_update"),
        "title": arguments["title"],
        "summary": arguments["summary"],
        "target_branch": arguments.get("target_branch", "main"),
        "expected_head_revision_id": arguments.get("expected_head_revision_id"),
        "from_commit_sha": arguments.get("from_commit_sha"),
        "to_commit_sha": arguments.get("to_commit_sha"),
        "content": arguments["content"],
        "source_anchors": arguments.get("source_anchors", []),
        "provenance": arguments.get("provenance", {}),
    }


@_adapter
def _complete_workflow_step_payload(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": arguments["session_id"],
        "step_key": arguments["step_key"],
        "summary": arguments["summary"],
        "artifacts": arguments.get("artifacts", []),
        "human_confirmation": arguments.get("human_confirmation"),
    }


@_adapter
def _suggest_skills_payload(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": arguments["session_id"],
        "query": arguments.get("query"),
    }


@_adapter
def _submit_skill_candidate_payload(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": arguments["session_id"],
        "slug": arguments["slug"],
        "name": arguments["name"],
        "summary": arguments["summary"],
        "triggers": arguments.get("triggers", []),
        "instructions": arguments["instructions"],
        "artifact_ids": arguments.get("artifact_ids", []),
    }


@_adapter
def _record_evidence_payload(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": arguments["session_id"],
        "evidence_type": arguments["evidence_type"],
        "source": arguments["source"],
        "status": arguments["status"],
        "conclusion": arguments["conclusion"],
        "command": arguments.get("command"),
        "output_summary": arguments.get("output_summary"),
        "raw_ref": arguments.get("raw_ref"),
        "metadata": arguments.get("metadata", {}),
    }


@_adapter
def _get_quality_status_payload(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": arguments["session_id"],
        "scope": arguments.get("scope", "work_item"),
    }


@_adapter
def _get_project_status_payload(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_id": arguments["project_id"],
    }


@_adapter
def _close_work_payload(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": arguments["session_id"],
        "status": arguments.get("status", "closed"),
        "development_update": arguments.get("development_update"),
    }


@_adapter
def _record_event_payload(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": arguments["session_id"],
        "event_type": arguments["event_type"],
        "payload": arguments["payload"],
    }


@_adapter
def _prepare_writeback_payload(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": arguments["session_id"],
        "type": arguments.get("type", "development_summary"),
        "title": arguments["title"],
        "content": arguments["content"],
        "asset_refs": arguments.get("asset_refs", []),
    }


@_adapter
def _search_knowledge_payload(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": arguments["session_id"],
        "query": arguments["query"],
        "token_budget": arguments.get("token_budget", 4000),
    }


# --- Canonical tool definitions ---------------------------------------------

TOOL_DEFINITIONS: tuple[McpToolDefinition, ...] = (
    McpToolDefinition(
        name="agora_start_work",
        description="Start an Agora work session for project-aware AI work. Use this before local code analysis. The user_message may include the project name or slug; repo_remote is optional fallback.",
        properties=(
            _str("user_message", "Original user request, including project name/slug when available."),
            _str("repo_remote", "Optional git origin remote. Agora also accepts normalized remotes without username or .git suffix."),
            _str("branch_name", "Optional local branch name for task key hints."),
            _obj("local_observation", "Optional sanitized local Git metadata. If omitted, the stdio connector observes the current workspace automatically."),
            _str("agent_type", default="codex"),
            _str("idempotency_key", "Client-generated idempotency key for safe retries (required by protocol 1.1)."),
        ),
        required=("user_message", "agent_type", "idempotency_key"),
        api_path="/harness/start-work",
        adapter=_start_work_payload,
    ),
    McpToolDefinition(
        name="agora_prepare_context",
        description="Prepare a budgeted, traceable ContextBundle for the current work session.",
        properties=(
            _str("session_id"),
            _str("query"),
            _int("token_budget", default=4000),
            _str("idempotency_key", "Client-generated idempotency key for safe retries (required by protocol 1.1)."),
        ),
        required=("session_id", "idempotency_key"),
        api_path="/harness/prepare-context",
        adapter=_prepare_context_payload,
    ),
    McpToolDefinition(
        name="agora_fetch_context_ref",
        description="Fetch the full content for a source reference returned by agora_prepare_context.",
        properties=(
            _str("session_id"),
            _str("asset_id", "The asset_id from a ContextPack source_refs item."),
            _int("max_tokens", default=2000),
        ),
        required=("session_id", "asset_id"),
        api_path="/harness/fetch-context-ref",
        adapter=_fetch_context_ref_payload,
    ),
    McpToolDefinition(
        name="agora_submit_context_proposal",
        description="Submit an AI-generated project context proposal for human review after analyzing local code and documents.",
        properties=(
            _str("session_id"),
            _str("type", enum=("initial", "refresh", "task_update", "correction")),
            _str("title"),
            _str("summary"),
            _str("target_branch", default="main"),
            _str("expected_head_revision_id"),
            _str("from_commit_sha"),
            _str("to_commit_sha"),
            _obj("content", "Structured context revision candidate generated from local repository analysis."),
            _arr("source_anchors", "object", "Traceable local code or document anchors used to generate the proposal."),
            _obj("provenance", "Tool, schema, repository and model metadata for audit."),
            _str("idempotency_key", "Client-generated idempotency key for safe retries (required by protocol 1.1)."),
        ),
        required=("session_id", "title", "summary", "content", "idempotency_key"),
        api_path="/harness/submit-context-proposal",
        adapter=_submit_context_proposal_payload,
    ),
    McpToolDefinition(
        name="agora_complete_workflow_step",
        description="Complete the current Agora workflow step after producing required artifacts and receiving human confirmation.",
        properties=(
            _str("session_id"),
            _str("step_key", "The current workflow step key, such as analysis, design, review, implementation, self_test, or upload."),
            _str("summary", "Concise evidence-backed summary of what was completed in this step."),
            _arr("artifacts", "object", "Structured artifacts produced for the workflow step."),
            _obj("human_confirmation", "Human review or confirmation record collected in the AI tool before advancing the workflow."),
            _str("idempotency_key", "Client-generated idempotency key for safe retries (required by protocol 1.1)."),
        ),
        required=("session_id", "step_key", "summary", "idempotency_key"),
        api_path="/harness/complete-workflow-step",
        minimum_protocol_version="1.1",
        adapter=_complete_workflow_step_payload,
    ),
    McpToolDefinition(
        name="agora_suggest_skills",
        description="Suggest reusable team SkillCandidates from repeated project work artifacts in the current Agora work session.",
        properties=(
            _str("session_id"),
            _str("query", "Optional experience area, such as release rollback risk or migration review."),
        ),
        required=("session_id",),
        api_path="/harness/suggest-skills",
        adapter=_suggest_skills_payload,
    ),
    McpToolDefinition(
        name="agora_submit_skill_candidate",
        description="Submit a reusable team SkillCandidate from the current work session for human review and approval.",
        properties=(
            _str("session_id"),
            _str("slug"),
            _str("name"),
            _str("summary"),
            _arr("triggers", "string"),
            _str("instructions"),
            _arr("artifact_ids", "string", "WorkArtifact ids that support this candidate."),
            _str("idempotency_key", "Client-generated idempotency key for safe retries (required by protocol 1.1)."),
        ),
        required=("session_id", "slug", "name", "summary", "instructions", "idempotency_key"),
        api_path="/harness/submit-skill-candidate",
        adapter=_submit_skill_candidate_payload,
    ),
    McpToolDefinition(
        name="agora_record_evidence",
        description="Record structured quality evidence such as local tests, CI, review findings, or risk findings for the current work session.",
        properties=(
            _str("session_id"),
            _str("evidence_type", "local_test, ci, review, risk, or another structured evidence type."),
            _str("source", "ai_tool, ci, human_review, or external system."),
            _str("status", enum=("passed", "failed", "warning", "unknown")),
            _str("conclusion"),
            _str("command"),
            _str("output_summary"),
            _str("raw_ref"),
            _obj("metadata"),
            _str("idempotency_key", "Client-generated idempotency key for safe retries (required by protocol 1.1)."),
        ),
        required=("session_id", "evidence_type", "source", "status", "conclusion", "idempotency_key"),
        api_path="/harness/record-evidence",
        adapter=_record_evidence_payload,
    ),
    McpToolDefinition(
        name="agora_get_quality_status",
        description="Get evidence-backed quality status for the current WorkItem or whole project. Failed or missing evidence is never converted into a passing claim.",
        properties=(
            _str("session_id"),
            _str("scope", enum=("work_item", "project")),
        ),
        required=("session_id",),
        api_path="/harness/get-quality-status",
        adapter=_get_quality_status_payload,
    ),
    McpToolDefinition(
        name="agora_get_project_status",
        description="Get project-manager status for WorkItems, stages, quality state, and pending approvals.",
        properties=(
            _str("project_id"),
        ),
        required=("project_id",),
        api_path="/harness/get-project-status",
        adapter=_get_project_status_payload,
    ),
    McpToolDefinition(
        name="agora_get_protocol_manifest",
        description="Return Agora Local Connector and Harness protocol compatibility metadata for AI tool upgrades.",
        properties=(),
        required=(),
        api_path=None,
    ),
    McpToolDefinition(
        name="agora_close_work",
        description="Close an Agora work session. When agent_summary or test_result is provided, the Local Connector captures a bounded development update (relative changed paths and diff-stat counters only) for human review. Server-local repository paths are never accepted.",
        properties=(
            _str("session_id"),
            _str("status", default="closed"),
            _str("agent_summary", "Agent's concise summary of the completed development work (max 8 KiB)."),
            _str("test_result", "Tests or checks run by the agent (max 8 KiB)."),
            _str("idempotency_key", "Client-generated idempotency key for safe retries (required by protocol 1.1)."),
        ),
        required=("session_id", "idempotency_key"),
        api_path="/harness/close-work",
        adapter=_close_work_payload,
    ),
    McpToolDefinition(
        name="agora_plan_context",
        description="Legacy plan-context tool; superseded by agora_prepare_context.",
        properties=(
            _str("session_id"),
            _str("query"),
            _int("token_budget", default=4000),
        ),
        required=("session_id",),
        api_path="/harness/plan-context",
        deprecated=True,
        canonical_tool="agora_prepare_context",
        adapter=_prepare_context_payload,
    ),
    McpToolDefinition(
        name="agora_record_event",
        description="Legacy event recording tool; removed in P2.",
        properties=(
            _str("session_id"),
            _str("event_type"),
            _obj("payload"),
        ),
        required=("session_id", "event_type", "payload"),
        api_path="/harness/record-event",
        deprecated=True,
        canonical_tool=None,
        adapter=_record_event_payload,
    ),
    McpToolDefinition(
        name="agora_prepare_writeback",
        description="Legacy writeback preparation tool; removed in P2.",
        properties=(
            _str("session_id"),
            _str("type", default="development_summary"),
            _str("title"),
            _str("content"),
            _arr("asset_refs", "string"),
        ),
        required=("session_id", "title", "content"),
        api_path="/harness/prepare-writeback",
        deprecated=True,
        canonical_tool=None,
        adapter=_prepare_writeback_payload,
    ),
    McpToolDefinition(
        name="agora_search_knowledge",
        description="Legacy knowledge search tool; superseded by agora_prepare_context.",
        properties=(
            _str("session_id"),
            _str("query"),
            _int("max_results", default=10),
        ),
        required=("session_id", "query"),
        api_path="/harness/plan-context",
        deprecated=True,
        canonical_tool="agora_prepare_context",
        adapter=_search_knowledge_payload,
    ),
)


# --- Registry accessors ------------------------------------------------------

def get_tool_definition(name: str) -> McpToolDefinition | None:
    for definition in TOOL_DEFINITIONS:
        if definition.name == name:
            return definition
    return None


def canonical_tool_names() -> tuple[str, ...]:
    return tuple(definition.name for definition in TOOL_DEFINITIONS if not definition.deprecated)


def deprecated_tool_map() -> dict[str, dict[str, Any]]:
    return {
        definition.name: {
            "canonical_tool": definition.canonical_tool,
            "remove_after": "P2",
        }
        for definition in TOOL_DEFINITIONS
        if definition.deprecated
    }


def tool_schema(definition: McpToolDefinition) -> dict[str, Any]:
    """Build a fresh JSON-schema copy for MCP advertisement."""
    return {
        "type": "object",
        "properties": {
            name: copy.deepcopy(schema)
            for name, schema in definition.properties
        },
        "required": list(definition.required),
        "additionalProperties": False,
    }


def build_remote_payload(definition: McpToolDefinition, arguments: dict[str, Any]) -> dict[str, Any]:
    if definition.adapter is None:
        raise ValueError(f"Tool has no payload adapter: {definition.name}")
    return definition.adapter(arguments)
