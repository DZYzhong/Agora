import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.auth import get_current_principal, require_human, require_project_approver, require_project_member
from apps.api.dependencies import get_db_session
from packages.core.auth import Principal
from packages.core.services.approval_grants import ApprovalDeniedError, approval_payload_digest, require_approval_capability
from packages.core.services.runtime import CoreRuntime
from packages.core.uow import SqlAlchemyUnitOfWork
from packages.domain.enums import SkillStatus
from packages.harness.skill_orchestrator import SkillOrchestrator
from packages.llm.fake_gateway import FakeLlmGateway

router = APIRouter(prefix="/projects/{project_id}", tags=["skills"])
logger = logging.getLogger(__name__)


class SkillCreateRequest(BaseModel):
    slug: str
    name: str
    status: SkillStatus = SkillStatus.CANDIDATE
    definition: dict = Field(default_factory=dict)


class SkillUpdateRequest(BaseModel):
    name: str | None = None
    status: SkillStatus | None = None
    definition: dict | None = None


class SkillApproveRequest(BaseModel):
    name: str | None = None
    definition: dict | None = None
    approval_grant_id: str | None = None


class SkillRunRequest(BaseModel):
    session_id: str | None = None
    input: dict = Field(default_factory=dict)
    context: dict = Field(default_factory=dict)


class _SkillExecutionFailed(Exception):
    def __init__(
        self,
        *,
        error: str,
        org_id: str,
        project_id: str,
        session_id: str | None,
        skill_id: str,
        input: dict,
    ):
        super().__init__(error)
        self.error = error
        self.org_id = org_id
        self.project_id = project_id
        self.session_id = session_id
        self.skill_id = skill_id
        self.input = input


def _content_preview(content: str, *, limit: int = 160) -> str:
    compact = " ".join(content.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 1]}..."


def _serialize_evidence_refs(runtime: CoreRuntime, skill) -> list[dict]:
    refs: list[dict] = []
    evidence_ids = (skill.definition or {}).get("evidence_writeback_ids") or []
    writebacks = runtime.list_writebacks_by_ids(evidence_ids)
    refs.extend(
        {
            "id": writeback.id,
            "source": "writeback",
            "type": writeback.type,
            "title": writeback.title,
            "status": writeback.status,
            "accepted_asset_id": writeback.accepted_asset_id,
            "content_preview": _content_preview(writeback.content),
        }
        for writeback in writebacks
    )
    artifact_ids = (skill.definition or {}).get("evidence_artifact_ids") or []
    if artifact_ids and hasattr(runtime, "list_work_artifacts_by_ids"):
        refs.extend(
            {
                "id": artifact.id,
                "source": "work_artifact",
                "type": artifact.type,
                "title": artifact.title,
                "status": "submitted",
                "accepted_asset_id": None,
                "content_preview": _content_preview(artifact.content),
            }
            for artifact in runtime.list_work_artifacts_by_ids(artifact_ids)
        )
    return refs


def _serialize_skill(skill, *, runtime: CoreRuntime | None = None, builtin: bool = False) -> dict:
    current_version = runtime.get_current_skill_version(skill.id) if runtime is not None and hasattr(runtime, "get_current_skill_version") else None
    return {
        "id": skill.id,
        "org_id": skill.org_id,
        "project_id": skill.project_id,
        "slug": skill.slug,
        "name": skill.name,
        "status": skill.status,
        "definition": skill.definition,
        "current_version_id": skill.current_version_id,
        "current_version": _serialize_skill_version(current_version) if current_version is not None else None,
        "evidence_refs": _serialize_evidence_refs(runtime, skill) if runtime is not None else [],
        "builtin": builtin,
        "created_at": skill.created_at,
    }


def _serialize_skill_version(version) -> dict:
    return {
        "id": version.id,
        "org_id": version.org_id,
        "project_id": version.project_id,
        "skill_id": version.skill_id,
        "version": version.version,
        "status": version.status,
        "definition": version.definition,
        "approved_by_user_id": version.approved_by_user_id,
        "created_at": version.created_at,
    }


