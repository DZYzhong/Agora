from apps.mcp.tools import AgoraMcpTools


class FakeHarness:
    def __init__(self):
        self.started = False
        self.closed_with = None
        self.fetched_with = None

    def start_work(self, **kwargs):
        self.started = True
        return type(
            "Result",
            (),
            {
                "session_id": "sess_1",
                "project": None,
                "task_id": "AG-128",
                "intent": "implementation",
                "next_action": "plan_context",
                "clarification": None,
            },
        )()

    def close_work(self, **kwargs):
        self.closed_with = kwargs
        return {"session_id": kwargs["session_id"], "status": kwargs.get("status", "closed"), "writeback": {"id": "wb_1"}}

    def fetch_context_ref(self, **kwargs):
        self.fetched_with = kwargs
        return {
            "session_id": kwargs["session_id"],
            "asset_id": kwargs["asset_id"],
            "content": "source content",
        }


def test_mcp_start_work_delegates_to_harness():
    fake_harness = FakeHarness()
    tools = AgoraMcpTools(harness=fake_harness)

    result = tools.agora_start_work(
        user_message="帮我做 AG-128",
        repo_remote="git@example.com:payment.git",
        agent_type="codex",
    )

    assert result["session_id"] == "sess_1"
    assert fake_harness.started


def test_mcp_close_work_passes_development_capture_arguments():
    fake_harness = FakeHarness()
    tools = AgoraMcpTools(harness=fake_harness)

    result = tools.agora_close_work(
        session_id="sess_1",
        status="closed",
        repo_path="/tmp/repo",
        agent_summary="完成新功能",
        test_result="pytest passed",
    )

    assert result["writeback"]["id"] == "wb_1"
    assert fake_harness.closed_with == {
        "session_id": "sess_1",
        "status": "closed",
        "repo_path": "/tmp/repo",
        "base_ref": "HEAD",
        "head_ref": None,
        "agent_summary": "完成新功能",
        "test_result": "pytest passed",
    }


def test_mcp_fetch_context_ref_delegates_to_harness():
    fake_harness = FakeHarness()
    tools = AgoraMcpTools(harness=fake_harness)

    result = tools.agora_fetch_context_ref(session_id="sess_1", asset_id="asset_1", max_tokens=100)

    assert result["content"] == "source content"
    assert fake_harness.fetched_with == {
        "session_id": "sess_1",
        "asset_id": "asset_1",
        "max_tokens": 100,
    }
