from datetime import datetime, timezone

from sqlalchemy import func, select, text

from packages.core.models import (
    ApprovalDecisionModel,
    AssetModel,
    ContextProposalModel,
    ContextRevisionModel,
    ContextStreamModel,
    ProjectModel,
    PullRequestSignalModel,
    QualityEvidenceModel,
    RepositoryRevisionSignalModel,
    SecurityAuditEventModel,
    SkillModel,
    SkillRunModel,
    SkillVersionModel,
    WorkItemModel,
)


def build_project_summary(session, project: ProjectModel) -> dict:
    revision = session.scalar(text("SELECT version_num FROM alembic_version"))
    return {
        "format": "agora-project-summary/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_revision": revision,
        "project": {
            "id": project.id,
            "org_id": project.org_id,
            "slug": project.slug,
            "name": project.name,
            "status": project.status,
            "git_remotes": project.git_remotes,
            "default_branch": project.default_branch,
        },
        "assets": {
            "total": _count_table(session, AssetModel, project.id),
            "by_type": _count_by(session, AssetModel, AssetModel.type, project.id),
            "by_source": _count_by(session, AssetModel, AssetModel.source, project.id),
        },
        "work_items": {
            "total": _count_table(session, WorkItemModel, project.id),
            "by_status": _count_by(session, WorkItemModel, WorkItemModel.status, project.id),
            "by_stage": _count_by(session, WorkItemModel, WorkItemModel.stage, project.id),
            "by_source": _count_by(session, WorkItemModel, WorkItemModel.source, project.id),
        },
        "context": {
            "streams": _count_table(session, ContextStreamModel, project.id),
            "revisions": _count_table(session, ContextRevisionModel, project.id),
            "proposals_by_status": _count_by(session, ContextProposalModel, ContextProposalModel.status, project.id),
        },
        "quality": {
            "evidence_by_status": _count_by(session, QualityEvidenceModel, QualityEvidenceModel.status, project.id),
            "evidence_by_type": _count_by(
                session,
                QualityEvidenceModel,
                QualityEvidenceModel.evidence_type,
                project.id,
            ),
        },
        "skills": {
            "skills_by_status": _count_by(session, SkillModel, SkillModel.status, project.id),
            "versions_by_status": _count_by(session, SkillVersionModel, SkillVersionModel.status, project.id),
            "runs_by_status": _count_by(session, SkillRunModel, SkillRunModel.status, project.id),
        },
        "approvals": {
            "decisions": _count_by(session, ApprovalDecisionModel, ApprovalDecisionModel.decision, project.id),
        },
        "security": {
            "decisions": _count_by(session, SecurityAuditEventModel, SecurityAuditEventModel.decision, project.id),
            "actions": _count_by(session, SecurityAuditEventModel, SecurityAuditEventModel.action, project.id),
        },
        "repository_signals": {
            "by_status": _count_by(
                session,
                RepositoryRevisionSignalModel,
                RepositoryRevisionSignalModel.status,
                project.id,
            ),
            "by_type": _count_by(
                session,
                RepositoryRevisionSignalModel,
                RepositoryRevisionSignalModel.signal_type,
                project.id,
            ),
        },
        "pull_request_signals": {
            "by_status": _count_by(session, PullRequestSignalModel, PullRequestSignalModel.status, project.id),
            "by_action": _count_by(session, PullRequestSignalModel, PullRequestSignalModel.action, project.id),
        },
    }


def _count_table(session, model, project_id: str) -> int:
    return int(session.scalar(select(func.count()).select_from(model).where(model.project_id == project_id)) or 0)


def _count_by(session, model, column, project_id: str) -> dict[str, int]:
    rows = session.execute(
        select(column, func.count()).where(model.project_id == project_id).group_by(column).order_by(column)
    ).all()
    return {str(key): int(count) for key, count in rows}
