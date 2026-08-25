from apps.mcp.tools import AgoraMcpTools


class FakeHarness:
    def __init__(self):
        self.started = False
        self.closed_with = None
        self.fetched_with = None
        self.submitted_with = None
        self.completed_step_with = None

    def start_work(self, **kwargs):
        self.started = True
        self.started_with = kwargs
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

    def prepare_context(self, **kwargs):
        self.prepared_with = kwargs
        return {"operation": "prepare_context", "session_id": kwargs["session_id"], "budget": {"estimated_tokens": 100}}

    def fetch_context_ref(self, **kwargs):
        self.fetched_with = kwargs
        return {
            "session_id": kwargs["session_id"],
            "asset_id": kwargs["asset_id"],
            "content": "source content",
        }

    def submit_context_proposal(self, **kwargs):
        self.submitted_with = kwargs
        return {
            "operation": "submit_context_proposal",
            "proposal": {"id": "proposal_1", "session_id": kwargs["session_id"]},
        }

    def complete_workflow_step(self, **kwargs):
        self.completed_step_with = kwargs
        return {
            "operation": "complete_workflow_step",
            "session_id": kwargs["session_id"],
            "completed_step": {"step_key": kwargs["step_key"], "status": "completed"},
            "artifacts": kwargs.get("artifacts", []),
            "human_confirmation": kwargs.get("human_confirmation"),
        }


def test_mcp_start_work_delegates_to_harness():
    fake_harness = FakeHarness()
    tools = AgoraMcpTools(harness=fake_harness)

    result = tools.agora_start_work(
        user_message="帮我做 AG-128",
        repo_remote="git@example.com:payment.git",
        agent_type="codex",
        branch_name="feature/AG-128-payments",
        local_observation={"dirty": False},
        principal="principal",
    )

    assert result["session_id"] == "sess_1"
    assert fake_harness.started
    assert fake_harness.started_with["branch_name"] == "feature/AG-128-payments"
    assert fake_harness.started_with["local_observation"] == {"dirty": False}
    assert fake_harness.started_with["principal"] == "principal"


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


def test_mcp_prepare_context_delegates_to_harness():
    fake_harness = FakeHarness()
    tools = AgoraMcpTools(harness=fake_harness)

    result = tools.agora_prepare_context(session_id="sess_1", query="refund retry", token_budget=800)

    assert result["operation"] == "prepare_context"
    assert fake_harness.prepared_with == {
        "session_id": "sess_1",
        "query": "refund retry",
        "token_budget": 800,
    }


def test_mcp_submit_context_proposal_delegates_to_harness():
    fake_harness = FakeHarness()
    tools = AgoraMcpTools(harness=fake_harness)

    result = tools.agora_submit_context_proposal(
        session_id="sess_1",
        type="task_update",
        title="PAY-318 退款审计上下文更新",
        summary="记录退款状态审计的上下文变化。",
        target_branch="main",
        content={"risks": ["状态重复流转会产生重复审计"]},
        source_anchors=[{"kind": "code", "path": "src/refund/service.py"}],
        provenance={"generating_tool": "codex"},
    )

    assert result["proposal"]["id"] == "proposal_1"
    assert fake_harness.submitted_with == {
        "session_id": "sess_1",
        "type": "task_update",
        "title": "PAY-318 退款审计上下文更新",
        "summary": "记录退款状态审计的上下文变化。",
        "target_branch": "main",
        "expected_head_revision_id": None,
        "from_commit_sha": None,
        "to_commit_sha": None,
        "content": {"risks": ["状态重复流转会产生重复审计"]},
        "source_anchors": [{"kind": "code", "path": "src/refund/service.py"}],
        "provenance": {"generating_tool": "codex"},
    }


def test_mcp_complete_workflow_step_delegates_to_harness():
    fake_harness = FakeHarness()
    tools = AgoraMcpTools(harness=fake_harness)

    result = tools.agora_complete_workflow_step(
        session_id="sess_1",
        step_key="analysis",
        summary="分析完成，确认支付状态流转影响面。",
        principal="principal",
    )

    assert result["completed_step"]["step_key"] == "analysis"
    assert fake_harness.completed_step_with == {
        "session_id": "sess_1",
        "step_key": "analysis",
        "summary": "分析完成，确认支付状态流转影响面。",
        "artifacts": [],
        "human_confirmation": None,
        "principal": "principal",
    }


def test_mcp_complete_workflow_step_passes_artifacts_and_human_confirmation():
    fake_harness = FakeHarness()
    tools = AgoraMcpTools(harness=fake_harness)

    result = tools.agora_complete_workflow_step(
        session_id="sess_1",
        step_key="analysis",
        summary="完成任务分析。",
        artifacts=[
            {
                "type": "analysis_note",
                "title": "AG-300 分析记录",
                "content": "识别权限校验和审计日志影响面。",
                "metadata": {"path": "docs/tasks/AG-300/analysis.md"},
            }
        ],
        human_confirmation={
            "confirmation_type": "step_review",
            "decision": "approved",
            "comment": "可以进入设计。",
        },
        principal="principal",
    )

    assert result["artifacts"][0]["type"] == "analysis_note"
    assert result["human_confirmation"]["decision"] == "approved"
    assert fake_harness.completed_step_with["artifacts"][0]["title"] == "AG-300 分析记录"
    assert fake_harness.completed_step_with["human_confirmation"]["comment"] == "可以进入设计。"
