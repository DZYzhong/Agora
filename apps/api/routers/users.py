from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.auth import get_current_principal
from apps.api.dependencies import get_db_session
from packages.core.auth import Principal
from packages.core.auth_admin import (
    AdminActionError,
    activate_user,
    create_user_with_activation,
    issue_reset_credential,
    list_users,
    reset_password,
    revoke_credential,
    set_user_enabled,
)
from packages.core.models import UserModel

router = APIRouter(prefix="/users", tags=["users"])


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    display_name: str = Field(min_length=1, max_length=128)
    org_id: str | None = None


class ActivateUserRequest(BaseModel):
    activation_token: str
    new_password: str = Field(min_length=8, max_length=512)


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str = Field(min_length=8, max_length=512)


def _user_to_dict(user: UserModel) -> dict[str, Any]:
    return {
        "id": user.id,
        "org_id": user.org_id,
        "username": user.username,
        "display_name": user.display_name,
        "status": user.status,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


def _admin_error(exc: AdminActionError) -> HTTPException:
    status_code = 403 if exc.code == "ORG_ADMIN_REQUIRED" else 400
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": exc.message})


@router.post("", status_code=201)
def create_user(
    payload: CreateUserRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    """Admin creates a user; the one-time activation token is returned once for external delivery."""
    org_id = payload.org_id if principal.is_bypass else principal.org_id
    if not org_id:
        raise HTTPException(status_code=400, detail={"code": "ORG_ID_REQUIRED", "message": "org_id is required"})
    try:
        created = create_user_with_activation(
            session,
            actor=principal,
            org_id=org_id,
            username=payload.username,
            display_name=payload.display_name,
        )
    except AdminActionError as exc:
        raise _admin_error(exc) from exc
    return {
        "user": {
            "id": created.user_id,
            "org_id": org_id,
            "username": created.username,
            "display_name": created.display_name,
            "status": created.status,
        },
        "activation_token": created.activation_token,
        "activation_expires_at": created.activation_expires_at,
        "delivery": "deliver the activation token to the user over an authenticated external channel",
    }


@router.post("/activate")
def activate(
    payload: ActivateUserRequest,
    session: Session = Depends(get_db_session),
):
    """First-time password set using the one-time activation credential."""
    try:
        user = activate_user(session, activation_token=payload.activation_token, new_password=payload.new_password)
    except AdminActionError as exc:
        raise _admin_error(exc) from exc
    return {"ok": True, "user": _user_to_dict(user)}


@router.post("/reset-password")
def reset_password_endpoint(
    payload: ResetPasswordRequest,
    session: Session = Depends(get_db_session),
):
    """Password reset using the one-time reset credential issued by an admin."""
    try:
        user = reset_password(session, reset_token=payload.reset_token, new_password=payload.new_password)
    except AdminActionError as exc:
        raise _admin_error(exc) from exc
    return {"ok": True, "user": _user_to_dict(user)}


@router.post("/{user_id}/reset")
def issue_reset(
    user_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    """Admin issues a one-time 15-minute reset credential; returned once for external delivery."""
    try:
        reset = issue_reset_credential(session, actor=principal, user_id=user_id)
    except AdminActionError as exc:
        raise _admin_error(exc) from exc
    return {
        "user_id": reset.user_id,
        "username": reset.username,
        "reset_token": reset.reset_token,
        "reset_expires_at": reset.reset_expires_at,
        "delivery": "deliver the reset token to the user over an authenticated external channel",
    }


@router.post("/{user_id}/disable")
def disable_user(
    user_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    try:
        user = set_user_enabled(session, actor=principal, user_id=user_id, enabled=False)
    except AdminActionError as exc:
        raise _admin_error(exc) from exc
    return {"ok": True, "user": _user_to_dict(user)}


@router.post("/{user_id}/enable")
def enable_user(
    user_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    try:
        user = set_user_enabled(session, actor=principal, user_id=user_id, enabled=True)
    except AdminActionError as exc:
        raise _admin_error(exc) from exc
    return {"ok": True, "user": _user_to_dict(user)}


@router.post("/{user_id}/credentials/{credential_id}/revoke")
def revoke_credential_endpoint(
    user_id: str,
    credential_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    try:
        revoked = revoke_credential(session, actor=principal, credential_id=credential_id)
    except AdminActionError as exc:
        raise _admin_error(exc) from exc
    return {"ok": True, "credential_id": revoked.id, "status": revoked.status}


@router.get("")
def list_users_endpoint(
    org_id: str | None = Query(default=None),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
):
    resolved_org_id = org_id if principal.is_bypass else principal.org_id
    if not resolved_org_id:
        raise HTTPException(status_code=400, detail={"code": "ORG_ID_REQUIRED", "message": "org_id is required"})
    try:
        users = list_users(session, actor=principal, org_id=resolved_org_id)
    except AdminActionError as exc:
        raise _admin_error(exc) from exc
    return {"users": [_user_to_dict(user) for user in users]}
