from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db_session
from packages.core.services.runtime import CoreRuntime
from packages.core.services.skills import BUILT_IN_SKILLS
from packages.domain.enums import SkillStatus
from packages.harness.skill_orchestrator import SkillOrchestrator
from packages.llm.fake_gateway import FakeLlmGateway

router = APIRouter(prefix="/projects/{project_id}", tags=["skills"])


class SkillCreateRequest(BaseModel):
    slug: str
    name: str
    status: SkillStatus = SkillStatus.CANDIDATE
    definition: dict = Field(default_factory=dict)


class SkillUpdateRequest(BaseModel):
    name: str | None = None
    status: SkillStatus | None = None
    definition: dict | None = None


class SkillRunRequest(BaseModel):
    session_id: str | None = None
    input: dict = Field(default_factory=dict)
    context: dict = Field(default_factory=dict)


def _serialize_skill(skill, *, builtin: bool = False) -> dict:
    return {
        "id": skill.id,
        "org_id": skill.org_id,
        "project_id": skill.project_id,
        "slug": skill.slug,
        "name": skill.name,
        "status": skill.status,
        "definition": skill.definition,
        "builtin": builtin,
        "created_at": skill.created_at,
    }


def _serialize_run(run) -> dict:
    return {
        "id": run.id,
        "org_id": run.org_id,
        "project_id": run.project_id,
        "session_id": run.session_id,
        "skill_id": run.skill_id,
        "input": run.input,
        "output": run.output,
        "warnings": run.warnings,
        "status": run.status,
        "created_at": run.created_at,
    }


def _ensure_project(runtime: CoreRuntime, project_id: str):
    project = runtime.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _is_builtin_skill(skill) -> bool:
    return skill.project_id is None or bool((skill.definition or {}).get("builtin"))


def _ensure_project_skill(skill, project_id: str) -> None:
    if _is_builtin_skill(skill):
        raise HTTPException(status_code=400, detail="Built-in skills are read-only")
    if skill.project_id != project_id:
        raise HTTPException(status_code=404, detail="Skill not found")


def _ensure_builtin_skills(runtime: CoreRuntime, *, org_id: str) -> None:
    for slug, definition in BUILT_IN_SKILLS.items():
        if runtime.get_skill_by_slug(slug) is None:
            runtime.create_skill(
                org_id=org_id,
                project_id=None,
                slug=slug,
                name=definition["name"],
                status=SkillStatus.APPROVED.value,
                definition={"builtin": True, "version": "1.0.0"},
            )


@router.get("/skills")
def list_skills(project_id: str, session: Session = Depends(get_db_session)):
    runtime = CoreRuntime(session)
    project = _ensure_project(runtime, project_id)
    _ensure_builtin_skills(runtime, org_id=project.org_id)
    return [
        _serialize_skill(skill, builtin=bool((skill.definition or {}).get("builtin")))
        for skill in runtime.list_skills_by_project(project_id)
    ]


@router.post("/skills", status_code=status.HTTP_201_CREATED)
def create_skill(project_id: str, payload: SkillCreateRequest, session: Session = Depends(get_db_session)):
    runtime = CoreRuntime(session)
    project = _ensure_project(runtime, project_id)
    skill = runtime.create_skill(
        org_id=project.org_id,
        project_id=project.id,
        slug=payload.slug,
        name=payload.name,
        status=payload.status.value,
        definition=payload.definition,
    )
    return _serialize_skill(skill)


@router.patch("/skills/{skill_id}")
def update_skill(project_id: str, skill_id: str, payload: SkillUpdateRequest, session: Session = Depends(get_db_session)):
    runtime = CoreRuntime(session)
    _ensure_project(runtime, project_id)
    try:
        skill = runtime.get_skill(skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    _ensure_project_skill(skill, project_id)
    skill = runtime.update_skill(
        skill_id,
        name=payload.name,
        status=payload.status.value if payload.status else None,
        definition=payload.definition,
    )
    return _serialize_skill(skill, builtin=bool((skill.definition or {}).get("builtin")))


@router.post("/skills/{skill_id}/approve")
def approve_skill(project_id: str, skill_id: str, session: Session = Depends(get_db_session)):
    runtime = CoreRuntime(session)
    _ensure_project(runtime, project_id)
    try:
        skill = runtime.get_skill(skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    _ensure_project_skill(skill, project_id)
    skill = runtime.update_skill(skill_id, status=SkillStatus.APPROVED.value)
    return _serialize_skill(skill, builtin=bool((skill.definition or {}).get("builtin")))


@router.post("/skills/{skill_id}/deprecate")
def deprecate_skill(project_id: str, skill_id: str, session: Session = Depends(get_db_session)):
    runtime = CoreRuntime(session)
    _ensure_project(runtime, project_id)
    try:
        skill = runtime.get_skill(skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    _ensure_project_skill(skill, project_id)
    skill = runtime.update_skill(skill_id, status=SkillStatus.DEPRECATED.value)
    return _serialize_skill(skill, builtin=bool((skill.definition or {}).get("builtin")))


@router.post("/skills/{skill_id}/run")
def run_skill(project_id: str, skill_id: str, payload: SkillRunRequest, session: Session = Depends(get_db_session)):
    runtime = CoreRuntime(session)
    project = _ensure_project(runtime, project_id)
    skill = runtime.get_skill(skill_id)
    if skill is None or skill.project_id not in (project_id, None):
        raise HTTPException(status_code=404, detail="Skill not found")
    if skill.status != SkillStatus.APPROVED.value:
        error = f"Skill is not approved: {skill.slug}"
        runtime.create_skill_run(
            org_id=project.org_id,
            project_id=project.id,
            session_id=payload.session_id,
            skill_id=skill.id,
            input=payload.input,
            output={"error": error},
            warnings=[error],
            status="failed",
        )
        raise HTTPException(status_code=400, detail=error)
    try:
        result = SkillOrchestrator(core=runtime, llm=FakeLlmGateway()).run_skill(
            session_id=payload.session_id,
            org_id=project.org_id,
            project_id=project.id,
            skill_slug=skill.slug,
            input=payload.input,
            context=payload.context,
        )
    except ValueError as exc:
        runtime.create_skill_run(
            org_id=project.org_id,
            project_id=project.id,
            session_id=payload.session_id,
            skill_id=skill.id,
            input=payload.input,
            output={"error": str(exc)},
            warnings=[str(exc)],
            status="failed",
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    run = next(run for run in runtime.list_skill_runs_by_project(project.id) if run.id == result.skill_run_id)
    return _serialize_run(run)


@router.get("/skill-runs")
def list_skill_runs(project_id: str, session: Session = Depends(get_db_session)):
    runtime = CoreRuntime(session)
    _ensure_project(runtime, project_id)
    return [_serialize_run(run) for run in runtime.list_skill_runs_by_project(project_id)]
