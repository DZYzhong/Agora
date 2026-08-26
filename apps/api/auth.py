import os

from fastapi import Header, HTTPException, status
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import auth_bypass_enabled, get_engine
from packages.core.auth import (
    BootstrapAuthError,
    Principal,
    bootstrap_local_identity,
    can_approve_project_knowledge,
    bypass_principal,
    has_project_membership,
    project_role,
    resolve_principal,
)


def bootstrap_auth_from_env() -> None:
    if auth_bypass_enabled():
        return
    session = sessionmaker(bind=get_engine())()
    try:
        bootstrap_local_identity(
            session,
            human_token=os.environ.get("AGORA_BOOTSTRAP_HUMAN_TOKEN"),
            agent_token=os.environ.get("AGORA_BOOTSTRAP_AGENT_TOKEN"),
            org_id=os.environ.get("AGORA_BOOTSTRAP_ORG_ID"),
        )
    except BootstrapAuthError as exc:
        raise RuntimeError(str(exc)) from exc
    finally:
        session.close()


def get_current_principal(authorization: str | None = Header(default=None)) -> Principal:
    if auth_bypass_enabled():
        return bypass_principal()
    token = _bearer_token(authorization)
    session = sessionmaker(bind=get_engine())()
    try:
        principal = resolve_principal(session, bearer_token=token)
        if principal is None:
            raise _auth_error("INVALID_CREDENTIAL", "Invalid bearer token")
        return principal
    finally:
        session.close()


def require_human(principal: Principal) -> None:
    if not principal.is_human:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "HUMAN_CREDENTIAL_REQUIRED",
                "message": "This action requires a human credential",
            },
        )


def require_project_member(session, principal: Principal, *, project_id: str) -> None:
    if not has_project_membership(session, principal=principal, project_id=project_id):
        raise HTTPException(status_code=404, detail="Project not found")


def require_project_approver(session, principal: Principal, *, project_id: str) -> None:
    if not can_approve_project_knowledge(session, principal=principal, project_id=project_id):
        role = project_role(session, principal=principal, project_id=project_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "PROJECT_ROLE_REQUIRED",
                "message": "This action requires project owner, admin, or reviewer role",
                "required_roles": ["owner", "admin", "reviewer"],
                "actual_role": role,
            },
        )


def _bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise _auth_error("AUTH_REQUIRED", "Authentication required")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _auth_error("AUTH_REQUIRED", "Authentication required")
    return token


def _auth_error(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": code, "message": message},
        headers={"WWW-Authenticate": "Bearer"},
    )
