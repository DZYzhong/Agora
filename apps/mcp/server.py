import asyncio
import json
import os
from typing import Any

import httpx
from mcp import types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.stdio import stdio_server

from packages.core.services.protocol import MCP_SERVER_NAME, MCP_SERVER_VERSION, build_protocol_manifest
from packages.local_connector.git_observer import observe_git_workspace

AGORA_API_URL = os.environ.get("AGORA_API_URL", "http://127.0.0.1:8000")
AGORA_AGENT_TOKEN = os.environ.get("AGORA_AGENT_TOKEN")


def _tool(name: str, description: str, properties: dict[str, Any], required: list[str]) -> types.Tool:
    return types.Tool(
        name=name,
        description=description,
        inputSchema={
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    )


TOOLS = [
    _tool(
        "agora_start_work",
        "Start an Agora work session for project-aware AI work. Use this before local code analysis. The user_message may include the project name or slug; repo_remote is optional fallback.",
        {
            "user_message": {"type": "string", "description": "Original user request, including project name/slug when available."},
            "repo_remote": {"type": "string", "description": "Optional git origin remote. Agora also accepts normalized remotes without username or .git suffix."},
            "branch_name": {"type": "string", "description": "Optional local branch name for task key hints."},
            "local_observation": {
                "type": "object",
                "description": "Optional sanitized local Git metadata. If omitted, the stdio connector observes the current workspace automatically.",
            },
            "agent_type": {"type": "string", "default": "codex"},
        },
        ["user_message", "agent_type"],
    ),
    _tool(
        "agora_prepare_context",
        "Prepare a budgeted, traceable ContextBundle for the current work session.",
        {
            "session_id": {"type": "string"},
            "query": {"type": "string"},
            "token_budget": {"type": "integer", "default": 4000},
        },
        ["session_id"],
    ),
    _tool(
        "agora_fetch_context_ref",
        "Fetch the full content for a source reference returned by agora_prepare_context.",
        {
            "session_id": {"type": "string"},
            "asset_id": {"type": "string", "description": "The asset_id from a ContextPack source_refs item."},
            "max_tokens": {"type": "integer", "default": 2000},
        },
        ["session_id", "asset_id"],
    ),
    _tool(
        "agora_submit_context_proposal",
        "Submit an AI-generated project context proposal for human review after analyzing local code and documents.",
        {
            "session_id": {"type": "string"},
            "type": {
                "type": "string",
                "enum": ["initial", "refresh", "task_update", "correction"],
                "default": "task_update",
            },
            "title": {"type": "string"},
            "summary": {"type": "string"},
            "target_branch": {"type": "string", "default": "main"},
            "expected_head_revision_id": {"type": "string"},
            "from_commit_sha": {"type": "string"},
            "to_commit_sha": {"type": "string"},
            "content": {
                "type": "object",
                "description": "Structured context revision candidate generated from local repository analysis.",
            },
            "source_anchors": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Traceable local code or document anchors used to generate the proposal.",
            },
            "provenance": {
                "type": "object",
                "description": "Tool, schema, repository and model metadata for audit.",
            },
        },
        ["session_id", "title", "summary", "content"],
    ),
    _tool(
        "agora_suggest_skills",
        "Suggest reusable team SkillCandidates from repeated project work artifacts in the current Agora work session.",
        {
            "session_id": {"type": "string"},
            "query": {"type": "string", "description": "Optional experience area, such as release rollback risk or migration review."},
        },
        ["session_id"],
    ),
    _tool(
        "agora_submit_skill_candidate",
        "Submit a reusable team SkillCandidate from the current work session for human review and approval.",
        {
            "session_id": {"type": "string"},
            "slug": {"type": "string"},
            "name": {"type": "string"},
            "summary": {"type": "string"},
            "triggers": {"type": "array", "items": {"type": "string"}},
            "instructions": {"type": "string"},
            "artifact_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "WorkArtifact ids that support this candidate.",
            },
        },
        ["session_id", "slug", "name", "summary", "instructions"],
    ),
    _tool(
        "agora_record_evidence",
        "Record structured quality evidence such as local tests, CI, review findings, or risk findings for the current work session.",
        {
            "session_id": {"type": "string"},
            "evidence_type": {"type": "string", "description": "local_test, ci, review, risk, or another structured evidence type."},
            "source": {"type": "string", "description": "ai_tool, ci, human_review, or external system."},
            "status": {"type": "string", "enum": ["passed", "failed", "warning", "unknown"]},
            "conclusion": {"type": "string"},
            "command": {"type": "string"},
            "output_summary": {"type": "string"},
            "raw_ref": {"type": "string"},
            "metadata": {"type": "object"},
        },
        ["session_id", "evidence_type", "source", "status", "conclusion"],
    ),
    _tool(
        "agora_get_quality_status",
        "Get evidence-backed quality status for the current WorkItem or whole project. Failed or missing evidence is never converted into a passing claim.",
        {
            "session_id": {"type": "string"},
            "scope": {"type": "string", "enum": ["work_item", "project"], "default": "work_item"},
        },
        ["session_id"],
    ),
    _tool(
        "agora_get_project_status",
        "Get project-manager status for WorkItems, stages, quality state, and pending approvals.",
        {
            "project_id": {"type": "string"},
        },
        ["project_id"],
    ),
    _tool(
        "agora_get_protocol_manifest",
        "Return Agora Local Connector and Harness protocol compatibility metadata for AI tool upgrades.",
        {},
        [],
    ),
    _tool(
        "agora_close_work",
        "Close an Agora work session. When repo_path or agent_summary is provided, Agora captures a development_update draft for human review.",
        {
            "session_id": {"type": "string"},
            "status": {"type": "string", "default": "closed"},
            "repo_path": {"type": "string", "description": "Optional local git repository path used to summarize the development diff."},
            "base_ref": {"type": "string", "default": "HEAD", "description": "Git base ref for diff capture. Defaults to HEAD versus working tree."},
            "head_ref": {"type": "string", "description": "Optional git head ref. If omitted, Agora compares base_ref to the working tree."},
            "agent_summary": {"type": "string", "description": "Agent's concise summary of the completed development work."},
            "test_result": {"type": "string", "description": "Tests or checks run by the agent."},
        },
        ["session_id"],
    ),
]


