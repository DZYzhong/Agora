"""PR3 B1: organization and project membership management service.

Guards mirror the existing admin model: organization admins (owner/admin)
manage org membership; project owners/admins (or org admins) manage project
membership. Controlled role sets prevent ad-hoc roles; "last administrator"
guards prevent lockout; every mutation is audited.
"""

from typing import Any

from sqlalchemy.orm import Session

from packages.core.auth import (
    ORG_ROLES,
    PROJECT_MANAGER_ROLES,
    PROJECT_ROLES,
)
from packages.core.auth_admin import ADMIN_ROLES
from packages.core.models import ProjectModel, UserModel
from packages.core.repositories.identities import IdentityRepository
from packages.core.repositories.projects import ProjectRepository
from packages.core.repositories.security import SecurityRepository


class MembershipError(Exception):
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
        raise MembershipError("HUMAN_CREDENTIAL_REQUIRED", "Identity management requires a human credential")
    
    membership = IdentityRepository(session).get_org_membership(
        org_id=org_id, user_id=actor.user_id
    )
    if membership is None or membership.role not in ADMIN_ROLES:
        raise MembershipError(
            "ORG_ADMIN_REQUIRED", "This action requires an organization admin"
        )


def _org_role_of(session: Session, *, actor, org_id: str) -> str | None:
    if actor.is_bypass:
        return "owner"
    membership = IdentityRepository(session).get_org_membership(
        org_id=org_id, user_id=actor.user_id
    )
    return membership.role if membership is not None else None


def _project_role_of(session: Session, *, actor, project: ProjectModel) -> str | None:
    if actor.is_bypass:
        return "owner"
    membership = IdentityRepository(session).get_membership(
        project_id=project.id, user_id=actor.user_id
    )
    return membership.role if membership is not None else None


def _require_project_manager(
    session: Session, *, actor, project: ProjectModel
) -> None:
    if actor.is_bypass:
        return
    if not actor.is_human:
        raise MembershipError("HUMAN_CREDENTIAL_REQUIRED", "Identity management requires a human credential")
    if _org_role_of(session, actor=actor, org_id=project.org_id) in ADMIN_ROLES:
        return
    role = _project_role_of(session, actor=actor, project=project)
    if role not in PROJECT_MANAGER_ROLES:
        raise MembershipError(
            "PROJECT_MANAGER_REQUIRED",
            "This action requires a project owner/admin or organization admin",
        )


def _can_grant_project_owner(session: Session, *, actor, project: ProjectModel) -> bool:
    """Granting/regranting the project owner role is reserved to the project
    owner or an organization admin (mirrors the org owner rule)."""
    if actor.is_bypass:
        return True
    if _org_role_of(session, actor=actor, org_id=project.org_id) in ADMIN_ROLES:
        return True
    return _project_role_of(session, actor=actor, project=project) == "owner"


def _require_role_allowed(role: str, allowed: set[str], scope: str) -> None:
    if role not in allowed:
        raise MembershipError(
            "ROLE_NOT_ALLOWED",
            f"Role {role!r} is not allowed for {scope} membership",
        )


def _resolve_user(
    repo: IdentityRepository, *, org_id: str, user_id: str | None, username: str | None
) -> UserModel:
    if bool(user_id) == bool(username):
        raise MembershipError(
            "IDENTIFIER_REQUIRED",
            "Provide exactly one of user_id or username",
        )
    user = repo.get_user(user_id) if user_id else repo.get_user_by_username(
        org_id=org_id, username=username
    )
    if user is None:
        raise MembershipError("USER_NOT_FOUND", "User not found")
    if user.org_id != org_id:
        raise MembershipError(
            "USER_NOT_IN_ORG", "User does not belong to this organization"
        )
    return user


def _member_payload(user: UserModel, role: str) -> dict[str, Any]:
    return {
        "user": {
            "id": user.id,
            "org_id": user.org_id,
            "username": user.username,
            "display_name": user.display_name,
            "status": user.status,
        },
        "role": role,
    }


# --- organization membership ------------------------------------------------


