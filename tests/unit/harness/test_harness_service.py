from packages.core.auth import Principal
from packages.harness.service import HarnessService


def _principal(user_id: str = "user_1", credential_id: str = "credential_1") -> Principal:
    return Principal(
        org_id="org_1",
        user_id=user_id,
        credential_id=credential_id,
        credential_kind="agent",
        token_prefix="test",
    )


def _run_git(repo_path, *args):
    import subprocess

    subprocess.run(["git", *args], cwd=repo_path, check=True, capture_output=True, text=True)


def test_start_work_resolves_project_by_remote(fake_core, fake_context_engine):
    project = fake_core.create_project(
        org_id="org_1",
        name="Payment",
        slug="payment",
        git_remotes=["git@example.com:payment.git"],
    )
    harness = HarnessService(core=fake_core, context_engine=fake_context_engine)

    result = harness.start_work(
        user_message="帮我做 AG-128",
        repo_remote="git@example.com:payment.git",
        agent_type="codex",
        principal=_principal(),
    )

    assert result.project.id == project.id
    assert result.session_id
    assert result.work_item_id == fake_core.work_items[0].id
    assert result.task_id == "AG-128"
    assert result.next_action == "plan_context"


def test_start_work_resolves_project_from_user_message_slug(fake_core, fake_context_engine):
    project = fake_core.create_project(
        org_id="org_1",
        name="df-new-bigdata",
        slug="df-new-bigdata",
        git_remotes=["http://zhangpengfei@192.168.28.114:8080/a/BIGDATA/df-new-bigdata"],
    )
    harness = HarnessService(core=fake_core, context_engine=fake_context_engine)

    result = harness.start_work(
        user_message="基于 Agora 分析 df-new-bigdata 项目的核心模块和风险",
        agent_type="codex",
        principal=_principal(),
    )

    assert result.project.id == project.id
    assert result.next_action == "plan_context"


def test_close_work_can_capture_development_update_from_git_diff(tmp_path, fake_core, fake_context_engine):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    _run_git(repo_path, "init")
    _run_git(repo_path, "config", "user.email", "dev@example.com")
    _run_git(repo_path, "config", "user.name", "Dev")
    source = repo_path / "src" / "payment.py"
    source.parent.mkdir()
    source.write_text("def pay():\n    return 'old'\n", encoding="utf-8")
    _run_git(repo_path, "add", ".")
    _run_git(repo_path, "commit", "-m", "initial")
    source.write_text("def pay():\n    return 'new'\n", encoding="utf-8")

    project = fake_core.create_project(
        org_id="org_1",
        name="Payment",
        slug="payment",
        git_remotes=["git@example.com:payment.git"],
    )
    harness = HarnessService(core=fake_core, context_engine=fake_context_engine)
    start = harness.start_work(
        project_id=project.id,
        user_message="实现支付状态流转",
        agent_type="codex",
        principal=_principal(),
    )

    result = harness.close_work(
        session_id=start.session_id,
        repo_path=str(repo_path),
        agent_summary="实现支付状态流转",
        test_result="pytest tests/payment - passed",
    )

    assert result["status"] == "closed"
    assert result["writeback"]["status"] == "draft"
    assert result["writeback"]["type"] == "development_update"
    assert fake_core.writebacks[0].project_id == project.id
    assert "实现支付状态流转" in fake_core.writebacks[0].content
    assert "src/payment.py" in fake_core.writebacks[0].content
    assert "pytest tests/payment - passed" in fake_core.writebacks[0].content
    event = fake_core.events[-1]
    assert event["session_id"] == start.session_id
    assert event["event_type"] == "development_update_captured"
    assert event["payload"]["writeback_id"] == fake_core.writebacks[0].id
    assert event["payload"]["writeback_type"] == "development_update"
    assert event["payload"]["development_update"]["summary"] == "实现支付状态流转"
    assert event["payload"]["development_update"]["changed_files"][0] == {
        "path": "src/payment.py",
        "status": "修改",
        "category": "源码",
    }


