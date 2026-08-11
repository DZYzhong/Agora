from apps.mcp.tools import AgoraMcpTools


class FakeHarness:
    def __init__(self):
        self.started = False

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
