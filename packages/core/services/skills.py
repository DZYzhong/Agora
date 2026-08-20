from sqlalchemy import select

from packages.core.models import ProjectModel


BUILT_IN_SKILLS = {
    "task-context-summary": {"name": "Task Context Summary"},
    "impact-analysis": {"name": "Impact Analysis"},
    "test-case-generation": {"name": "Test Case Generation"},
    "risk-check": {"name": "Risk Check"},
    "knowledge-writeback": {"name": "Knowledge Writeback"},
}


def ensure_builtin_skills(runtime, *, org_id: str) -> None:
    for slug, definition in BUILT_IN_SKILLS.items():
        if runtime.get_skill_by_slug(slug) is None:
            runtime.create_skill(
                org_id=org_id,
                project_id=None,
                slug=slug,
                name=definition["name"],
                status="approved",
                definition={"builtin": True, "version": "1.0.0"},
            )


def ensure_builtin_skills_for_existing_projects(runtime) -> None:
    org_ids = list(runtime.session.scalars(select(ProjectModel.org_id).distinct()).all())
    for org_id in org_ids:
        ensure_builtin_skills(runtime, org_id=org_id)


def get_builtin_skill(slug: str) -> dict | None:
    return BUILT_IN_SKILLS.get(slug)
