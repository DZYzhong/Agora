"""PR1B approval grants and the credential denial matrix.

Design: `docs/superpowers/specs/2026-08-28-agora-production-readiness-design.zh-CN.md`
§5.4 — Agent, CI and Personal Tokens can never approve. Approval and
high-risk HumanConfirmation require a reauthenticated Web human session or a
grant issued by one; a grant is bound to the human user, object ID, payload
digest, decision, policy version and a five-minute expiry, and is single-use.
"""

from __future__ import annotations

from datetime import timedelta
import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from packages.core.auth import Principal
from packages.core.models import ApprovalGrantModel, utc_now
from packages.core.repositories.approval_grants import ApprovalGrantRepository
from packages.core.repositories.sessions_auth import WebSessionRepository

APPROVAL_GRANT_TTL = timedelta(minutes=5)
APPROVAL_POLICY_VERSION = "pr1b-1"


def approval_payload_digest(*parts: Any) -> str:
    """Deterministic digest of the approval payload for grant binding."""
    encoded = json.dumps(
        [part for part in parts],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class ApprovalDeniedError(ValueError):
    def __init__(self, *, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def issue_approval_grant(
    session: Session,
    *,
    actor: Principal,
    org_id: str,
    object_type: str,
    object_id: str,
    payload_digest: str,
    decision: str,
    policy_version: str = APPROVAL_POLICY_VERSION,
    session_id: str | None = None,
) -> ApprovalGrantModel:
    _require_approval_principal(session, actor)
    now = utc_now()
    grant = ApprovalGrantRepository(session).create(
        org_id=org_id,
        user_id=actor.user_id,
        session_id=session_id or (actor.credential_id if actor.credential_kind == "web_session" else None),
        object_type=object_type,
        object_id=object_id,
        payload_digest=payload_digest,
        decision=decision,
        policy_version=policy_version,
        expires_at=now + APPROVAL_GRANT_TTL,
        now=now,
    )
    return grant


def consume_approval_grant(
    session: Session,
    *,
    grant_id: str,
    actor: Principal,
    object_type: str,
    object_id: str,
    payload_digest: str,
    decision: str,
) -> ApprovalGrantModel:
    repo = ApprovalGrantRepository(session)
    grant = repo.get(grant_id)
    now = utc_now()
    if grant is None or grant.user_id != actor.user_id:
        raise ApprovalDeniedError(code="APPROVAL_GRANT_INVALID", message="Approval grant is invalid")
    if grant.object_type != object_type or grant.object_id != object_id:
        raise ApprovalDeniedError(code="APPROVAL_GRANT_OBJECT_MISMATCH", message="Approval grant does not match the approval target")
    if grant.payload_digest != payload_digest:
        raise ApprovalDeniedError(code="APPROVAL_GRANT_DIGEST_MISMATCH", message="Approval grant payload digest mismatch")
    if grant.decision != decision:
        raise ApprovalDeniedError(code="APPROVAL_GRANT_DECISION_MISMATCH", message="Approval grant decision mismatch")
    if _expired(grant.expires_at, now=now):
        raise ApprovalDeniedError(code="APPROVAL_GRANT_EXPIRED", message="Approval grant has expired")
    if grant.consumed_at is not None:
        raise ApprovalDeniedError(code="APPROVAL_GRANT_USED", message="Approval grant has already been used")
    repo.consume(grant, at=now)
    return grant


def is_reauth_valid(session: Session, principal: Principal, *, now=None) -> bool:
    if principal.is_bypass:
        return True
    if principal.credential_kind != "web_session":
        return False
    record = WebSessionRepository(session).get(principal.credential_id)
    if record is None or record.reauth_expires_at is None:
        return False
    current = now or utc_now()
    return not _expired(record.reauth_expires_at, now=current)


def require_approval_capability(
    session: Session,
    *,
    principal: Principal,
    org_id: str,
    object_type: str,
    object_id: str,
    payload_digest: str,
    decision: str,
    policy_version: str = APPROVAL_POLICY_VERSION,
    grant_id: str | None = None,
) -> None:
    """Denial matrix: only reauthenticated Web human sessions or their grants approve."""
    if principal.is_bypass:
        return
    if grant_id:
        consume_approval_grant(
            session,
            grant_id=grant_id,
            actor=principal,
            object_type=object_type,
            object_id=object_id,
            payload_digest=payload_digest,
            decision=decision,
        )
        return
    if principal.credential_kind == "web_session" and is_reauth_valid(session, principal):
        return
    raise ApprovalDeniedError(
        code="APPROVAL_CREDENTIAL_REQUIRED",
        message="Approval requires a reauthenticated Web human session or a valid approval grant",
    )


def _require_approval_principal(session: Session, actor: Principal) -> None:
    if actor.is_bypass:
        return
    if actor.credential_kind == "web_session" and is_reauth_valid(session, actor):
        return
    raise ApprovalDeniedError(
        code="APPROVAL_CREDENTIAL_REQUIRED",
        message="Approval grants can only be issued by a reauthenticated Web human session",
    )


def _expired(expires_at, *, now) -> bool:
    if expires_at.tzinfo is None:
        return expires_at <= now.replace(tzinfo=None)
    return expires_at <= now
