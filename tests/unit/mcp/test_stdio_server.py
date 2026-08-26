import asyncio

from apps.mcp.server import _dispatch, list_tools


def test_stdio_mcp_server_lists_agora_tools():
    result = asyncio.run(list_tools(None, None))
    tool_names = {tool.name for tool in result.tools}

    assert tool_names == {
        "agora_start_work",
        "agora_prepare_context",
        "agora_fetch_context_ref",
        "agora_submit_context_proposal",
        "agora_submit_skill_candidate",
        "agora_suggest_skills",
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

    proposal_tool = next(tool for tool in result.tools if tool.name == "agora_submit_context_proposal")
    assert "session_id" in proposal_tool.input_schema["required"]
    assert "content" in proposal_tool.input_schema["required"]

    skill_tool = next(tool for tool in result.tools if tool.name == "agora_submit_skill_candidate")
    assert "session_id" in skill_tool.input_schema["required"]
    assert "instructions" in skill_tool.input_schema["required"]

    suggest_tool = next(tool for tool in result.tools if tool.name == "agora_suggest_skills")
    assert "session_id" in suggest_tool.input_schema["required"]


def test_stdio_submit_context_proposal_dispatches_to_harness(monkeypatch):
    captured = {}

    async def fake_post(path, payload):
        captured["path"] = path
        captured["payload"] = payload
        return {"protocol_version": "1.0", "operation": "submit_context_proposal", "proposal": {"id": "proposal_1"}}

    monkeypatch.setattr("apps.mcp.server._post", fake_post)

    result = asyncio.run(
        _dispatch(
            "agora_submit_context_proposal",
            {
                "session_id": "sess_1",
                "type": "task_update",
                "title": "PAY-318 退款审计上下文更新",
                "summary": "记录退款状态审计的上下文变化。",
                "target_branch": "main",
                "content": {"modules": [{"path": "src/refund/service.py"}]},
                "source_anchors": [{"kind": "code", "path": "src/refund/service.py"}],
                "provenance": {"generating_tool": "codex"},
            },
        )
    )

    assert result["proposal"]["id"] == "proposal_1"
    assert captured["path"] == "/harness/submit-context-proposal"
    assert captured["payload"]["session_id"] == "sess_1"
    assert captured["payload"]["content"]["modules"][0]["path"] == "src/refund/service.py"


def test_stdio_submit_skill_candidate_dispatches_to_harness(monkeypatch):
    captured = {}

    async def fake_post(path, payload):
        captured["path"] = path
        captured["payload"] = payload
        return {"protocol_version": "1.0", "operation": "submit_skill_candidate", "skill": {"id": "skill_1"}}

    monkeypatch.setattr("apps.mcp.server._post", fake_post)

    result = asyncio.run(
        _dispatch(
            "agora_submit_skill_candidate",
            {
                "session_id": "sess_1",
                "slug": "release-risk-review",
                "name": "Release Risk Review",
                "summary": "沉淀发布风险检查经验。",
                "triggers": ["release", "risk"],
                "instructions": "检查测试证据和回滚方案。",
                "artifact_ids": ["artifact_1"],
            },
        )
    )

    assert result["skill"]["id"] == "skill_1"
    assert captured["path"] == "/harness/submit-skill-candidate"
    assert captured["payload"]["slug"] == "release-risk-review"
    assert captured["payload"]["artifact_ids"] == ["artifact_1"]


def test_stdio_suggest_skills_dispatches_to_harness(monkeypatch):
    captured = {}

    async def fake_post(path, payload):
        captured["path"] = path
        captured["payload"] = payload
        return {"protocol_version": "1.0", "operation": "suggest_skills", "suggestions": [{"slug": "release-risk-review"}]}

    monkeypatch.setattr("apps.mcp.server._post", fake_post)

    result = asyncio.run(
        _dispatch(
            "agora_suggest_skills",
            {
                "session_id": "sess_1",
                "query": "发布风险检查",
            },
        )
    )

    assert result["suggestions"][0]["slug"] == "release-risk-review"
    assert captured["path"] == "/harness/suggest-skills"
    assert captured["payload"] == {"session_id": "sess_1", "query": "发布风险检查"}


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
