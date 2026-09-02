"""Web session persistence for PR1B human sessions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.core.models import WebSessionModel


class WebSessionRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        *,
        user_id: str,
        org_id: str,
        token_hash: str,
        csrf_secret_hash: str,
        expires_at: datetime,
        idle_expires_at: datetime,
        now: datetime,
    ) -> WebSessionModel:
        record = WebSessionModel(
            user_id=user_id,
            org_id=org_id,
            token_hash=token_hash,
            csrf_secret_hash=csrf_secret_hash,
            created_at=now,
            last_used_at=now,
            expires_at=expires_at,
            idle_expires_at=idle_expires_at,
        )
        self.session.add(record)
        self.session.flush()
        self.session.refresh(record)
        return record

    def get_active_by_token_hash(self, token_hash: str, *, now: datetime) -> WebSessionModel | None:
        statement = select(WebSessionModel).where(
            WebSessionModel.token_hash == token_hash,
            WebSessionModel.revoked_at.is_(None),
        )
        record = self.session.scalars(statement).first()
        if record is None:
            return None
        if _expired(record.expires_at, now=now) or _expired(record.idle_expires_at, now=now):
            record.revoked_at = now
            self.session.flush()
            return None
        return record

    def touch(self, record: WebSessionModel, *, now: datetime, idle_expires_at: datetime) -> None:
        record.last_used_at = now
        record.idle_expires_at = idle_expires_at
        self.session.flush()

    def revoke(self, record: WebSessionModel, *, at: datetime) -> None:
        record.revoked_at = at
        self.session.flush()

    def revoke_user_sessions(self, user_id: str, *, at: datetime) -> int:
        statement = select(WebSessionModel).where(
            WebSessionModel.user_id == user_id,
            WebSessionModel.revoked_at.is_(None),
        )
        records = list(self.session.scalars(statement).all())
        for record in records:
            record.revoked_at = at
        self.session.flush()
        return len(records)

    def mark_reauthenticated(self, record: WebSessionModel, *, reauth_expires_at: datetime) -> None:
        record.reauth_expires_at = reauth_expires_at
        self.session.flush()

    def get(self, session_id: str) -> WebSessionModel | None:
        return self.session.get(WebSessionModel, session_id)


def _expired(expires_at: datetime, *, now: datetime) -> bool:
    if expires_at.tzinfo is None:
        return expires_at <= now.replace(tzinfo=None)
    return expires_at <= now
