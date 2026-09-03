"""PR3 B2: API token lifecycle (issue / list / rotate) domain service.

Non-committing: every mutation route owns an explicit SqlAlchemyUnitOfWork.
Tokens are shown in plaintext exactly once at issue/rotate time; only the
SHA-256 hash is stored.
"""

from datetime import datetime, timezone
import secrets
from typing import Any

from sqlalchemy.orm import Session

from packages.core.auth import hash_token, token_diagnostic_prefix
from packages.core.auth_admin import ADMIN_ROLES
from packages.core.models import CredentialModel, UserModel, utc_now
from packages.core.repositories.identities import IdentityRepository
from packages.core.repositories.security import SecurityRepository

# Bearer credential kinds that can be issued to humans/tools.
API_CREDENTIAL_KINDS = ("human", "agent", "ci")


class CredentialError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _audit(
    session: Session,
    *,
    actor,
    org_id: str,
    action: str,
    target_type: str,
    target_id: str,
    reason: str,
) -> None:
    SecurityRepository(session).create_audit_event(
        org_id=org_id,
        project_id=None,
        actor_user_id=actor.user_id,
        actor_credential_id=actor.credential_id or None,
        actor_credential_kind=actor.credential_kind,
        action=action,
        target_type=target_type,
        target_id=target_id,
        decision="allow",
        reason=reason,
    )


def _require_org_admin(session: Session, *, actor, org_id: str) -> None:
    if actor.is_bypass:
        return
    if not actor.is_human:
        raise CredentialError("HUMAN_CREDENTIAL_REQUIRED", "Identity management requires a human credential")
    
    membership = IdentityRepository(session).get_org_membership(
        org_id=org_id, user_id=actor.user_id
    )
    if membership is None or membership.role not in ADMIN_ROLES:
        raise CredentialError(
            "ORG_ADMIN_REQUIRED", "This action requires an organization admin"
        )


def _load_user(session: Session, *, user_id: str) -> UserModel:
    user = IdentityRepository(session).get_user(user_id)
    if user is None:
        raise CredentialError("USER_NOT_FOUND", "User not found")
    return user


def _credential_meta(credential: CredentialModel) -> dict[str, Any]:
    return {
        "id": credential.id,
        "user_id": credential.user_id,
        "kind": credential.kind,
        "label": credential.label,
        "status": credential.status,
        "token_prefix": credential.token_prefix,
        "expires_at": credential.expires_at.isoformat() if credential.expires_at else None,
        "last_used_at": credential.last_used_at.isoformat() if credential.last_used_at else None,
        "created_at": credential.created_at.isoformat(),
    }


def _validate_kind(kind: str) -> None:
    if kind not in API_CREDENTIAL_KINDS:
        raise CredentialError(
            "KIND_NOT_ALLOWED",
            f"Credential kind must be one of {', '.join(API_CREDENTIAL_KINDS)}",
        )


def _validate_expiry(expires_at: datetime | None) -> None:
    if expires_at is None:
        return
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= utc_now():
        raise CredentialError("EXPIRY_IN_PAST", "expires_at must be in the future")


def _issue(
    session: Session,
    *,
    actor,
    user_id: str,
    kind: str,
    label: str | None,
    expires_at: datetime | None,
) -> tuple[CredentialModel, str]:
    repo = IdentityRepository(session)
    user = _load_user(session, user_id=user_id)
    _require_org_admin(session, actor=actor, org_id=user.org_id)
    _validate_kind(kind)
    _validate_expiry(expires_at)
    token = secrets.token_urlsafe(32)
    credential = repo.create_api_credential(
        user_id=user.id,
        kind=kind,
        token_hash=hash_token(token),
        token_prefix=token_diagnostic_prefix(token),
        label=label,
        expires_at=expires_at,
    )
    _audit(
        session,
        actor=actor,
        org_id=user.org_id,
        action="credential.issue",
        target_type="credential",
        target_id=credential.id,
        reason=f"{kind} API credential issued" + (f" ({label})" if label else ""),
    )
    return credential, token


def issue_api_credential(
    session: Session,
    *,
    actor,
    user_id: str,
    kind: str,
    label: str | None = None,
    expires_at: datetime | None = None,
) -> dict[str, Any]:
    credential, token = _issue(
        session,
        actor=actor,
        user_id=user_id,
        kind=kind,
        label=label,
        expires_at=expires_at,
    )
    return {"credential": _credential_meta(credential), "token": token}


def rotate_api_credential(
    session: Session,
    *,
    actor,
    user_id: str,
    credential_id: str,
) -> dict[str, Any]:
    repo = IdentityRepository(session)
    user = _load_user(session, user_id=user_id)
    _require_org_admin(session, actor=actor, org_id=user.org_id)
    credential = repo.get_credential(credential_id)
    if credential is None or credential.user_id != user.id:
        raise CredentialError("CREDENTIAL_NOT_FOUND", "Credential not found")
    if credential.status != "active":
        raise CredentialError(
            "CREDENTIAL_NOT_ACTIVE",
            "Only an active credential can be rotated",
        )
    if credential.kind not in API_CREDENTIAL_KINDS:
        raise CredentialError(
            "KIND_NOT_ALLOWED",
            "Only issued API credentials (human/agent/ci) can be rotated",
        )
    repo.revoke_credential(credential)
    new_credential, token = _issue(
        session,
        actor=actor,
        user_id=user.id,
        kind=credential.kind,
        label=credential.label,
        expires_at=credential.expires_at,
    )
    _audit(
        session,
        actor=actor,
        org_id=user.org_id,
        action="credential.rotate",
        target_type="credential",
        target_id=new_credential.id,
        reason=f"{credential.kind} API credential rotated, previous {credential_id} revoked",
    )
    return {"credential": _credential_meta(new_credential), "token": token}


def list_credential_metadata(
    session: Session, *, actor, user_id: str
) -> list[dict[str, Any]]:
    repo = IdentityRepository(session)
    user = _load_user(session, user_id=user_id)
    _require_org_admin(session, actor=actor, org_id=user.org_id)
    return [
        _credential_meta(credential)
        for credential in repo.list_credentials_by_user(user.id)
        if credential.kind in API_CREDENTIAL_KINDS
    ]
