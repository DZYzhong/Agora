import asyncio

from apps.mcp.server import list_tools


def test_stdio_mcp_server_lists_agora_tools():
    result = asyncio.run(list_tools(None, None))
    tool_names = {tool.name for tool in result.tools}

    assert "agora_start_work" in tool_names
    assert "agora_plan_context" in tool_names
    assert "agora_fetch_context_ref" in tool_names
    assert "agora_prepare_writeback" in tool_names
    assert "agora_close_work" in tool_names

    fetch_tool = next(tool for tool in result.tools if tool.name == "agora_fetch_context_ref")
    assert "asset_id" in fetch_tool.input_schema["properties"]
    assert "asset_id" in fetch_tool.input_schema["required"]
