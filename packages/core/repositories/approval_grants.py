"""Approval grant persistence for PR1B."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.core.models import ApprovalGrantModel


class ApprovalGrantRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        *,
        org_id: str,
        user_id: str,
        session_id: str | None,
        object_type: str,
        object_id: str,
        payload_digest: str,
        decision: str,
        policy_version: str,
        expires_at: datetime,
        now: datetime,
    ) -> ApprovalGrantModel:
        grant = ApprovalGrantModel(
            org_id=org_id,
            user_id=user_id,
            session_id=session_id,
            object_type=object_type,
            object_id=object_id,
            payload_digest=payload_digest,
            decision=decision,
            policy_version=policy_version,
            expires_at=expires_at,
            created_at=now,
        )
        self.session.add(grant)
        self.session.flush()
        self.session.refresh(grant)
        return grant

    def get(self, grant_id: str) -> ApprovalGrantModel | None:
        return self.session.get(ApprovalGrantModel, grant_id)

    def consume(self, grant: ApprovalGrantModel, *, at: datetime) -> None:
        grant.consumed_at = at
        self.session.flush()

    def list_by_user(self, user_id: str, *, limit: int = 50) -> list[ApprovalGrantModel]:
        statement = (
            select(ApprovalGrantModel)
            .where(ApprovalGrantModel.user_id == user_id)
            .order_by(ApprovalGrantModel.created_at.desc(), ApprovalGrantModel.id.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement).all())
