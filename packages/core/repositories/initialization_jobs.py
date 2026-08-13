from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.core.models import ProjectInitializationJobModel, utc_now


class InitializationJobRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        *,
        org_id: str,
        project_id: str,
        repo_path: str,
        git_remote: str | None = None,
        status: str = "running",
    ) -> ProjectInitializationJobModel:
        job = ProjectInitializationJobModel(
            org_id=org_id,
            project_id=project_id,
            repo_path=repo_path,
            git_remote=git_remote,
            status=status,
            started_at=utc_now(),
        )
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def list_by_project(self, project_id: str) -> list[ProjectInitializationJobModel]:
        statement = (
            select(ProjectInitializationJobModel)
            .where(ProjectInitializationJobModel.project_id == project_id)
            .order_by(ProjectInitializationJobModel.created_at.desc())
        )
        return list(self.session.scalars(statement).all())

    def get(self, job_id: str) -> ProjectInitializationJobModel | None:
        return self.session.get(ProjectInitializationJobModel, job_id)

    def mark_completed(
        self,
        job: ProjectInitializationJobModel,
        *,
        asset_count: int,
        warnings: list[str],
    ) -> ProjectInitializationJobModel:
        job.status = "completed"
        job.asset_count = asset_count
        job.warnings = warnings
        job.error = None
        job.completed_at = utc_now()
        self.session.commit()
        self.session.refresh(job)
        return job

    def mark_failed(self, job: ProjectInitializationJobModel, *, error: str) -> ProjectInitializationJobModel:
        job.status = "failed"
        job.error = error
        job.completed_at = utc_now()
        self.session.commit()
        self.session.refresh(job)
        return job
