from packages.harness.service import HarnessService


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
