from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db_session
from packages.core.repositories.projects import ProjectRepository
from packages.domain.schemas import ProjectCreate, ProjectRead

router = APIRouter(prefix="/projects", tags=["projects"])


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
