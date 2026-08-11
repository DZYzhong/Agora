from sqlalchemy.orm import Session

from packages.core.repositories.assets import AssetRepository
from packages.core.repositories.projects import ProjectRepository
from packages.core.repositories.sessions import TaskSessionRepository
from packages.core.repositories.writebacks import WritebackRepository


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

    def create_asset(self, **kwargs):
        return AssetRepository(self.session).create(**kwargs)

    def get_asset(self, asset_id: str):
        return AssetRepository(self.session).get(asset_id)

    def create_writeback(self, **kwargs):
        return WritebackRepository(self.session).create(**kwargs)

    def get_writeback(self, writeback_id: str):
        return WritebackRepository(self.session).get(writeback_id)

    def accept_writeback(self, writeback_id: str, *, accepted_asset_id: str | None = None):
        return WritebackRepository(self.session).accept(writeback_id, accepted_asset_id=accepted_asset_id)
