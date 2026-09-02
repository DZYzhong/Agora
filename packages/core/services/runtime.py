from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from packages.core.models import (
    ApprovalDecisionModel,
    AssetModel,
    ContextPackModel,
    ContextProposalModel,
    ContextRevisionModel,
    ContextStreamModel,
    HumanConfirmationModel,
    IdempotencyRecordModel,
    OutboxEventModel,
    ProjectModel,
    PullRequestSignalModel,
    QualityEvidenceModel,
    RepositoryRevisionSignalModel,
    SecurityAuditEventModel,
    SessionEventModel,
    SkillModel,
    SkillRunModel,
    SkillVersionModel,
    TaskSessionModel,
    WorkArtifactModel,
    WorkflowExecutionModel,
    WorkflowStepRunModel,
    WorkflowVersionModel,
    WorkItemLinkModel,
    WorkItemModel,
    WritebackModel,
)
from packages.core.repositories.assets import AssetRepository
from packages.core.repositories.context_governance import ContextGovernanceRepository
from packages.core.repositories.integrations import IntegrationRepository
from packages.core.repositories.context_packs import ContextPackRepository
from packages.core.repositories.projects import ProjectRepository
from packages.core.repositories.quality import QualityRepository
from packages.core.repositories.security import SecurityRepository
from packages.core.repositories.sessions import TaskSessionRepository
from packages.core.repositories.skills import SkillRepository
from packages.core.repositories.work import WorkRepository, WorkSessionView
from packages.core.repositories.workflows import WorkflowRepository
from packages.core.repositories.writebacks import WritebackRepository