def test_start_work_resolves_project_by_normalized_remote(fake_core, fake_context_engine):
    project = fake_core.create_project(
        org_id="org_1",
        name="df-new-bigdata",
        slug="df-new-bigdata",
        git_remotes=["http://zhangpengfei@192.168.28.114:8080/a/BIGDATA/df-new-bigdata"],
    )
    harness = HarnessService(core=fake_core, context_engine=fake_context_engine)

    result = harness.start_work(
        user_message="分析当前项目",
        repo_remote="http://192.168.28.114:8080/a/BIGDATA/df-new-bigdata.git",
        agent_type="codex",
        principal=_principal(),
    )

    assert result.project.id == project.id
    assert result.next_action == "plan_context"


def test_start_work_infers_analysis_intent_for_project_overview_request(fake_core, fake_context_engine):
    project = fake_core.create_project(
        org_id="org_1",
        name="Payment",
        slug="payment",
        git_remotes=["git@example.com:payment.git"],
    )
    harness = HarnessService(core=fake_core, context_engine=fake_context_engine)

    result = harness.start_work(
        project_id=project.id,
        user_message="介绍一下这个项目",
        agent_type="codex",
        principal=_principal(),
    )

    assert result.intent == "analysis"


def test_start_work_uses_principal_for_work_session_identity(fake_core, fake_context_engine):
    project = fake_core.create_project(
        org_id="org_1",
        name="Payment",
        slug="payment",
        git_remotes=["git@example.com:payment.git"],
    )
    harness = HarnessService(core=fake_core, context_engine=fake_context_engine)

    result = harness.start_work(
        project_id=project.id,
        user_message="实现支付状态流转",
        agent_type="codex",
        principal=_principal(user_id="principal_user", credential_id="principal_credential"),
    )

    assert result.session_id == fake_core.work_sessions[0].id
    assert fake_core.work_sessions[0].user_id == "principal_user"
    assert fake_core.work_sessions[0].credential_id == "principal_credential"
    assert fake_core.sessions == []


def test_two_users_share_one_work_item_but_get_separate_work_sessions(fake_core, fake_context_engine):
    project = fake_core.create_project(
        org_id="org_1",
        name="Payment",
        slug="payment",
        git_remotes=["git@example.com:payment.git"],
    )
    harness = HarnessService(core=fake_core, context_engine=fake_context_engine)

    first = harness.start_work(
        project_id=project.id,
        user_message="帮我做 AG-128：实现支付状态流转",
        agent_type="codex",
        principal=_principal(user_id="user_1", credential_id="credential_1"),
    )
    second = harness.start_work(
        project_id=project.id,
        user_message="继续 AG-128",
        agent_type="codex",
        principal=_principal(user_id="user_2", credential_id="credential_2"),
    )

    assert first.work_item_id == second.work_item_id
    assert first.session_id != second.session_id
    assert [session.user_id for session in fake_core.work_sessions] == ["user_1", "user_2"]


def test_ambiguous_work_item_resolution_asks_user_without_creating_session(fake_core, fake_context_engine):
    project = fake_core.create_project(
        org_id="org_1",
        name="Payment",
        slug="payment",
        git_remotes=["git@example.com:payment.git"],
    )
    fake_core.create_work_item(org_id="org_1", project_id=project.id, title="支付状态流转")
    fake_core.create_work_item(org_id="org_1", project_id=project.id, title="支付回调重试")
    harness = HarnessService(core=fake_core, context_engine=fake_context_engine)

    result = harness.start_work(
        project_id=project.id,
        user_message="继续支付任务",
        agent_type="codex",
        principal=_principal(),
    )

    assert result.session_id is None
    assert result.next_action == "ask_user"
    assert "支付状态流转" in result.clarification
    assert fake_core.work_sessions == []
