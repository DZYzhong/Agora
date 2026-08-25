from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.core.models import (
    ApprovalDecisionModel,
    ContextProposalModel,
    ContextRevisionModel,
    ContextStreamModel,
    OutboxEventModel,
)


class ContextGovernanceRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_stream(self, stream_id: str) -> ContextStreamModel | None:
        return self.session.get(ContextStreamModel, stream_id)

    def get_stream_by_project_branch(self, *, project_id: str, branch: str, name: str = "default") -> ContextStreamModel | None:
        return self.session.scalar(
            select(ContextStreamModel).where(
                ContextStreamModel.project_id == project_id,
                ContextStreamModel.branch == branch,
                ContextStreamModel.name == name,
            )
        )

    def ensure_stream(
        self,
        *,
        org_id: str,
        project_id: str,
        branch: str,
        name: str = "default",
        repository_identity: dict | None = None,
    ) -> ContextStreamModel:
        stream = self.get_stream_by_project_branch(project_id=project_id, branch=branch, name=name)
        if stream is not None:
            return stream
        stream = ContextStreamModel(
            org_id=org_id,
            project_id=project_id,
            branch=branch,
            name=name,
            repository_identity=repository_identity or {},
            status="active",
        )
        self.session.add(stream)
        self.session.flush()
        self.session.refresh(stream)
        return stream

    def list_streams_by_project(self, project_id: str) -> list[ContextStreamModel]:
        return list(
            self.session.scalars(
                select(ContextStreamModel).where(ContextStreamModel.project_id == project_id).order_by(ContextStreamModel.created_at)
            ).all()
        )

    def get_head_revision_for_project(self, *, project_id: str, branch: str | None = None) -> ContextRevisionModel | None:
        statement = (
            select(ContextRevisionModel)
            .join(ContextStreamModel, ContextStreamModel.head_revision_id == ContextRevisionModel.id)
            .where(ContextStreamModel.project_id == project_id)
            .order_by(ContextRevisionModel.created_at.desc())
        )
        if branch:
            statement = statement.where(ContextStreamModel.branch == branch)
        return self.session.scalars(statement).first()

    def create_proposal(self, **kwargs) -> ContextProposalModel:
        proposal = ContextProposalModel(**kwargs)
        self.session.add(proposal)
        self.session.flush()
        self.session.refresh(proposal)
        return proposal

    def get_proposal(self, proposal_id: str) -> ContextProposalModel | None:
        return self.session.get(ContextProposalModel, proposal_id)

    def list_proposals_by_project(self, project_id: str) -> list[ContextProposalModel]:
        return list(
            self.session.scalars(
                select(ContextProposalModel)
                .where(ContextProposalModel.project_id == project_id)
                .order_by(ContextProposalModel.created_at.desc())
            ).all()
        )

    def create_revision(self, **kwargs) -> ContextRevisionModel:
        revision = ContextRevisionModel(**kwargs)
        self.session.add(revision)
        self.session.flush()
        self.session.refresh(revision)
        return revision

    def get_revision(self, revision_id: str) -> ContextRevisionModel | None:
        return self.session.get(ContextRevisionModel, revision_id)

    def create_approval_decision(self, **kwargs) -> ApprovalDecisionModel:
        decision = ApprovalDecisionModel(**kwargs)
        self.session.add(decision)
        self.session.flush()
        self.session.refresh(decision)
        return decision

    def create_outbox_event(self, **kwargs) -> OutboxEventModel:
        event = OutboxEventModel(**kwargs)
        self.session.add(event)
        self.session.flush()
        self.session.refresh(event)
        return event