def add_org_member(
    session: Session,
    *,
    actor,
    org_id: str,
    role: str,
    user_id: str | None = None,
    username: str | None = None,
) -> dict[str, Any]:
    # (transaction owned by the calling API route)
    _require_org_admin(session, actor=actor, org_id=org_id)
    _require_role_allowed(role, ORG_ROLES, "organization")
    if role == "owner" and _org_role_of(session, actor=actor, org_id=org_id) != "owner":
        raise MembershipError(
            "OWNER_ROLE_RESERVED",
            "The owner role can only be granted by the organization owner",
        )
    repo = IdentityRepository(session)
    user = _resolve_user(repo, org_id=org_id, user_id=user_id, username=username)
    existing = repo.get_org_membership(org_id=org_id, user_id=user.id)
    membership = repo.set_org_role(org_id=org_id, user_id=user.id, role=role)
    _audit(
        session,
        actor=actor,
        org_id=org_id,
        action="org.member.role" if existing else "org.member.add",
        target_type="user",
        target_id=user.id,
        reason=f"organization membership role {role}",
    )
    return _member_payload(user, membership.role)


def set_org_member_role(
    session: Session,
    *,
    actor,
    org_id: str,
    user_id: str,
    role: str,
) -> dict[str, Any]:
    # (transaction owned by the calling API route)
    _require_org_admin(session, actor=actor, org_id=org_id)
    _require_role_allowed(role, ORG_ROLES, "organization")
    if role == "owner" and _org_role_of(session, actor=actor, org_id=org_id) != "owner":
        raise MembershipError(
            "OWNER_ROLE_RESERVED",
            "The owner role can only be granted by the organization owner",
        )
    repo = IdentityRepository(session)
    user = _resolve_user(repo, org_id=org_id, user_id=user_id, username=None)
    membership = repo.get_org_membership(org_id=org_id, user_id=user.id)
    if membership is None:
        raise MembershipError("NOT_ORG_MEMBER", "User is not an organization member")
    actor_role = _org_role_of(session, actor=actor, org_id=org_id)
    target_self = user.id == actor.user_id
    if membership.role in ADMIN_ROLES:
        if repo.count_org_administrators(org_id) <= 1 and target_self:
            raise MembershipError(
                "LAST_ADMIN_GUARD", "Cannot demote the last organization admin"
            )
        if not target_self and actor_role != "owner":
            raise MembershipError(
                "ORG_ADMIN_REQUIRED",
                "Only the organization owner can change an admin's role",
            )
    repo.set_org_role(org_id=org_id, user_id=user.id, role=role)
    _audit(
        session,
        actor=actor,
        org_id=org_id,
        action="org.member.role",
        target_type="user",
        target_id=user.id,
        reason=f"organization role changed to {role}",
    )
    return _member_payload(user, role)


def remove_org_member(
    session: Session,
    *,
    actor,
    org_id: str,
    user_id: str,
) -> None:
    # (transaction owned by the calling API route)
    _require_org_admin(session, actor=actor, org_id=org_id)
    repo = IdentityRepository(session)
    user = _resolve_user(repo, org_id=org_id, user_id=user_id, username=None)
    membership = repo.get_org_membership(org_id=org_id, user_id=user.id)
    if membership is None:
        raise MembershipError("NOT_ORG_MEMBER", "User is not an organization member")
    actor_role = _org_role_of(session, actor=actor, org_id=org_id)
    target_self = user.id == actor.user_id
    if membership.role in ADMIN_ROLES:
        if repo.count_org_administrators(org_id) <= 1 and target_self:
            raise MembershipError(
                "LAST_ADMIN_GUARD", "Cannot remove the last organization admin"
            )
        if not target_self and actor_role != "owner":
            raise MembershipError(
                "ORG_ADMIN_REQUIRED",
                "Only the organization owner can remove an admin",
            )
    repo.remove_org_membership(org_id=org_id, user_id=user.id)
    _audit(
        session,
        actor=actor,
        org_id=org_id,
        action="org.member.remove",
        target_type="user",
        target_id=user.id,
        reason="organization membership removed",
    )


def list_org_members(session: Session, *, actor, org_id: str) -> list[dict[str, Any]]:
    _require_org_admin(session, actor=actor, org_id=org_id)
    repo = IdentityRepository(session)
    return [
        _member_payload(user, membership.role)
        for user, membership in repo.list_org_members(org_id)
    ]


# --- project membership ------------------------------------------------------


def _resolve_project(session: Session, project_id: str) -> ProjectModel:
    project = ProjectRepository(session).get(project_id)
    if project is None:
        raise MembershipError("PROJECT_NOT_FOUND", "Project not found")
    return project


