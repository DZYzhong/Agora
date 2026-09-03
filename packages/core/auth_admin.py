"""PR1B admin bootstrap, user lifecycle and credential flows.

Design: `docs/superpowers/specs/2026-08-28-agora-production-readiness-design.zh-CN.md`
§5.2 — one-time Admin bootstrap, Argon2id local accounts, single-use expiring
activation/reset credentials (hashed-only), immediate revocation on disable,
and audit of every identity/credential change.

Plaintext credentials are returned exactly once (for external delivery) and
are never persisted; the database stores only hashes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import secrets
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from packages.core.auth import Principal, hash_token, token_diagnostic_prefix
from packages.core.models import CredentialModel, UserModel, utc_now
from packages.core.passwords import hash_password
from packages.core.repositories.approval_grants import ApprovalGrantRepository
from packages.core.repositories.identities import IdentityRepository
from packages.core.repositories.security import SecurityRepository
from packages.core.repositories.sessions_auth import WebSessionRepository
from packages.core.uow import SqlAlchemyUnitOfWork

ACTIVATION_TOKEN_TTL_MINUTES = 30
RESET_TOKEN_TTL_MINUTES = 15
ADMIN_ROLES = ("owner", "admin")


class AdminActionError(ValueError):
    def __init__(self, *, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class CreatedUser:
    user_id: str
    username: str
    display_name: str
    status: str
    activation_token: str
    activation_expires_at: datetime


@dataclass(frozen=True)
class ResetIssued:
    user_id: str
    username: str
    reset_token: str
    reset_expires_at: datetime


def bootstrap_admin(
    session: Session,
    *,
    org_id: str,
    admin_username: str,
    admin_password: str,
    display_name: str = "Administrator",
) -> UserModel:
    """One-time admin bootstrap. Concurrent/second attempts fail deterministically."""
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            repo = IdentityRepository(session)
            if repo.list_org_admins(org_id):
                raise AdminActionError(
                    code="ADMIN_ALREADY_BOOTSTRAPPED",
                    message=f"An admin already exists for organization {org_id}",
                )
            user = repo.create_user(
                org_id=org_id,
                username=admin_username,
                display_name=display_name,
                password_hash=hash_password(admin_password),
                status="active",
            )
            repo.create_org_membership(org_id=org_id, user_id=user.id, role="admin")
            SecurityRepository(session).create_audit_event(
                org_id=org_id,
                project_id=None,
                actor_user_id=user.id,
                actor_credential_id=None,
                actor_credential_kind="system",
                action="admin.bootstrap",
                target_type="organization",
                target_id=org_id,
                decision="allow",
                reason="one-time admin bootstrap",
            )
            uow.commit()
            return user
    except IntegrityError as exc:
        raise AdminActionError(
            code="ADMIN_ALREADY_BOOTSTRAPPED",
            message=f"An admin already exists for organization {org_id}",
        ) from exc


def create_user_with_activation(
    session: Session,
    *,
    actor: Principal,
    org_id: str,
    username: str,
    display_name: str,
) -> CreatedUser:
    with SqlAlchemyUnitOfWork(session) as uow:
        _require_org_admin(session, actor=actor, org_id=org_id)
        repo = IdentityRepository(session)
        try:
            user = repo.create_user(
                org_id=org_id,
                username=username,
                display_name=display_name,
                status="pending_activation",
            )
        except ValueError as exc:
            raise AdminActionError(code="USERNAME_TAKEN", message=str(exc)) from exc
        token = secrets.token_urlsafe(32)
        expires_at = utc_now() + timedelta(minutes=ACTIVATION_TOKEN_TTL_MINUTES)
        repo.create_single_use_credential(
            user_id=user.id,
            kind="activation",
            token_hash=hash_token(token),
            token_prefix=token_diagnostic_prefix(token),
            expires_at=expires_at,
        )
        _audit(
            session,
            actor=actor,
            org_id=org_id,
            action="user.create",
            target_type="user",
            target_id=user.id,
            decision="allow",
            reason=f"activation credential issued, expires in {ACTIVATION_TOKEN_TTL_MINUTES} minutes",
        )
        uow.commit()
        return CreatedUser(
            user_id=user.id,
            username=username,
            display_name=display_name,
            status=user.status,
            activation_token=token,
            activation_expires_at=expires_at,
        )


def activate_user(session: Session, *, activation_token: str, new_password: str) -> UserModel:
    with SqlAlchemyUnitOfWork(session) as uow:
        repo = IdentityRepository(session)
        credential = repo.get_active_single_use_credential_by_hash(
            hash_token(activation_token), now=utc_now()
        )
        if credential is None or credential.kind != "activation":
            raise AdminActionError(
                code="ACTIVATION_TOKEN_INVALID",
                message="Activation token is invalid, expired or already used",
            )
        user = repo.get_user(credential.user_id)
        if user is None or user.status != "pending_activation":
            raise AdminActionError(
                code="USER_NOT_PENDING_ACTIVATION",
                message="User is not awaiting activation",
            )
        repo.set_user_password(user, password_hash=hash_password(new_password))
        repo.set_user_status(user, status="active")
        repo.consume_single_use_credential(credential, at=utc_now())
        _audit(
            session,
            actor=_principal_for_user(repo, user),
            org_id=user.org_id,
            action="user.activate",
            target_type="user",
            target_id=user.id,
            decision="allow",
            reason="activation credential consumed",
        )
        uow.commit()
        return user


def issue_reset_credential(session: Session, *, actor: Principal, user_id: str) -> ResetIssued:
    with SqlAlchemyUnitOfWork(session) as uow:
        repo = IdentityRepository(session)
        user = repo.get_user(user_id)
        if user is None:
            raise AdminActionError(code="USER_NOT_FOUND", message="User not found")
        _require_org_admin(session, actor=actor, org_id=user.org_id)
        token = secrets.token_urlsafe(32)
        expires_at = utc_now() + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)
        repo.create_single_use_credential(
            user_id=user.id,
            kind="reset",
            token_hash=hash_token(token),
            token_prefix=token_diagnostic_prefix(token),
            expires_at=expires_at,
        )
        _audit(
            session,
            actor=actor,
            org_id=user.org_id,
            action="credential.reset_issue",
            target_type="user",
            target_id=user.id,
            decision="allow",
            reason=f"reset credential issued, expires in {RESET_TOKEN_TTL_MINUTES} minutes",
        )
        uow.commit()
        return ResetIssued(
            user_id=user.id,
            username=user.username or user.display_name,
            reset_token=token,
            reset_expires_at=expires_at,
        )


def reset_password(session: Session, *, reset_token: str, new_password: str) -> UserModel:
    with SqlAlchemyUnitOfWork(session) as uow:
        repo = IdentityRepository(session)
        credential = repo.get_active_single_use_credential_by_hash(
            hash_token(reset_token), now=utc_now()
        )
        if credential is None or credential.kind != "reset":
            raise AdminActionError(
                code="RESET_TOKEN_INVALID",
                message="Reset token is invalid, expired or already used",
            )
        user = repo.get_user(credential.user_id)
        if user is None or user.status != "active":
            raise AdminActionError(code="USER_NOT_ACTIVE", message="User is not active")
        repo.set_user_password(user, password_hash=hash_password(new_password))
        repo.consume_single_use_credential(credential, at=utc_now())
        _audit(
            session,
            actor=_principal_for_user(repo, user),
            org_id=user.org_id,
            action="credential.reset_use",
            target_type="user",
            target_id=user.id,
            decision="allow",
            reason="reset credential consumed",
        )
        uow.commit()
        return user


def set_user_enabled(session: Session, *, actor: Principal, user_id: str, enabled: bool) -> UserModel:
    with SqlAlchemyUnitOfWork(session) as uow:
        repo = IdentityRepository(session)
        user = repo.get_user(user_id)
        if user is None:
            raise AdminActionError(code="USER_NOT_FOUND", message="User not found")
        _require_org_admin(session, actor=actor, org_id=user.org_id)
        if enabled:
            repo.set_user_status(user, status="active")
            _audit(
                session,
                actor=actor,
                org_id=user.org_id,
                action="user.enable",
                target_type="user",
                target_id=user.id,
                decision="allow",
                reason="user enabled",
            )
        else:
            repo.set_user_status(user, status="disabled")
            now = utc_now()
            revoked = repo.revoke_user_credentials(user_id)
            sessions_revoked = WebSessionRepository(session).revoke_user_sessions(
                user_id, at=now
            )
            grants_revoked = ApprovalGrantRepository(session).revoke_user_grants(
                user_id, at=now
            )
            _audit(
                session,
                actor=actor,
                org_id=user.org_id,
                action="user.disable",
                target_type="user",
                target_id=user.id,
                decision="allow",
                reason=(
                    f"{revoked} credentials, {sessions_revoked} sessions, "
                    f"{grants_revoked} approval grants revoked"
                ),
            )
        uow.commit()
        return user


def revoke_credential(session: Session, *, actor: Principal, credential_id: str) -> CredentialModel:
    with SqlAlchemyUnitOfWork(session) as uow:
        repo = IdentityRepository(session)
        credential = repo.get_credential(credential_id)
        if credential is None:
            raise AdminActionError(code="CREDENTIAL_NOT_FOUND", message="Credential not found")
        _require_org_admin(session, actor=actor, org_id=actor.org_id)
        repo.revoke_credential(credential)
        _audit(
            session,
            actor=actor,
            org_id=actor.org_id,
            action="credential.revoke",
            target_type="credential",
            target_id=credential.id,
            decision="allow",
            reason=f"{credential.kind} credential revoked",
        )
        uow.commit()
        return credential


def list_users(session: Session, *, actor: Principal, org_id: str) -> list[UserModel]:
    _require_org_admin(session, actor=actor, org_id=org_id)
    return IdentityRepository(session).list_users(org_id)


def _require_org_admin(session: Session, *, actor: Principal, org_id: str) -> None:
    if actor.is_bypass:
        return
    membership = IdentityRepository(session).get_org_membership(org_id=org_id, user_id=actor.user_id)
    if membership is None or membership.role not in ADMIN_ROLES:
        raise AdminActionError(
            code="ORG_ADMIN_REQUIRED",
            message="This action requires an organization admin",
        )


def _principal_for_user(repo: IdentityRepository, user: UserModel) -> Principal:
    return Principal(
        org_id=user.org_id,
        user_id=user.id,
        credential_id="",
        credential_kind="human",
        token_prefix="",
    )


def _audit(
    session: Session,
    *,
    actor: Principal,
    org_id: str,
    action: str,
    target_type: str,
    target_id: str,
    decision: str,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
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
        decision=decision,
        reason=reason,
        metadata=metadata,
    )
