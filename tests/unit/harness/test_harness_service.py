from packages.harness.service import HarnessService


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
    )

    assert result.project.id == project.id
    assert result.session_id
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
    assert fake_core.events[-1] == {
        "session_id": start.session_id,
        "event_type": "development_update_captured",
        "payload": {"writeback_id": fake_core.writebacks[0].id, "writeback_type": "development_update"},
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
    )

    assert result.project.id == project.id
    assert result.next_action == "plan_context"