def add_project_member(
    session: Session,
    *,
    actor,
    project_id: str,
    role: str,
    user_id: str | None = None,
    username: str | None = None,
) -> dict[str, Any]:
    # (transaction owned by the calling API route)
    project = _resolve_project(session, project_id)
    _require_project_manager(session, actor=actor, project=project)
    _require_role_allowed(role, PROJECT_ROLES, "project")
    if role == "owner" and not _can_grant_project_owner(session, actor=actor, project=project):
        raise MembershipError(
            "OWNER_ROLE_RESERVED",
            "The project owner role can only be granted by the project owner or an org admin",
        )
    repo = IdentityRepository(session)
    user = _resolve_user(
        repo, org_id=project.org_id, user_id=user_id, username=username
    )
    existing = repo.get_membership(project_id=project.id, user_id=user.id)
    membership = repo.grant_membership(
        project_id=project.id, user_id=user.id, role=role
    )
    _audit(
        session,
        actor=actor,
        org_id=project.org_id,
        action="project.member.role" if existing else "project.member.add",
        target_type="user",
        target_id=user.id,
        reason=f"project membership role {role} on {project.id}",
    )
    return _member_payload(user, membership.role)


def set_project_member_role(
    session: Session,
    *,
    actor,
    project_id: str,
    user_id: str,
    role: str,
) -> dict[str, Any]:
    # (transaction owned by the calling API route)
    project = _resolve_project(session, project_id)
    _require_project_manager(session, actor=actor, project=project)
    _require_role_allowed(role, PROJECT_ROLES, "project")
    if role == "owner" and not _can_grant_project_owner(session, actor=actor, project=project):
        raise MembershipError(
            "OWNER_ROLE_RESERVED",
            "The project owner role can only be granted by the project owner or an org admin",
        )
    repo = IdentityRepository(session)
    user = _resolve_user(
        repo, org_id=project.org_id, user_id=user_id, username=None
    )
    membership = repo.get_membership(project_id=project.id, user_id=user.id)
    if membership is None:
        raise MembershipError("NOT_PROJECT_MEMBER", "User is not a project member")
    actor_role = _project_role_of(session, actor=actor, project=project)
    org_role = _org_role_of(session, actor=actor, org_id=project.org_id)
    target_self = user.id == actor.user_id
    if membership.role in PROJECT_MANAGER_ROLES and role not in PROJECT_MANAGER_ROLES:
        if repo.count_project_managers(project.id) <= 1 and target_self:
            raise MembershipError(
                "LAST_ADMIN_GUARD", "Cannot demote the last project owner/admin"
            )
        if not target_self and actor_role != "owner" and org_role not in ADMIN_ROLES:
            raise MembershipError(
                "PROJECT_MANAGER_REQUIRED",
                "Only the project owner or an org admin can demote a project owner/admin",
            )
    repo.grant_membership(project_id=project.id, user_id=user.id, role=role)
    _audit(
        session,
        actor=actor,
        org_id=project.org_id,
        action="project.member.role",
        target_type="user",
        target_id=user.id,
        reason=f"project role changed to {role} on {project.id}",
    )
    return _member_payload(user, role)


def remove_project_member(
    session: Session,
    *,
    actor,
    project_id: str,
    user_id: str,
) -> None:
    # (transaction owned by the calling API route)
    project = _resolve_project(session, project_id)
    _require_project_manager(session, actor=actor, project=project)
    repo = IdentityRepository(session)
    user = _resolve_user(
        repo, org_id=project.org_id, user_id=user_id, username=None
    )
    membership = repo.get_membership(project_id=project.id, user_id=user.id)
    if membership is None:
        raise MembershipError("NOT_PROJECT_MEMBER", "User is not a project member")
    actor_role = _project_role_of(session, actor=actor, project=project)
    org_role = _org_role_of(session, actor=actor, org_id=project.org_id)
    target_self = user.id == actor.user_id
    if membership.role in PROJECT_MANAGER_ROLES:
        if repo.count_project_managers(project.id) <= 1 and target_self:
            raise MembershipError(
                "LAST_ADMIN_GUARD", "Cannot remove the last project owner/admin"
            )
        if not target_self and actor_role != "owner" and org_role not in ADMIN_ROLES:
            raise MembershipError(
                "PROJECT_MANAGER_REQUIRED",
                "Only the project owner or an org admin can remove a project owner/admin",
            )
    repo.remove_project_membership(project_id=project.id, user_id=user.id)
    _audit(
        session,
        actor=actor,
        org_id=project.org_id,
        action="project.member.remove",
        target_type="user",
        target_id=user.id,
        reason=f"project membership removed from {project.id}",
    )


def list_project_members(
    session: Session, *, actor, project_id: str
) -> list[dict[str, Any]]:
    project = _resolve_project(session, project_id)
    _require_project_manager(session, actor=actor, project=project)
    repo = IdentityRepository(session)
    return [
        _member_payload(user, membership.role)
        for user, membership in repo.list_project_members(project.id)
    ]
