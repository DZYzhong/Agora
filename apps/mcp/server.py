import asyncio
import json
import os
from typing import Any

import httpx
from mcp import types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.stdio import stdio_server

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
            "agent_type": {"type": "string", "default": "codex"},
        },
        ["user_message", "agent_type"],
    ),
    _tool(
        "agora_plan_context",
        "Retrieve a compressed, traceable project context pack for the current work session.",
        {
            "session_id": {"type": "string"},
            "query": {"type": "string"},
            "token_budget": {"type": "integer", "default": 4000},
        },
        ["session_id"],
    ),
    _tool(
        "agora_fetch_context_ref",
        "Fetch the full content for a source reference returned by agora_plan_context.",
        {
            "session_id": {"type": "string"},
            "asset_id": {"type": "string", "description": "The asset_id from a ContextPack source_refs item."},
            "max_tokens": {"type": "integer", "default": 2000},
        },
        ["session_id", "asset_id"],
    ),
    _tool(
        "agora_record_event",
        "Record an AI work event into Agora.",
        {
            "session_id": {"type": "string"},
            "event_type": {"type": "string"},
            "payload": {"type": "object"},
        },
        ["session_id", "event_type", "payload"],
    ),
    _tool(
        "agora_prepare_writeback",
        "Prepare AI-generated project knowledge for human review.",
        {
            "session_id": {"type": "string"},
            "type": {"type": "string", "default": "development_summary"},
            "title": {"type": "string"},
            "content": {"type": "string"},
            "asset_refs": {"type": "array", "items": {"type": "string"}},
        },
        ["session_id", "type", "title", "content"],
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
    _tool(
        "agora_search_knowledge",
        "Search Agora project knowledge through the current session context planner.",
        {
            "session_id": {"type": "string"},
            "query": {"type": "string"},
            "token_budget": {"type": "integer", "default": 4000},
        },
        ["session_id", "query"],
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
    if name == "agora_start_work":
        return await _post(
            "/harness/start-work",
            {
                "user_message": arguments["user_message"],
                "repo_remote": arguments.get("repo_remote"),
                "agent_type": arguments.get("agent_type", "codex"),
            },
        )
    if name == "agora_plan_context":
        return await _post(
            "/harness/plan-context",
            {
                "session_id": arguments["session_id"],
                "query": arguments.get("query"),
                "token_budget": arguments.get("token_budget", 4000),
            },
        )
    if name == "agora_fetch_context_ref":
        return await _post(
            "/harness/fetch-context-ref",
            {
                "session_id": arguments["session_id"],
                "asset_id": arguments["asset_id"],
                "max_tokens": arguments.get("max_tokens", 2000),
            },
        )
    if name == "agora_record_event":
        return await _post(
            "/harness/record-event",
            {
                "session_id": arguments["session_id"],
                "event_type": arguments["event_type"],
                "payload": arguments["payload"],
            },
        )
    if name == "agora_prepare_writeback":
        return await _post(
            "/harness/prepare-writeback",
            {
                "session_id": arguments["session_id"],
                "type": arguments.get("type", "development_summary"),
                "title": arguments["title"],
                "content": arguments["content"],
                "asset_refs": arguments.get("asset_refs", []),
            },
        )
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
        return await _post(
            "/harness/plan-context",
            {
                "session_id": arguments["session_id"],
                "query": arguments["query"],
                "token_budget": arguments.get("token_budget", 4000),
            },
        )
    raise ValueError(f"Unknown tool: {name}")


async def run() -> None:
    server = Server("agora", version="0.1.0", on_list_tools=list_tools, on_call_tool=call_tool)
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
