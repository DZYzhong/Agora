from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.core.models import ProjectModel


class ProjectRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        *,
        org_id: str,
        name: str,
        slug: str,
        description: str | None = None,
        git_remotes: list[str] | None = None,
        default_branch: str | None = None,
    ) -> ProjectModel:
        project = ProjectModel(
            org_id=org_id,
            name=name,
            slug=slug,
            description=description,
            git_remotes=git_remotes or [],
            default_branch=default_branch,
        )
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        return project

    def get(self, project_id: str) -> ProjectModel | None:
        return self.session.get(ProjectModel, project_id)

    def list(self) -> list[ProjectModel]:
        return list(self.session.scalars(select(ProjectModel)).all())

    def find_by_git_remote(self, repo_remote: str) -> ProjectModel | None:
        for project in self.list():
            if repo_remote in (project.git_remotes or []):
                return project
        return None
