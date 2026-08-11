from sqlalchemy.orm import Session

from packages.core.repositories.projects import ProjectRepository
from packages.core.repositories.sessions import TaskSessionRepository


class CoreRuntime:
    def __init__(self, session: Session):
        self.session = session

    def find_project_by_git_remote(self, repo_remote: str):
        return ProjectRepository(self.session).find_by_git_remote(repo_remote)

    def create_session(self, **kwargs):
        return TaskSessionRepository(self.session).create(**kwargs)

    def get_session(self, session_id: str):
        return TaskSessionRepository(self.session).get(session_id)

    def record_event(self, **kwargs):
        return TaskSessionRepository(self.session).record_event(**kwargs)