class CoreRuntime:
    def __init__(self, session: Session) -> None:
        self.session = session

    def find_project_by_git_remote(self, repo_remote: str) -> ProjectModel | None:
        return ProjectRepository(self.session).find_by_git_remote(repo_remote)

    def get_project(self, project_id: str) -> ProjectModel | None:
        return ProjectRepository(self.session).get(project_id)

    def list_projects(self) -> list[ProjectModel]:
        return ProjectRepository(self.session).list()

    def create_session(self, **kwargs: Any) -> TaskSessionModel:
        return TaskSessionRepository(self.session).create(**kwargs)

    def create_work_item(self, **kwargs: Any) -> WorkItemModel:
        return WorkRepository(self.session).create_work_item(**kwargs)

    def get_work_item(self, work_item_id: str) -> WorkItemModel | None:
        return WorkRepository(self.session).get_work_item(work_item_id)

    def get_work_item_by_project(self, *, project_id: str, work_item_id: str) -> WorkItemModel | None:
        return WorkRepository(self.session).get_work_item_by_project(project_id=project_id, work_item_id=work_item_id)

    def get_work_item_by_external_key(self, *, project_id: str, external_key: str) -> WorkItemModel | None:
        return WorkRepository(self.session).get_work_item_by_external_key(project_id=project_id, external_key=external_key)

    def find_work_items_by_title(self, *, project_id: str, title: str) -> list[WorkItemModel]:
        return WorkRepository(self.session).find_work_items_by_title(project_id=project_id, title=title)

    def upsert_work_item_link(self, **kwargs: Any) -> WorkItemLinkModel:
        return WorkRepository(self.session).upsert_work_item_link(**kwargs)

    def list_work_item_links_by_work_item_ids(self, work_item_ids: list[str]) -> list[WorkItemLinkModel]:
        return WorkRepository(self.session).list_work_item_links_by_work_item_ids(work_item_ids)

    def list_work_items_by_project(self, project_id: str) -> list[tuple[WorkItemModel, int]]:
        return WorkRepository(self.session).list_work_items_by_project(project_id)

    def list_work_sessions_by_work_item(self, work_item_id: str) -> list[WorkSessionView]:
        return WorkRepository(self.session).list_work_sessions_by_work_item(work_item_id)

    def create_work_session(self, **kwargs: Any) -> WorkSessionView:
        return WorkRepository(self.session).create_work_session(**kwargs)

    def ensure_standard_workflow_version(self, *, org_id: str, project_id: str | None = None) -> WorkflowVersionModel:
        return WorkflowRepository(self.session).ensure_standard_workflow_version(org_id=org_id, project_id=project_id)

    def ensure_workflow_execution_for_work_item(self, *, work_item: WorkItemModel, workflow_version: WorkflowVersionModel) -> WorkflowExecutionModel:
        return WorkflowRepository(self.session).ensure_execution_for_work_item(
            work_item=work_item,
            workflow_version=workflow_version,
        )

    def get_workflow_execution_by_work_item(self, work_item_id: str) -> WorkflowExecutionModel | None:
        return WorkflowRepository(self.session).get_execution_by_work_item(work_item_id)

    def list_workflow_step_runs(self, workflow_execution_id: str) -> list[WorkflowStepRunModel]:
        return WorkflowRepository(self.session).list_step_runs(workflow_execution_id)

    def list_work_artifacts_by_execution(self, workflow_execution_id: str) -> list[WorkArtifactModel]:
        return WorkflowRepository(self.session).list_work_artifacts_by_execution(workflow_execution_id)

    def list_work_artifacts_by_ids(self, artifact_ids: list[str]) -> list[WorkArtifactModel]:
        return WorkflowRepository(self.session).list_work_artifacts_by_ids(artifact_ids)

    def list_work_artifacts_by_project(self, project_id: str) -> list[WorkArtifactModel]:
        return WorkflowRepository(self.session).list_work_artifacts_by_project(project_id)

    def list_human_confirmations_by_execution(self, workflow_execution_id: str) -> list[HumanConfirmationModel]:
        return WorkflowRepository(self.session).list_human_confirmations_by_execution(workflow_execution_id)

    def complete_current_workflow_step(
        self,
        *,
        workflow_execution_id: str,
        step_key: str,
    ) -> tuple[WorkflowExecutionModel, WorkflowStepRunModel, WorkflowStepRunModel | None]:
        return WorkflowRepository(self.session).complete_current_step(
            workflow_execution_id=workflow_execution_id,
            step_key=step_key,
        )

    def create_work_artifact(self, **kwargs: Any) -> WorkArtifactModel:
        return WorkflowRepository(self.session).create_work_artifact(**kwargs)

    def create_human_confirmation(self, **kwargs: Any) -> HumanConfirmationModel:
        return WorkflowRepository(self.session).create_human_confirmation(**kwargs)

    def create_quality_evidence(self, **kwargs: Any) -> QualityEvidenceModel:
        return QualityRepository(self.session).create_evidence(**kwargs)

    def list_quality_evidence_by_work_item(self, work_item_id: str) -> list[QualityEvidenceModel]:
        return QualityRepository(self.session).list_by_work_item(work_item_id)

    def list_quality_evidence_by_project(self, project_id: str) -> list[QualityEvidenceModel]:
        return QualityRepository(self.session).list_by_project(project_id)

    def create_security_audit_event(self, **kwargs: Any) -> SecurityAuditEventModel:
        return SecurityRepository(self.session).create_audit_event(**kwargs)

    def list_security_audit_events_by_project(self, project_id: str, *, limit: int = 100) -> list[SecurityAuditEventModel]:
        return SecurityRepository(self.session).list_by_project(project_id, limit=limit)

    def create_repository_revision_signal(self, **kwargs: Any) -> RepositoryRevisionSignalModel:
        return IntegrationRepository(self.session).create_repository_revision_signal(**kwargs)

    def create_pull_request_signal(self, **kwargs: Any) -> PullRequestSignalModel:
        return IntegrationRepository(self.session).create_pull_request_signal(**kwargs)

    def get_session(self, session_id: str) -> WorkSessionView | TaskSessionModel | None:
        work_session = WorkRepository(self.session).get_work_session(session_id)
        return work_session or TaskSessionRepository(self.session).get(session_id)

    def list_sessions_by_project(
        self,
        project_id: str,
        *,
        intent: str | None = None,
        status: str | None = None,
    ) -> list[WorkSessionView | TaskSessionModel]:
        work_sessions = WorkRepository(self.session).list_work_sessions_by_project(project_id, intent=intent, status=status)
        legacy_sessions = TaskSessionRepository(self.session).list_by_project(project_id, intent=intent, status=status)
        work_session_ids = {session.id for session in work_sessions}
        return [*work_sessions, *[session for session in legacy_sessions if session.id not in work_session_ids]]

    def get_session_by_project(self, *, project_id: str, session_id: str) -> WorkSessionView | TaskSessionModel | None:
        work_session = WorkRepository(self.session).get_work_session_by_project(project_id=project_id, session_id=session_id)
        return work_session or TaskSessionRepository(self.session).get_by_project(project_id=project_id, session_id=session_id)

    def get_idempotency_record(self, **kwargs: Any) -> IdempotencyRecordModel | None:
        return WorkRepository(self.session).get_idempotency_record(**kwargs)

    def create_idempotency_record(self, **kwargs: Any) -> IdempotencyRecordModel:
        return WorkRepository(self.session).create_idempotency_record(**kwargs)

    def complete_idempotency_record(self, *args: Any, **kwargs: Any) -> IdempotencyRecordModel:
        return WorkRepository(self.session).complete_idempotency_record(*args, **kwargs)

    def list_session_events(self, session_id: str) -> list[SessionEventModel]:
        return TaskSessionRepository(self.session).list_events(session_id)

    def record_event(self, **kwargs: Any) -> SessionEventModel:
        return TaskSessionRepository(self.session).record_event(**kwargs)

    def create_context_pack(self, **kwargs: Any) -> ContextPackModel:
        return ContextPackRepository(self.session).create(**kwargs)

    def list_context_packs_by_ids(self, context_pack_ids: list[str]) -> list[ContextPackModel]:
        return ContextPackRepository(self.session).list_by_ids(context_pack_ids)

    def ensure_context_stream(self, **kwargs: Any) -> ContextStreamModel:
        return ContextGovernanceRepository(self.session).ensure_stream(**kwargs)

    def get_context_stream(self, stream_id: str) -> ContextStreamModel | None:
        return ContextGovernanceRepository(self.session).get_stream(stream_id)

    def list_context_streams_by_project(self, project_id: str) -> list[ContextStreamModel]:
        return ContextGovernanceRepository(self.session).list_streams_by_project(project_id)

    def get_head_context_revision_for_project(self, *, project_id: str, branch: str | None = None) -> ContextRevisionModel | None:
        return ContextGovernanceRepository(self.session).get_head_revision_for_project(project_id=project_id, branch=branch)

    def create_context_proposal(self, **kwargs: Any) -> ContextProposalModel:
        return ContextGovernanceRepository(self.session).create_proposal(**kwargs)

    def get_context_proposal(self, proposal_id: str) -> ContextProposalModel | None:
        return ContextGovernanceRepository(self.session).get_proposal(proposal_id)

    def list_context_proposals_by_project(self, project_id: str) -> list[ContextProposalModel]:
        return ContextGovernanceRepository(self.session).list_proposals_by_project(project_id)

    def create_context_revision(self, **kwargs: Any) -> ContextRevisionModel:
        return ContextGovernanceRepository(self.session).create_revision(**kwargs)

    def get_context_revision(self, revision_id: str) -> ContextRevisionModel | None:
        return ContextGovernanceRepository(self.session).get_revision(revision_id)

    def create_approval_decision(self, **kwargs: Any) -> ApprovalDecisionModel:
        return ContextGovernanceRepository(self.session).create_approval_decision(**kwargs)

    def create_outbox_event(self, **kwargs: Any) -> OutboxEventModel:
        return ContextGovernanceRepository(self.session).create_outbox_event(**kwargs)

    def create_skill(self, **kwargs: Any) -> SkillModel:
        return SkillRepository(self.session).create(**kwargs)

    def get_skill(self, skill_id: str) -> SkillModel | None:
        return SkillRepository(self.session).get(skill_id)

    def get_skill_by_slug(self, skill_slug: str, *, project_id: str | None = None) -> SkillModel | None:
        return SkillRepository(self.session).get_by_slug(skill_slug, project_id=project_id)

    def list_skills_by_project(self, project_id: str) -> list[SkillModel]:
        return SkillRepository(self.session).list_by_project(project_id)

    def update_skill(self, skill_id: str, **kwargs: Any) -> SkillModel:
        return SkillRepository(self.session).update(skill_id, **kwargs)

    def ensure_approved_skill_version(self, skill_id: str, *, approved_by_user_id: str | None = None) -> SkillVersionModel:
        return SkillRepository(self.session).ensure_approved_version(skill_id, approved_by_user_id=approved_by_user_id)

    def get_current_skill_version(self, skill_id: str) -> SkillVersionModel | None:
        return SkillRepository(self.session).get_current_version(skill_id)

    def list_applicable_skill_versions(self, *, project_id: str, query: str, limit: int = 5) -> list[SkillVersionModel]:
        return SkillRepository(self.session).list_applicable_approved_versions(
            project_id=project_id,
            query=query,
            limit=limit,
        )

    def create_skill_run(self, **kwargs: Any) -> SkillRunModel:
        return SkillRepository(self.session).create_run(**kwargs)

    def pin_work_session_skill_version(self, *, session_id: str, skill_version_id: str) -> None:
        return SkillRepository(self.session).pin_work_session_skill_version(
            session_id=session_id,
            skill_version_id=skill_version_id,
        )

    def list_skill_runs_by_project(self, project_id: str) -> list[SkillRunModel]:
        return SkillRepository(self.session).list_runs_by_project(project_id)

    def list_skill_runs_by_session(self, *, project_id: str, session_id: str) -> list[SkillRunModel]:
        return SkillRepository(self.session).list_runs_by_session(project_id=project_id, session_id=session_id)

    def create_asset(self, **kwargs: Any) -> AssetModel:
        return AssetRepository(self.session).create(**kwargs)

    def get_asset(self, asset_id: str) -> AssetModel | None:
        return AssetRepository(self.session).get(asset_id)

    def create_writeback(self, **kwargs: Any) -> WritebackModel:
        return WritebackRepository(self.session).create(**kwargs)

    def get_writeback(self, writeback_id: str) -> WritebackModel | None:
        return WritebackRepository(self.session).get(writeback_id)

    def list_accepted_writebacks_by_type(self, *, project_id: str, type: str) -> list[WritebackModel]:
        return WritebackRepository(self.session).list_by_project_type_status(project_id=project_id, type=type, status="accepted")

    def list_writebacks_by_ids(self, writeback_ids: list[str]) -> list[WritebackModel]:
        return WritebackRepository(self.session).list_by_ids(writeback_ids)

    def list_writebacks_by_session(self, *, project_id: str, session_id: str) -> list[WritebackModel]:
        return WritebackRepository(self.session).list_by_session(project_id=project_id, session_id=session_id)

    def accept_writeback(self, writeback_id: str, *, accepted_asset_id: str | None = None) -> WritebackModel:
        return WritebackRepository(self.session).accept(writeback_id, accepted_asset_id=accepted_asset_id)
