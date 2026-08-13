from sqlalchemy.orm import Session

from packages.core.repositories.assets import AssetRepository
from packages.core.repositories.context_packs import ContextPackRepository
from packages.core.repositories.projects import ProjectRepository
from packages.core.repositories.sessions import TaskSessionRepository
from packages.core.repositories.skills import SkillRepository
from packages.core.repositories.writebacks import WritebackRepository


class CoreRuntime:
    def __init__(self, session: Session):
        self.session = session

    def find_project_by_git_remote(self, repo_remote: str):
        return ProjectRepository(self.session).find_by_git_remote(repo_remote)

    def get_project(self, project_id: str):
        return ProjectRepository(self.session).get(project_id)

    def list_projects(self):
        return ProjectRepository(self.session).list()

    def create_session(self, **kwargs):
        return TaskSessionRepository(self.session).create(**kwargs)

    def get_session(self, session_id: str):
        return TaskSessionRepository(self.session).get(session_id)

    def list_sessions_by_project(self, project_id: str):
        return TaskSessionRepository(self.session).list_by_project(project_id)

    def list_session_events(self, session_id: str):
        return TaskSessionRepository(self.session).list_events(session_id)

    def record_event(self, **kwargs):
        return TaskSessionRepository(self.session).record_event(**kwargs)

    def create_context_pack(self, **kwargs):
        return ContextPackRepository(self.session).create(**kwargs)

    def list_context_packs_by_ids(self, context_pack_ids: list[str]):
        return ContextPackRepository(self.session).list_by_ids(context_pack_ids)

    def create_skill(self, **kwargs):
        return SkillRepository(self.session).create(**kwargs)

    def get_skill(self, skill_id: str):
        return SkillRepository(self.session).get(skill_id)

    def get_skill_by_slug(self, skill_slug: str, *, project_id: str | None = None):
        return SkillRepository(self.session).get_by_slug(skill_slug, project_id=project_id)

    def list_skills_by_project(self, project_id: str):
        return SkillRepository(self.session).list_by_project(project_id)

    def update_skill(self, skill_id: str, **kwargs):
        return SkillRepository(self.session).update(skill_id, **kwargs)

    def create_skill_run(self, **kwargs):
        return SkillRepository(self.session).create_run(**kwargs)

    def list_skill_runs_by_project(self, project_id: str):
        return SkillRepository(self.session).list_runs_by_project(project_id)

    def create_asset(self, **kwargs):
        return AssetRepository(self.session).create(**kwargs)

    def get_asset(self, asset_id: str):
        return AssetRepository(self.session).get(asset_id)

    def create_writeback(self, **kwargs):
        return WritebackRepository(self.session).create(**kwargs)

    def get_writeback(self, writeback_id: str):
        return WritebackRepository(self.session).get(writeback_id)

    def list_accepted_writebacks_by_type(self, *, project_id: str, type: str):
        return WritebackRepository(self.session).list_by_project_type_status(project_id=project_id, type=type, status="accepted")

    def accept_writeback(self, writeback_id: str, *, accepted_asset_id: str | None = None):
        return WritebackRepository(self.session).accept(writeback_id, accepted_asset_id=accepted_asset_id)
