from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db_session, get_keyword_index, get_vector_index
from apps.workers.workflows.initialize_project import initialize_project_from_local_repo
from packages.core.repositories.assets import AssetRepository
from packages.core.repositories.initialization_jobs import InitializationJobRepository
from packages.core.repositories.projects import ProjectRepository
from packages.core.services.runtime import CoreRuntime
from packages.core.services.skills import ensure_builtin_skills
from packages.core.uow import SqlAlchemyUnitOfWork
from packages.domain.schemas import AssetCreate, ProjectCreate, ProjectRead
from packages.integrations.git.clone import GitCloneError, clone_repository
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex

router = APIRouter(prefix="/projects", tags=["projects"])


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


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, session: Session = Depends(get_db_session)):
    with SqlAlchemyUnitOfWork(session) as uow:
        project = ProjectRepository(session).create(**payload.model_dump())
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
def list_projects(include_archived: bool = Query(default=False), session: Session = Depends(get_db_session)):
    projects = ProjectRepository(session).list(include_archived=include_archived)
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
def get_project(project_id: str, session: Session = Depends(get_db_session)):
    project = ProjectRepository(session).get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
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


@router.post("/{project_id}/archive", response_model=ProjectRead)
def archive_project(project_id: str, session: Session = Depends(get_db_session)):
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
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
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    with SqlAlchemyUnitOfWork(session) as uow:
        project = ProjectRepository(session).get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

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
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    with SqlAlchemyUnitOfWork(session) as uow:
        project = ProjectRepository(session).get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

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

    for asset_id, asset in index_updates:
        keyword_index.index_asset(asset_id, asset)
        vector_index.index_asset(asset_id, asset)
    return response


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
def list_initialization_jobs(project_id: str, session: Session = Depends(get_db_session)):
    project = ProjectRepository(session).get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    jobs = InitializationJobRepository(session).list_by_project(project_id)
    return [_serialize_initialization_job(job) for job in jobs]
