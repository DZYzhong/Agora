from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.core.models import SecurityAuditEventModel


class SecurityRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_audit_event(
        self,
        *,
        org_id: str,
        project_id: str,
        actor_user_id: str,
        actor_credential_id: str | None,
        actor_credential_kind: str,
        action: str,
        target_type: str,
        target_id: str,
        decision: str,
        reason: str | None = None,
        metadata: dict | None = None,
    ) -> SecurityAuditEventModel:
        event = SecurityAuditEventModel(
            org_id=org_id,
            project_id=project_id,
            actor_user_id=actor_user_id,
            actor_credential_id=actor_credential_id,
            actor_credential_kind=actor_credential_kind,
            action=action,
            target_type=target_type,
            target_id=target_id,
            decision=decision,
            reason=reason,
            event_metadata=metadata or {},
        )
        self.session.add(event)
        self.session.flush()
        self.session.refresh(event)
        return event

    def list_by_project(self, project_id: str, *, limit: int = 100) -> list[SecurityAuditEventModel]:
        statement = (
            select(SecurityAuditEventModel)
            .where(SecurityAuditEventModel.project_id == project_id)
            .order_by(SecurityAuditEventModel.created_at.desc(), SecurityAuditEventModel.id.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement).all())

    def list_by_org(self, org_id: str, *, limit: int = 200) -> list[SecurityAuditEventModel]:
        statement = (
            select(SecurityAuditEventModel)
            .where(SecurityAuditEventModel.org_id == org_id)
            .order_by(SecurityAuditEventModel.created_at.desc(), SecurityAuditEventModel.id.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement).all())
