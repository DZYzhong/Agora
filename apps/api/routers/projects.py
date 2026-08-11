from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db_session, get_keyword_index, get_vector_index
from apps.workers.workflows.initialize_project import initialize_project_from_local_repo
from packages.core.repositories.assets import AssetRepository
from packages.core.repositories.projects import ProjectRepository
from packages.domain.schemas import ProjectCreate, ProjectRead
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex

router = APIRouter(prefix="/projects", tags=["projects"])


class InitializeLocalProjectRequest(BaseModel):
    repo_path: str


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, session: Session = Depends(get_db_session)):
    project = ProjectRepository(session).create(**payload.model_dump())
    return ProjectRead(
        id=project.id,
        org_id=project.org_id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        git_remotes=project.git_remotes,
        default_branch=project.default_branch,
    )


@router.get("", response_model=list[ProjectRead])
def list_projects(session: Session = Depends(get_db_session)):
    projects = ProjectRepository(session).list()
    return [
        ProjectRead(
            id=project.id,
            org_id=project.org_id,
            name=project.name,
            slug=project.slug,
            description=project.description,
            git_remotes=project.git_remotes,
            default_branch=project.default_branch,
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
    )


@router.post("/{project_id}/initialize-local")
def initialize_local_project(
    project_id: str,
    payload: InitializeLocalProjectRequest,
    session: Session = Depends(get_db_session),
    keyword_index: FakeKeywordIndex = Depends(get_keyword_index),
    vector_index: FakeVectorIndex = Depends(get_vector_index),
):
    project = ProjectRepository(session).get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    repo_path = Path(payload.repo_path)
    if not repo_path.exists():
        raise HTTPException(status_code=400, detail=f"Repository path does not exist: {payload.repo_path}")

    result = initialize_project_from_local_repo(org_id=project.org_id, project_id=project.id, repo_path=repo_path)
    asset_repo = AssetRepository(session)
    stored_assets = []
    for asset in result.assets:
        stored = asset_repo.create(**asset.model_dump())
        keyword_index.index_asset(stored.id, asset)
        vector_index.index_asset(stored.id, asset)
        stored_assets.append(stored)

    return {
        "project_id": project.id,
        "asset_count": len(stored_assets),
        "modules": result.modules,
        "warnings": result.warnings,
    }
