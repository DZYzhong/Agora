from dataclasses import dataclass, field

from packages.core.services.skills import get_builtin_skill
from packages.llm.structured_output import ensure_dict_output


@dataclass(frozen=True)
class SkillRunResult:
    skill_run_id: str
    output: dict
    warnings: list[str] = field(default_factory=list)
    confidence: float | None = None
    next_steps: list[str] = field(default_factory=list)


class SkillOrchestrator:
    def __init__(self, *, core, llm):
        self.core = core
        self.llm = llm

    def run_skill(
        self,
        *,
        session_id: str | None = None,
        org_id: str,
        project_id: str,
        skill_slug: str,
        input: dict,
        context: dict,
    ) -> SkillRunResult:
        try:
            skill = self.core.get_skill_by_slug(skill_slug, project_id=project_id)
        except TypeError:
            skill = self.core.get_skill_by_slug(skill_slug)
        if skill is None and get_builtin_skill(skill_slug):
            skill = self.core.create_skill(slug=skill_slug, status="approved", name=get_builtin_skill(skill_slug)["name"])
        if skill is None:
            raise ValueError(f"Skill not found: {skill_slug}")
        if skill.status != "approved":
            raise ValueError(f"Skill is not approved: {skill_slug}")

        output = ensure_dict_output(self.llm.generate_structured(task=skill_slug, context=context))
        run = self.core.create_skill_run(
            org_id=org_id,
            project_id=project_id,
            session_id=session_id,
            skill_id=skill.id,
            input=input,
            output=output,
            warnings=[],
            status="completed",
        )
        return SkillRunResult(skill_run_id=run.id, output=output, warnings=[])
