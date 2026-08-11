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
