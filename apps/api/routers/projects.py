import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.auth import get_current_principal, require_human, require_project_member
from apps.api.dependencies import get_db_session, get_keyword_index, get_vector_index
from apps.workers.workflows.initialize_project import initialize_project_from_local_repo
from packages.core.repositories.assets import AssetRepository
from packages.core.repositories.identities import IdentityRepository
from packages.core.repositories.initialization_jobs import InitializationJobRepository
from packages.core.repositories.projects import ProjectRepository
from packages.core.auth import Principal
from packages.core.services.runtime import CoreRuntime
from packages.core.services.skills import ensure_builtin_skills
from packages.core.uow import SqlAlchemyUnitOfWork
from packages.domain.schemas import AssetCreate, ProjectCreate, ProjectRead
from packages.integrations.git.clone import GitCloneError, clone_repository
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex

router = APIRouter(prefix="/projects", tags=["projects"])
logger = logging.getLogger(__name__)


class InitializeLocalProjectRequest(BaseModel):
    repo_path: str


def _serialize_initialization_job(job) -> dict:
    return {
        "id": job.id,
        "org_id": job.org_id,
        "project_id": job.project_id,
        "repo_path": job.repo_path,
        "git_remote": job.git_remote,
        "status": job.status,
        "asset_count": job.asset_count,
        "error": job.error,
        "warnings": job.warnings,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def _serialize_security_audit_event(event) -> dict:
    return {
        "id": event.id,
        "org_id": event.org_id,
        "project_id": event.project_id,
        "actor_user_id": event.actor_user_id,
        "actor_credential_id": event.actor_credential_id,
        "actor_credential_kind": event.actor_credential_kind,
        "action": event.action,
        "target_type": event.target_type,
        "target_id": event.target_id,
        "decision": event.decision,
        "reason": event.reason,
        "metadata": event.event_metadata,
        "created_at": event.created_at,
    }


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    require_human(principal)
    with SqlAlchemyUnitOfWork(session) as uow:
        values = payload.model_dump()
        values["org_id"] = payload.org_id if principal.is_bypass else principal.org_id
        project = ProjectRepository(session).create(**values)
        if not principal.is_bypass:
            IdentityRepository(session).grant_membership(project_id=project.id, user_id=principal.user_id, role="owner")
        ensure_builtin_skills(CoreRuntime(session), org_id=project.org_id)
        response = ProjectRead(
            id=project.id,
            org_id=project.org_id,
            name=project.name,
            slug=project.slug,
            description=project.description,
            git_remotes=project.git_remotes,
            default_branch=project.default_branch,
            status=project.status,
        )
        uow.commit()
    return response


@router.get("", response_model=list[ProjectRead])
def list_projects(
    include_archived: bool = Query(default=False),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    repo = ProjectRepository(session)
    projects = (
        repo.list(include_archived=include_archived)
        if principal.is_bypass
        else repo.list_for_user(user_id=principal.user_id, include_archived=include_archived)
    )
    return [
        ProjectRead(
            id=project.id,
            org_id=project.org_id,
            name=project.name,
            slug=project.slug,
            description=project.description,
            git_remotes=project.git_remotes,
            default_branch=project.default_branch,
            status=project.status,
        )
        for project in projects
    ]


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    project = ProjectRepository(session).get(project_id)
    if project is None or (not principal.is_bypass and project.org_id != principal.org_id):
        raise HTTPException(status_code=404, detail="Project not found")
    require_project_member(session, principal, project_id=project.id)
    return ProjectRead(
        id=project.id,
        org_id=project.org_id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        git_remotes=project.git_remotes,
        default_branch=project.default_branch,
        status=project.status,
    )


@router.get("/{project_id}/security-audit")
def list_security_audit(
    project_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    project = ProjectRepository(session).get(project_id)
    if project is None or (not principal.is_bypass and project.org_id != principal.org_id):
        raise HTTPException(status_code=404, detail="Project not found")
    require_project_member(session, principal, project_id=project.id)
    return [_serialize_security_audit_event(event) for event in CoreRuntime(session).list_security_audit_events_by_project(project.id, limit=limit)]


@router.post("/{project_id}/archive", response_model=ProjectRead)
def archive_project(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    require_human(principal)
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            require_project_member(session, principal, project_id=project_id)
            project = ProjectRepository(session).archive(project_id)
            response = ProjectRead(
                id=project.id,
                org_id=project.org_id,
                name=project.name,
                slug=project.slug,
                description=project.description,
                git_remotes=project.git_remotes,
                default_branch=project.default_branch,
                status=project.status,
            )
            uow.commit()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return response


@router.post("/{project_id}/initialize-local")
def initialize_local_project(
    project_id: str,
    payload: InitializeLocalProjectRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    require_human(principal)
    with SqlAlchemyUnitOfWork(session) as uow:
        project = ProjectRepository(session).get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        require_project_member(session, principal, project_id=project.id)

        job_repo = InitializationJobRepository(session)
        git_remote = project.git_remotes[0] if project.git_remotes else None
        job = job_repo.create(
            org_id=project.org_id,
            project_id=project.id,
            repo_path=payload.repo_path,
            git_remote=git_remote,
        )
        job_id = job.id
        uow.commit()
    return _execute_initialization_job(
        project_id=project_id,
        job_id=job_id,
        session=session,
        keyword_index=keyword_index,
        vector_index=vector_index,
    )


@router.post("/{project_id}/initialization-jobs/{job_id}/retry")
def retry_initialization_job(
    project_id: str,
    job_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    require_human(principal)
    with SqlAlchemyUnitOfWork(session) as uow:
        project = ProjectRepository(session).get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        require_project_member(session, principal, project_id=project.id)

        job_repo = InitializationJobRepository(session)
        previous_job = job_repo.get(job_id)
        if previous_job is None or previous_job.project_id != project_id:
            raise HTTPException(status_code=404, detail="Initialization job not found")
        if previous_job.status != "failed":
            raise HTTPException(status_code=400, detail="Only failed initialization jobs can be retried")

        retry_job = job_repo.create(
            org_id=project.org_id,
            project_id=project.id,
            repo_path=previous_job.repo_path,
            git_remote=previous_job.git_remote,
        )
        retry_job_id = retry_job.id
        previous_job_id = previous_job.id
        uow.commit()
    response = _execute_initialization_job(
        project_id=project_id,
        job_id=retry_job_id,
        session=session,
        keyword_index=keyword_index,
        vector_index=vector_index,
    )
    response["retry_of_job_id"] = previous_job_id
    return response


def _execute_initialization_job(
    *,
    project_id: str,
    job_id: str,
    session: Session,
    keyword_index: FakeKeywordIndex,
    vector_index: FakeVectorIndex,
) -> dict:
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            project = ProjectRepository(session).get(project_id)
            job_repo = InitializationJobRepository(session)
            job = job_repo.get(job_id)
            if project is None or job is None or job.project_id != project_id:
                raise HTTPException(status_code=404, detail="Initialization command state not found")
            response, index_updates = _run_initialization_job(
                project=project,
                job=job,
                session=session,
                job_repo=job_repo,
            )
            uow.commit()
    except HTTPException as exc:
        _mark_initialization_job_failed(session, job_id=job_id, error=str(exc.detail))
        raise
    except Exception as exc:
        error = f"Project initialization failed: {exc}"
        _mark_initialization_job_failed(session, job_id=job_id, error=error)
        raise HTTPException(status_code=500, detail=error) from exc

    index_warnings = _index_assets_after_commit(
        index_updates,
        keyword_index=keyword_index,
        vector_index=vector_index,
        command_name="project initialization",
    )
    response["index_status"] = "pending_rebuild" if index_warnings else "indexed"
    if index_warnings:
        response["warnings"] = [*response.get("warnings", []), *index_warnings]
    return response


def _index_assets_after_commit(
    index_updates: list[tuple[str, AssetCreate]],
    *,
    keyword_index: FakeKeywordIndex,
    vector_index: FakeVectorIndex,
    command_name: str,
) -> list[str]:
    warnings = []
    for asset_id, asset in index_updates:
        for index_name, index in (("keyword", keyword_index), ("vector", vector_index)):
            try:
                index.index_asset(asset_id, asset)
            except Exception as exc:
                logger.exception("Post-commit %s index refresh failed during %s", index_name, command_name)
                warnings.append(f"{index_name} index pending_rebuild: {exc}")
    return warnings


def _mark_initialization_job_failed(session: Session, *, job_id: str, error: str) -> None:
    with SqlAlchemyUnitOfWork(session) as uow:
        job_repo = InitializationJobRepository(session)
        job = job_repo.get(job_id)
        if job is None:
            raise RuntimeError(f"Initialization job not found after rollback: {job_id}")
        job_repo.mark_failed(job, error=error)
        uow.commit()


def _run_initialization_job(
    *,
    project,
    job,
    session: Session,
    job_repo: InitializationJobRepository,
) -> tuple[dict, list[tuple[str, AssetCreate]]]:
    repo_path = Path(job.repo_path)
    if not repo_path.exists():
        if not project.git_remotes:
            error = f"Repository path does not exist and project has no Git remote to clone: {job.repo_path}"
            raise HTTPException(
                status_code=400,
                detail=error,
            )
        try:
            clone_repository(project.git_remotes[0], repo_path)
        except GitCloneError as exc:
            error = f"Git clone failed: {exc}"
            raise HTTPException(status_code=400, detail=error) from exc

    try:
        result = initialize_project_from_local_repo(org_id=project.org_id, project_id=project.id, repo_path=repo_path)
        asset_repo = AssetRepository(session)
        stored_assets = []
        index_updates = []
        for asset in result.assets:
            stored = asset_repo.upsert_by_source_uri(**asset.model_dump())
            stored_assets.append(stored)
            index_updates.append((stored.id, asset))
        asset_repo.prune_project_sources(
            project_id=project.id,
            managed_source_uris={asset.source_uri for asset in result.assets},
        )
        job_repo.mark_completed(job, asset_count=len(stored_assets), warnings=result.warnings)
    except HTTPException:
        raise
    except Exception as exc:
        error = f"Project initialization failed: {exc}"
        raise HTTPException(status_code=500, detail=error) from exc

    return (
        {
            "project_id": project.id,
            "job_id": job.id,
            "status": job.status,
            "asset_count": len(stored_assets),
            "modules": result.modules,
            "warnings": result.warnings,
        },
        index_updates,
    )


@router.get("/{project_id}/initialization-jobs")
def list_initialization_jobs(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    project = ProjectRepository(session).get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    require_project_member(session, principal, project_id=project.id)

    jobs = InitializationJobRepository(session).list_by_project(project_id)
    return [_serialize_initialization_job(job) for job in jobs]
