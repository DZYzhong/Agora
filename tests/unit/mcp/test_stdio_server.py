import asyncio

import httpx

from apps.mcp.server import _dispatch, _post, list_tools
from packages.core.services.mcp_tools import (
    TOOL_DEFINITIONS,
    canonical_tool_names,
    get_tool_definition,
    tool_schema,
)
from packages.core.services.protocol import CANONICAL_MCP_TOOLS, DEPRECATED_MCP_TOOLS, build_protocol_manifest


def test_stdio_mcp_server_lists_agora_tools():
    result = asyncio.run(list_tools(None, None))
    tool_names = {tool.name for tool in result.tools}

    assert tool_names == {
        "agora_start_work",
        "agora_prepare_context",
        "agora_fetch_context_ref",
        "agora_submit_context_proposal",
        "agora_complete_workflow_step",
        "agora_submit_skill_candidate",
        "agora_suggest_skills",
        "agora_record_evidence",
        "agora_get_quality_status",
        "agora_get_project_status",
        "agora_get_protocol_manifest",
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

    workflow_tool = next(tool for tool in result.tools if tool.name == "agora_complete_workflow_step")
    assert "session_id" in workflow_tool.input_schema["required"]
    assert "step_key" in workflow_tool.input_schema["required"]
    assert "human_confirmation" in workflow_tool.input_schema["properties"]

    skill_tool = next(tool for tool in result.tools if tool.name == "agora_submit_skill_candidate")
    assert "session_id" in skill_tool.input_schema["required"]
    assert "instructions" in skill_tool.input_schema["required"]

    suggest_tool = next(tool for tool in result.tools if tool.name == "agora_suggest_skills")
    assert "session_id" in suggest_tool.input_schema["required"]

    evidence_tool = next(tool for tool in result.tools if tool.name == "agora_record_evidence")
    assert "session_id" in evidence_tool.input_schema["required"]
    assert "status" in evidence_tool.input_schema["required"]

    quality_tool = next(tool for tool in result.tools if tool.name == "agora_get_quality_status")
    assert "session_id" in quality_tool.input_schema["required"]

    project_tool = next(tool for tool in result.tools if tool.name == "agora_get_project_status")
    assert "project_id" in project_tool.input_schema["required"]

    manifest_tool = next(tool for tool in result.tools if tool.name == "agora_get_protocol_manifest")
    assert manifest_tool.input_schema["required"] == []


def test_stdio_protocol_manifest_reports_versions_and_tool_compatibility():
    result = asyncio.run(_dispatch("agora_get_protocol_manifest", {}))

    assert result["format"] == "agora-protocol-manifest/v1"
    assert result["mcp_server"]["name"] == "agora"
    assert result["mcp_server"]["version"]
    assert result["harness_protocol"]["current"] == "1.1"
    assert result["harness_protocol"]["supported"] == ["1.0", "1.1"]
    assert "agora_prepare_context" in result["tools"]["canonical"]
    assert result["tools"]["deprecated"]["agora_plan_context"]["canonical_tool"] == "agora_prepare_context"
    assert result["compatibility"]["minimum_local_connector_version"]


def test_stdio_post_sends_current_protocol_and_connector_headers(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

    class FakeAsyncClient:
        def __init__(self, *, base_url, timeout):
            captured["base_url"] = base_url
            captured["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, path, *, json, headers):
            captured["path"] = path
            captured["json"] = json
            captured["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    result = asyncio.run(_post("/harness/get-project-status", {"project_id": "project_1"}))

    assert result == {"ok": True}
    assert captured["headers"]["Agora-Protocol-Version"] == "1.1"
    assert captured["headers"]["Agora-Connector-Version"] == "0.1.0"


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


def test_stdio_complete_workflow_step_dispatches_to_harness(monkeypatch):
    captured = {}

    async def fake_post(path, payload):
        captured["path"] = path
        captured["payload"] = payload
        return {"protocol_version": "1.1", "operation": "complete_workflow_step", "completed_step": {"step_key": "analysis"}}

    monkeypatch.setattr("apps.mcp.server._post", fake_post)

    result = asyncio.run(
        _dispatch(
            "agora_complete_workflow_step",
            {
                "session_id": "sess_1",
                "step_key": "analysis",
                "summary": "分析完成，人工已确认。",
                "artifacts": [{"type": "analysis_note", "title": "分析记录", "content": "影响面已确认。"}],
                "human_confirmation": {"confirmation_type": "step_review", "decision": "approved"},
            },
        )
    )

    assert result["completed_step"]["step_key"] == "analysis"
    assert captured["path"] == "/harness/complete-workflow-step"
    assert captured["payload"]["summary"] == "分析完成，人工已确认。"
    assert captured["payload"]["artifacts"][0]["title"] == "分析记录"
    assert captured["payload"]["human_confirmation"]["decision"] == "approved"


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


def test_stdio_record_evidence_dispatches_to_harness(monkeypatch):
    captured = {}

    async def fake_post(path, payload):
        captured["path"] = path
        captured["payload"] = payload
        return {"protocol_version": "1.0", "operation": "record_evidence", "evidence": {"id": "evidence_1"}}

    monkeypatch.setattr("apps.mcp.server._post", fake_post)

    result = asyncio.run(
        _dispatch(
            "agora_record_evidence",
            {
                "session_id": "sess_1",
                "evidence_type": "local_test",
                "source": "ai_tool",
                "status": "failed",
                "conclusion": "pytest failed",
                "command": "pytest tests/payment",
                "output_summary": "1 failed",
                "raw_ref": "local://pytest/payment",
                "metadata": {"commit_sha": "abc123"},
            },
        )
    )

    assert result["evidence"]["id"] == "evidence_1"
    assert captured["path"] == "/harness/record-evidence"
    assert captured["payload"]["status"] == "failed"


def test_stdio_quality_and_project_status_dispatch_to_harness(monkeypatch):
    captured = []

    async def fake_post(path, payload):
        captured.append((path, payload))
        return {"protocol_version": "1.0", "operation": path.rsplit("/", 1)[-1].replace("-", "_")}

    monkeypatch.setattr("apps.mcp.server._post", fake_post)

    quality = asyncio.run(_dispatch("agora_get_quality_status", {"session_id": "sess_1", "scope": "work_item"}))
    project = asyncio.run(_dispatch("agora_get_project_status", {"project_id": "project_1"}))

    assert quality["operation"] == "get_quality_status"
    assert project["operation"] == "get_project_status"
    assert captured == [
        ("/harness/get-quality-status", {"session_id": "sess_1", "scope": "work_item"}),
        ("/harness/get-project-status", {"project_id": "project_1"}),
    ]


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


def test_stdio_close_work_schema_excludes_server_repository_paths():
    result = asyncio.run(list_tools(None, None))
    tool = next(item for item in result.tools if item.name == "agora_close_work")

    properties = tool.input_schema["properties"]
    assert "session_id" in tool.input_schema["required"]
    assert "agent_summary" in properties
    assert "test_result" in properties
    assert "repo_path" not in properties
    assert "base_ref" not in properties
    assert "head_ref" not in properties


def test_stdio_close_work_builds_local_development_capture(monkeypatch):
    captured = {}

    async def fake_post(path, payload):
        captured["path"] = path
        captured["payload"] = payload
        return {"protocol_version": "1.1", "session_id": "sess_1", "status": "closed"}

    def fake_capture():
        return {
            "changed_files": [{"path": "src/app.py", "status": "modified"}],
            "dirty": True,
            "diff_stat": {"files_changed": 1, "insertions": 2, "deletions": 1},
        }

    monkeypatch.setattr("apps.mcp.server.capture_local_development_change", fake_capture)
    monkeypatch.setattr("apps.mcp.server._post", fake_post)

    result = asyncio.run(
        _dispatch(
            "agora_close_work",
            {
                "session_id": "sess_1",
                "agent_summary": "完成新功能",
                "test_result": "pytest passed",
            },
        )
    )

    assert result["session_id"] == "sess_1"
    assert captured["path"] == "/harness/close-work"
    assert captured["payload"]["session_id"] == "sess_1"
    assert captured["payload"]["development_update"]["agent_summary"] == "完成新功能"
    assert captured["payload"]["development_update"]["test_result"] == "pytest passed"
    assert captured["payload"]["development_update"]["changed_files"] == [
        {"path": "src/app.py", "status": "modified"}
    ]
    assert "repo_path" not in captured["payload"]
    assert "base_ref" not in captured["payload"]
    assert "head_ref" not in captured["payload"]


def test_stdio_close_work_without_summary_sends_no_development_update(monkeypatch):
    captured = {}

    async def fake_post(path, payload):
        captured["path"] = path
        captured["payload"] = payload
        return {"protocol_version": "1.1", "session_id": "sess_1", "status": "closed"}

    monkeypatch.setattr("apps.mcp.server._post", fake_post)

    result = asyncio.run(_dispatch("agora_close_work", {"session_id": "sess_1"}))

    assert result["status"] == "closed"
    assert captured["payload"]["development_update"] is None


# --- Task 6: canonical immutable tool/handler registry ----------------------


def test_registry_canonical_names_match_manifest_and_dispatch_keys():
    canonical = canonical_tool_names()
    registry_names = {definition.name for definition in TOOL_DEFINITIONS if not definition.deprecated}

    assert set(canonical) == registry_names
    assert set(canonical) == set(CANONICAL_MCP_TOOLS)
    for name in canonical:
        assert get_tool_definition(name) is not None

    manifest = build_protocol_manifest()
    assert set(manifest["tools"]["canonical"]) == set(canonical)
    assert set(manifest["tools"]["deprecated"]) == set(DEPRECATED_MCP_TOOLS)


def test_registry_deprecated_aliases_share_registry():
    assert set(DEPRECATED_MCP_TOOLS) == {
        "agora_plan_context",
        "agora_record_event",
        "agora_prepare_writeback",
        "agora_search_knowledge",
    }
    for name in DEPRECATED_MCP_TOOLS:
        definition = get_tool_definition(name)
        assert definition is not None
        assert definition.deprecated is True


def test_registry_schemas_use_immutable_storage_and_fresh_copies():
    for definition in TOOL_DEFINITIONS:
        assert isinstance(definition.properties, tuple)
        assert isinstance(definition.required, tuple)

        first = tool_schema(definition)
        second = tool_schema(definition)
        assert first == second
        assert first is not second
        assert first["properties"] is not second["properties"]

        if first["properties"]:
            key = next(iter(first["properties"]))
            first["properties"][key]["type"] = "integer"
        assert tool_schema(definition) == second


def test_registry_canonical_tools_include_workflow_completion():
    assert "agora_complete_workflow_step" in canonical_tool_names()


def test_registry_every_definition_exposes_minimum_protocol_version():
    for definition in TOOL_DEFINITIONS:
        assert definition.minimum_protocol_version in ("1.0", "1.1")
    workflow_completion = get_tool_definition("agora_complete_workflow_step")
    assert workflow_completion.minimum_protocol_version == "1.1"


MINIMAL_DISPATCH_ARGUMENTS = {
    "agora_start_work": {"user_message": "task", "agent_type": "codex", "local_observation": {"dirty": False}},
    "agora_prepare_context": {"session_id": "sess_1"},
    "agora_fetch_context_ref": {"session_id": "sess_1", "asset_id": "asset_1"},
    "agora_submit_context_proposal": {"session_id": "sess_1", "title": "t", "summary": "m", "content": {}},
    "agora_complete_workflow_step": {"session_id": "sess_1", "step_key": "analysis", "summary": "m"},
    "agora_suggest_skills": {"session_id": "sess_1"},
    "agora_submit_skill_candidate": {"session_id": "sess_1", "slug": "x", "name": "n", "summary": "m", "instructions": "i"},
    "agora_record_evidence": {"session_id": "sess_1", "evidence_type": "local_test", "source": "ai_tool", "status": "passed", "conclusion": "c"},
    "agora_get_quality_status": {"session_id": "sess_1"},
    "agora_get_project_status": {"project_id": "project_1"},
    "agora_close_work": {"session_id": "sess_1"},
    "agora_plan_context": {"session_id": "sess_1"},
    "agora_record_event": {"session_id": "sess_1", "event_type": "e", "payload": {}},
    "agora_prepare_writeback": {"session_id": "sess_1", "title": "t", "content": "c"},
    "agora_search_knowledge": {"session_id": "sess_1", "query": "q"},
}


def test_registry_parameterized_dispatch_posts_every_remote_definition_to_declared_path(monkeypatch):
    captured = {}

    async def fake_post(path, payload):
        captured["path"] = path
        captured["payload"] = payload
        return {"ok": True}

    monkeypatch.setattr("apps.mcp.server._post", fake_post)

    for definition in TOOL_DEFINITIONS:
        if definition.api_path is None:
            continue
        arguments = dict(MINIMAL_DISPATCH_ARGUMENTS[definition.name])
        result = asyncio.run(_dispatch(definition.name, arguments))

        assert captured["path"] == definition.api_path, definition.name
        assert result["ok"] is True
        if definition.deprecated:
            assert result["deprecation"]["legacy_tool"] == definition.name
            assert result["deprecation"]["canonical_tool"] == definition.canonical_tool


def test_registry_local_manifest_definition_has_no_api_path():
    definition = get_tool_definition("agora_get_protocol_manifest")
    assert definition is not None
    assert definition.api_path is None
    assert definition.adapter is None

    result = asyncio.run(_dispatch("agora_get_protocol_manifest", {}))
    assert result["format"] == "agora-protocol-manifest/v1"
