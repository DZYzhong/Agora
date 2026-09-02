import asyncio
import json
import os
from typing import Any

import httpx
from mcp import types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.stdio import stdio_server

from packages.core.services.mcp_tools import (
    TOOL_DEFINITIONS,
    build_remote_payload,
    get_tool_definition,
    tool_schema,
)
from packages.core.services.protocol import HARNESS_PROTOCOL_CURRENT, MCP_SERVER_NAME, MCP_SERVER_VERSION, build_protocol_manifest
from packages.local_connector.development_capture import capture_local_development_change
from packages.local_connector.git_observer import observe_git_workspace

AGORA_API_URL = os.environ.get("AGORA_API_URL", "http://127.0.0.1:8000")
AGORA_AGENT_TOKEN = os.environ.get("AGORA_AGENT_TOKEN")

TOOLS = [
    types.Tool(
        name=definition.name,
        description=definition.description,
        inputSchema=tool_schema(definition),
    )
    for definition in TOOL_DEFINITIONS
    if not definition.deprecated
]


async def _post(path: str, payload: dict[str, Any], *, idempotency_key: str | None = None) -> dict[str, Any]:
    headers = {
        "Agora-Protocol-Version": HARNESS_PROTOCOL_CURRENT,
        "Agora-Connector-Version": MCP_SERVER_VERSION,
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    if AGORA_AGENT_TOKEN:
        headers["Authorization"] = f"Bearer {AGORA_AGENT_TOKEN}"
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
    definition = get_tool_definition(name)
    if definition is None:
        raise ValueError(f"Unknown tool: {name}")
    if definition.api_path is None:
        if definition.name == "agora_get_protocol_manifest":
            return build_protocol_manifest()
        raise ValueError(f"Tool has no remote handler: {name}")

    idempotency_key = arguments.pop("idempotency_key", None)
    if name == "agora_start_work" and not arguments.get("local_observation"):
        arguments["local_observation"] = observe_git_workspace().model_dump()
    if name == "agora_close_work":
        agent_summary = arguments.get("agent_summary")
        test_result = arguments.get("test_result")
        if (agent_summary or test_result) and arguments.get("development_update") is None:
            arguments["development_update"] = {
                **capture_local_development_change(),
                "agent_summary": agent_summary,
                "test_result": test_result,
            }

    payload = build_remote_payload(definition, arguments)
    result = await _post(definition.api_path, payload, idempotency_key=idempotency_key)
    if definition.deprecated:
        result = _with_tool_deprecation(result, legacy_tool=definition.name, canonical_tool=definition.canonical_tool)
    return result


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
