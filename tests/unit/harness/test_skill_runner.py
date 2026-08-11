from packages.harness.skill_orchestrator import SkillOrchestrator
from packages.llm.fake_gateway import FakeLlmGateway


def test_impact_analysis_skill_returns_structured_output(fake_core):
    fake_core.create_skill(slug="impact-analysis", status="approved")
    orchestrator = SkillOrchestrator(core=fake_core, llm=FakeLlmGateway())

    result = orchestrator.run_skill(
        session_id="sess_1",
        org_id="org_1",
        project_id="proj_1",
        skill_slug="impact-analysis",
        input={"task": "refund retry"},
        context={"summary": "Refund retry touches refund-service."},
    )

    assert result.skill_run_id
    assert "risks" in result.output
