from sqlalchemy.orm import Session

from packages.core.repositories.assets import AssetRepository
from packages.core.repositories.context_governance import ContextGovernanceRepository
from packages.core.repositories.context_packs import ContextPackRepository
from packages.core.repositories.projects import ProjectRepository
from packages.core.repositories.sessions import TaskSessionRepository
from packages.core.repositories.skills import SkillRepository
from packages.core.repositories.work import WorkRepository
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

    def create_work_item(self, **kwargs):
        return WorkRepository(self.session).create_work_item(**kwargs)

    def get_work_item(self, work_item_id: str):
        return WorkRepository(self.session).get_work_item(work_item_id)

    def get_work_item_by_project(self, *, project_id: str, work_item_id: str):
        return WorkRepository(self.session).get_work_item_by_project(project_id=project_id, work_item_id=work_item_id)

    def get_work_item_by_external_key(self, *, project_id: str, external_key: str):
        return WorkRepository(self.session).get_work_item_by_external_key(project_id=project_id, external_key=external_key)

    def find_work_items_by_title(self, *, project_id: str, title: str):
        return WorkRepository(self.session).find_work_items_by_title(project_id=project_id, title=title)

    def list_work_items_by_project(self, project_id: str):
        return WorkRepository(self.session).list_work_items_by_project(project_id)

    def list_work_sessions_by_work_item(self, work_item_id: str):
        return WorkRepository(self.session).list_work_sessions_by_work_item(work_item_id)

    def create_work_session(self, **kwargs):
        return WorkRepository(self.session).create_work_session(**kwargs)

    def get_session(self, session_id: str):
        work_session = WorkRepository(self.session).get_work_session(session_id)
        return work_session or TaskSessionRepository(self.session).get(session_id)

    def list_sessions_by_project(self, project_id: str, *, intent: str | None = None, status: str | None = None):
        work_sessions = WorkRepository(self.session).list_work_sessions_by_project(project_id, intent=intent, status=status)
        legacy_sessions = TaskSessionRepository(self.session).list_by_project(project_id, intent=intent, status=status)
        work_session_ids = {session.id for session in work_sessions}
        return [*work_sessions, *[session for session in legacy_sessions if session.id not in work_session_ids]]

    def get_session_by_project(self, *, project_id: str, session_id: str):
        work_session = WorkRepository(self.session).get_work_session_by_project(project_id=project_id, session_id=session_id)
        return work_session or TaskSessionRepository(self.session).get_by_project(project_id=project_id, session_id=session_id)

    def get_idempotency_record(self, **kwargs):
        return WorkRepository(self.session).get_idempotency_record(**kwargs)

    def create_idempotency_record(self, **kwargs):
        return WorkRepository(self.session).create_idempotency_record(**kwargs)

    def complete_idempotency_record(self, *args, **kwargs):
        return WorkRepository(self.session).complete_idempotency_record(*args, **kwargs)

    def list_session_events(self, session_id: str):
        return TaskSessionRepository(self.session).list_events(session_id)

    def record_event(self, **kwargs):
        return TaskSessionRepository(self.session).record_event(**kwargs)

    def create_context_pack(self, **kwargs):
        return ContextPackRepository(self.session).create(**kwargs)

    def list_context_packs_by_ids(self, context_pack_ids: list[str]):
        return ContextPackRepository(self.session).list_by_ids(context_pack_ids)

    def ensure_context_stream(self, **kwargs):
        return ContextGovernanceRepository(self.session).ensure_stream(**kwargs)

    def get_context_stream(self, stream_id: str):
        return ContextGovernanceRepository(self.session).get_stream(stream_id)

    def list_context_streams_by_project(self, project_id: str):
        return ContextGovernanceRepository(self.session).list_streams_by_project(project_id)

    def get_head_context_revision_for_project(self, *, project_id: str, branch: str | None = None):
        return ContextGovernanceRepository(self.session).get_head_revision_for_project(project_id=project_id, branch=branch)

    def create_context_proposal(self, **kwargs):
        return ContextGovernanceRepository(self.session).create_proposal(**kwargs)

    def get_context_proposal(self, proposal_id: str):
        return ContextGovernanceRepository(self.session).get_proposal(proposal_id)

    def list_context_proposals_by_project(self, project_id: str):
        return ContextGovernanceRepository(self.session).list_proposals_by_project(project_id)

    def create_context_revision(self, **kwargs):
        return ContextGovernanceRepository(self.session).create_revision(**kwargs)

    def create_approval_decision(self, **kwargs):
        return ContextGovernanceRepository(self.session).create_approval_decision(**kwargs)

    def create_outbox_event(self, **kwargs):
        return ContextGovernanceRepository(self.session).create_outbox_event(**kwargs)

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

    def list_skill_runs_by_session(self, *, project_id: str, session_id: str):
        return SkillRepository(self.session).list_runs_by_session(project_id=project_id, session_id=session_id)

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

    def list_writebacks_by_ids(self, writeback_ids: list[str]):
        return WritebackRepository(self.session).list_by_ids(writeback_ids)

    def list_writebacks_by_session(self, *, project_id: str, session_id: str):
        return WritebackRepository(self.session).list_by_session(project_id=project_id, session_id=session_id)

    def accept_writeback(self, writeback_id: str, *, accepted_asset_id: str | None = None):
        return WritebackRepository(self.session).accept(writeback_id, accepted_asset_id=accepted_asset_id)
