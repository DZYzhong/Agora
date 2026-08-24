import asyncio

from apps.mcp.server import _dispatch, list_tools


def test_stdio_mcp_server_lists_agora_tools():
    result = asyncio.run(list_tools(None, None))
    tool_names = {tool.name for tool in result.tools}

    assert tool_names == {
        "agora_start_work",
        "agora_prepare_context",
        "agora_fetch_context_ref",
        "agora_close_work",
    }

    fetch_tool = next(tool for tool in result.tools if tool.name == "agora_fetch_context_ref")
    assert "asset_id" in fetch_tool.input_schema["properties"]
    assert "asset_id" in fetch_tool.input_schema["required"]

    start_tool = next(tool for tool in result.tools if tool.name == "agora_start_work")
    assert "branch_name" in start_tool.input_schema["properties"]
    assert "local_observation" in start_tool.input_schema["properties"]

    context_tool = next(tool for tool in result.tools if tool.name == "agora_prepare_context")
    assert "token_budget" in context_tool.input_schema["properties"]


def test_stdio_start_work_observes_local_workspace_when_not_supplied(monkeypatch):
    captured = {}

    class FakeObservation:
        def model_dump(self):
            return {
                "repository": {
                    "host": "git.example.cn",
                    "path": "team/payment-service",
                    "normalized": "git.example.cn/team/payment-service",
                },
                "branch_name": "feature/AG-128",
                "head_commit": "0123456789abcdef",
                "dirty": True,
                "changed_file_count": 1,
                "untracked_file_count": 0,
                "observer": "agora-mcp",
            }

    async def fake_post(path, payload):
        captured["path"] = path
        captured["payload"] = payload
        return {"protocol_version": "1.0", "session_id": "sess_1"}

    monkeypatch.setattr("apps.mcp.server.observe_git_workspace", lambda: FakeObservation())
    monkeypatch.setattr("apps.mcp.server._post", fake_post)

    result = asyncio.run(
        _dispatch(
            "agora_start_work",
            {
                "user_message": "实现 AG-128",
                "agent_type": "codex",
            },
        )
    )

    assert result["session_id"] == "sess_1"
    assert captured["path"] == "/harness/start-work"
    assert captured["payload"]["local_observation"]["repository"]["normalized"] == "git.example.cn/team/payment-service"
    assert "repo_path" not in captured["payload"]["local_observation"]


def test_legacy_plan_context_dispatch_is_accepted_but_marked_deprecated(monkeypatch):
    async def fake_post(path, payload):
        return {
            "operation": "prepare_context",
            "path": path,
            "payload": payload,
            "deprecation": {"legacy_endpoint": "/harness/plan-context"},
        }

    monkeypatch.setattr("apps.mcp.server._post", fake_post)

    result = asyncio.run(
        _dispatch(
            "agora_plan_context",
            {
                "session_id": "sess_1",
                "query": "refund retry",
                "token_budget": 700,
            },
        )
    )

    assert result["operation"] == "prepare_context"
    assert result["path"] == "/harness/plan-context"
    assert result["deprecation"]["legacy_tool"] == "agora_plan_context"
    assert result["deprecation"]["canonical_tool"] == "agora_prepare_context"