async def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {AGORA_AGENT_TOKEN}"} if AGORA_AGENT_TOKEN else {}
    async with httpx.AsyncClient(base_url=AGORA_API_URL, timeout=30) as client:
        response = await client.post(path, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


async def list_tools(_ctx, _params) -> types.ListToolsResult:
    return types.ListToolsResult(tools=TOOLS)


async def call_tool(_ctx, params: types.CallToolRequestParams) -> types.CallToolResult:
    arguments = params.arguments or {}
    try:
        result = await _dispatch(params.name, arguments)
        return types.CallToolResult(
            content=[types.TextContent(text=json.dumps(result, ensure_ascii=False, indent=2))],
            structuredContent=result,
        )
    except Exception as exc:
        return types.CallToolResult(content=[types.TextContent(text=str(exc))], isError=True)


async def _dispatch(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "agora_get_protocol_manifest":
        return build_protocol_manifest()
    if name == "agora_start_work":
        local_observation = arguments.get("local_observation") or observe_git_workspace().model_dump()
        return await _post(
            "/harness/start-work",
            {
                "user_message": arguments["user_message"],
                "repo_remote": arguments.get("repo_remote"),
                "branch_name": arguments.get("branch_name"),
                "local_observation": local_observation,
                "agent_type": arguments.get("agent_type", "codex"),
            },
        )
    if name == "agora_prepare_context":
        return await _post(
            "/harness/prepare-context",
            {
                "session_id": arguments["session_id"],
                "query": arguments.get("query"),
                "token_budget": arguments.get("token_budget", 4000),
            },
        )
    if name == "agora_plan_context":
        result = await _post(
            "/harness/plan-context",
            {
                "session_id": arguments["session_id"],
                "query": arguments.get("query"),
                "token_budget": arguments.get("token_budget", 4000),
            },
        )
        return _with_tool_deprecation(result, legacy_tool=name, canonical_tool="agora_prepare_context")
    if name == "agora_fetch_context_ref":
        return await _post(
            "/harness/fetch-context-ref",
            {
                "session_id": arguments["session_id"],
                "asset_id": arguments["asset_id"],
                "max_tokens": arguments.get("max_tokens", 2000),
            },
        )
    if name == "agora_submit_context_proposal":
        return await _post(
            "/harness/submit-context-proposal",
            {
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
            },
        )
    if name == "agora_suggest_skills":
        return await _post(
            "/harness/suggest-skills",
            {
                "session_id": arguments["session_id"],
                "query": arguments.get("query"),
            },
        )
    if name == "agora_submit_skill_candidate":
        return await _post(
            "/harness/submit-skill-candidate",
            {
                "session_id": arguments["session_id"],
                "slug": arguments["slug"],
                "name": arguments["name"],
                "summary": arguments["summary"],
                "triggers": arguments.get("triggers", []),
                "instructions": arguments["instructions"],
                "artifact_ids": arguments.get("artifact_ids", []),
            },
        )
    if name == "agora_record_evidence":
        return await _post(
            "/harness/record-evidence",
            {
                "session_id": arguments["session_id"],
                "evidence_type": arguments["evidence_type"],
                "source": arguments["source"],
                "status": arguments["status"],
                "conclusion": arguments["conclusion"],
                "command": arguments.get("command"),
                "output_summary": arguments.get("output_summary"),
                "raw_ref": arguments.get("raw_ref"),
                "metadata": arguments.get("metadata", {}),
            },
        )
    if name == "agora_get_quality_status":
        return await _post(
            "/harness/get-quality-status",
            {
                "session_id": arguments["session_id"],
                "scope": arguments.get("scope", "work_item"),
            },
        )
    if name == "agora_get_project_status":
        return await _post(
            "/harness/get-project-status",
            {
                "project_id": arguments["project_id"],
            },
        )
    if name == "agora_record_event":
        result = await _post(
            "/harness/record-event",
            {
                "session_id": arguments["session_id"],
                "event_type": arguments["event_type"],
                "payload": arguments["payload"],
            },
        )
        return _with_tool_deprecation(result, legacy_tool=name, canonical_tool=None)
    if name == "agora_prepare_writeback":
        result = await _post(
            "/harness/prepare-writeback",
            {
                "session_id": arguments["session_id"],
                "type": arguments.get("type", "development_summary"),
                "title": arguments["title"],
                "content": arguments["content"],
                "asset_refs": arguments.get("asset_refs", []),
            },
        )
        return _with_tool_deprecation(result, legacy_tool=name, canonical_tool=None)
    if name == "agora_close_work":
        return await _post(
            "/harness/close-work",
            {
                "session_id": arguments["session_id"],
                "status": arguments.get("status", "closed"),
                "repo_path": arguments.get("repo_path"),
                "base_ref": arguments.get("base_ref", "HEAD"),
                "head_ref": arguments.get("head_ref"),
                "agent_summary": arguments.get("agent_summary"),
                "test_result": arguments.get("test_result"),
            },
        )
    if name == "agora_search_knowledge":
        result = await _post(
            "/harness/plan-context",
            {
                "session_id": arguments["session_id"],
                "query": arguments["query"],
                "token_budget": arguments.get("token_budget", 4000),
            },
        )
        return _with_tool_deprecation(result, legacy_tool=name, canonical_tool="agora_prepare_context")
    raise ValueError(f"Unknown tool: {name}")


def _with_tool_deprecation(result: dict[str, Any], *, legacy_tool: str, canonical_tool: str | None) -> dict[str, Any]:
    deprecation = {
        "legacy_tool": legacy_tool,
        "canonical_tool": canonical_tool,
        "remove_after": "P2",
    }
    existing = result.get("deprecation")
    if isinstance(existing, dict):
        result["deprecation"] = {**existing, **deprecation}
    else:
        result["deprecation"] = deprecation
    return result


async def run() -> None:
    server = Server(MCP_SERVER_NAME, version=MCP_SERVER_VERSION, on_list_tools=list_tools, on_call_tool=call_tool)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(notification_options=NotificationOptions()),
        )


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