def _serialize_run(run) -> dict:
    return {
        "id": run.id,
        "org_id": run.org_id,
        "project_id": run.project_id,
        "session_id": run.session_id,
        "skill_id": run.skill_id,
        "skill_version_id": run.skill_version_id,
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


def _ensure_session_in_project(runtime: CoreRuntime, *, project_id: str, session_id: str | None) -> None:
    if session_id is None:
        return
    task_session = runtime.get_session(session_id)
    if task_session is None or task_session.project_id != project_id:
        raise HTTPException(status_code=404, detail="Session not found")


def _is_builtin_skill(skill) -> bool:
    return skill.project_id is None or bool((skill.definition or {}).get("builtin"))


def _ensure_project_skill(skill, project_id: str) -> None:
    if _is_builtin_skill(skill):
        raise HTTPException(status_code=400, detail="Built-in skills are read-only")
    if skill.project_id != project_id:
        raise HTTPException(status_code=404, detail="Skill not found")


def _record_failed_skill_run(session: Session, failure: _SkillExecutionFailed) -> None:
    with SqlAlchemyUnitOfWork(session) as uow:
        CoreRuntime(session).create_skill_run(
            org_id=failure.org_id,
            project_id=failure.project_id,
            session_id=failure.session_id,
            skill_id=failure.skill_id,
            input=failure.input,
            output={"error": failure.error},
            warnings=[failure.error],
            status="failed",
        )
        uow.commit()


@router.get("/skills")
def list_skills(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    runtime = CoreRuntime(session)
    _ensure_project(runtime, project_id)
    require_project_member(session, principal, project_id=project_id)
    return [
        _serialize_skill(skill, runtime=runtime, builtin=bool((skill.definition or {}).get("builtin")))
        for skill in runtime.list_skills_by_project(project_id)
    ]


@router.post("/skills", status_code=status.HTTP_201_CREATED)
def create_skill(
    project_id: str,
    payload: SkillCreateRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    require_human(principal)
    with SqlAlchemyUnitOfWork(session) as uow:
        runtime = CoreRuntime(session)
        project = _ensure_project(runtime, project_id)
        require_project_member(session, principal, project_id=project.id)
        skill = runtime.create_skill(
            org_id=project.org_id,
            project_id=project.id,
            slug=payload.slug,
            name=payload.name,
            status=payload.status.value,
            definition=payload.definition,
        )
        response = _serialize_skill(skill, runtime=runtime)
        uow.commit()
    return response


@router.patch("/skills/{skill_id}")
def update_skill(
    project_id: str,
    skill_id: str,
    payload: SkillUpdateRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    require_human(principal)
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            runtime = CoreRuntime(session)
            project = _ensure_project(runtime, project_id)
            require_project_member(session, principal, project_id=project.id)
            skill = runtime.get_skill(skill_id)
            if skill is None:
                raise HTTPException(status_code=404, detail="Skill not found")
            _ensure_project_skill(skill, project_id)
            skill = runtime.update_skill(
                skill_id,
                name=payload.name,
                status=payload.status.value if payload.status else None,
                definition=payload.definition,
            )
            response = _serialize_skill(skill, runtime=runtime, builtin=bool((skill.definition or {}).get("builtin")))
            uow.commit()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return response


@router.post("/skills/{skill_id}/approve")
def approve_skill(
    project_id: str,
    skill_id: str,
    payload: SkillApproveRequest | None = None,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            runtime = CoreRuntime(session)
            project = _ensure_project(runtime, project_id)
            require_project_member(session, principal, project_id=project.id)
            skill = runtime.get_skill(skill_id)
            if skill is None:
                raise HTTPException(status_code=404, detail="Skill not found")
            _ensure_project_skill(skill, project_id)
            try:
                require_approval_capability(
                    session,
                    principal=principal,
                    org_id=project.org_id,
                    object_type="skill",
                    object_id=skill.id,
                    payload_digest=approval_payload_digest(
                        skill.id,
                        skill.slug,
                        skill.name,
                        payload.name if payload is not None else None,
                        payload.definition if payload is not None else None,
                    ),
                    decision="approved",
                    grant_id=payload.approval_grant_id if payload is not None else None,
                )
            except ApprovalDeniedError as exc:
                _record_security_audit(
                    runtime,
                    project=project,
                    principal=principal,
                    action="skill.approve",
                    target_type="skill",
                    target_id=skill.id,
                    decision="deny",
                    reason=exc.code,
                    metadata={"detail": exc.message},
                )
                uow.commit()
                raise HTTPException(status_code=403, detail={"code": exc.code, "message": exc.message}) from exc
            try:
                require_project_approver(session, principal, project_id=project.id)
            except HTTPException as exc:
                _record_security_audit(
                    runtime,
                    project=project,
                    principal=principal,
                    action="skill.approve",
                    target_type="skill",
                    target_id=skill.id,
                    decision="deny",
                    reason="PROJECT_ROLE_REQUIRED",
                    metadata={"detail": exc.detail},
                )
                uow.commit()
                raise
            definition = skill.definition
            if payload is not None and payload.definition is not None:
                definition = {
                    **(skill.definition or {}),
                    **payload.definition,
                    "evidence_writeback_ids": (skill.definition or {}).get("evidence_writeback_ids") or [],
                    "evidence_artifact_ids": (skill.definition or {}).get("evidence_artifact_ids") or [],
                    "source": (skill.definition or {}).get("source"),
                    "session_id": (skill.definition or {}).get("session_id"),
                    "work_item_id": (skill.definition or {}).get("work_item_id"),
                    "submitted_by_user_id": (skill.definition or {}).get("submitted_by_user_id"),
                }
            skill = runtime.update_skill(
                skill_id,
                name=payload.name if payload is not None else None,
                status=SkillStatus.APPROVED.value,
                definition=definition,
            )
            runtime.ensure_approved_skill_version(skill.id, approved_by_user_id=principal.user_id)
            response = _serialize_skill(skill, runtime=runtime, builtin=bool((skill.definition or {}).get("builtin")))
            _record_security_audit(
                runtime,
                project=project,
                principal=principal,
                action="skill.approve",
                target_type="skill",
                target_id=skill.id,
                decision="allow",
                reason="PROJECT_APPROVER",
                metadata={"skill_version_id": response["current_version"]["id"] if response.get("current_version") else None},
            )
            uow.commit()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return response


def _record_security_audit(
    runtime: CoreRuntime,
    *,
    project,
    principal: Principal,
    action: str,
    target_type: str,
    target_id: str,
    decision: str,
    reason: str,
    metadata: dict | None = None,
) -> None:
    runtime.create_security_audit_event(
        org_id=project.org_id,
        project_id=project.id,
        actor_user_id=principal.user_id,
        actor_credential_id=None if principal.is_bypass else principal.credential_id,
        actor_credential_kind=principal.credential_kind,
        action=action,
        target_type=target_type,
        target_id=target_id,
        decision=decision,
        reason=reason,
        metadata=metadata or {},
    )


@router.post("/skills/{skill_id}/deprecate")
def deprecate_skill(
    project_id: str,
    skill_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    require_human(principal)
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            runtime = CoreRuntime(session)
            project = _ensure_project(runtime, project_id)
            require_project_member(session, principal, project_id=project.id)
            skill = runtime.get_skill(skill_id)
            if skill is None:
                raise HTTPException(status_code=404, detail="Skill not found")
            _ensure_project_skill(skill, project_id)
            skill = runtime.update_skill(skill_id, status=SkillStatus.DEPRECATED.value)
            response = _serialize_skill(skill, runtime=runtime, builtin=bool((skill.definition or {}).get("builtin")))
            uow.commit()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return response


@router.post("/skills/{skill_id}/run")
def run_skill(
    project_id: str,
    skill_id: str,
    payload: SkillRunRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            runtime = CoreRuntime(session)
            project = _ensure_project(runtime, project_id)
            require_project_member(session, principal, project_id=project.id)
            _ensure_session_in_project(runtime, project_id=project.id, session_id=payload.session_id)
            skill = runtime.get_skill(skill_id)
            if skill is None or skill.project_id not in (project_id, None):
                raise HTTPException(status_code=404, detail="Skill not found")
            if skill.status != SkillStatus.APPROVED.value:
                raise HTTPException(status_code=400, detail=f"Skill is not approved: {skill.slug}")
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
                raise _SkillExecutionFailed(
                    error=str(exc),
                    org_id=project.org_id,
                    project_id=project.id,
                    session_id=payload.session_id,
                    skill_id=skill.id,
                    input=payload.input,
                ) from exc
            run = next(run for run in runtime.list_skill_runs_by_project(project.id) if run.id == result.skill_run_id)
            response = _serialize_run(run)
            uow.commit()
    except _SkillExecutionFailed as exc:
        try:
            _record_failed_skill_run(session, exc)
        except Exception:
            logger.exception("Failed to record failed SkillRun audit for skill %s", exc.skill_id)
        raise HTTPException(status_code=400, detail=exc.error) from exc
    return response


@router.get("/skill-runs")
def list_skill_runs(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    runtime = CoreRuntime(session)
    _ensure_project(runtime, project_id)
    require_project_member(session, principal, project_id=project_id)
    return [_serialize_run(run) for run in runtime.list_skill_runs_by_project(project_id)]
