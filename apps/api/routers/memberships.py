from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.auth import get_current_principal
from apps.api.dependencies import get_db_session
from packages.core.auth import Principal
from packages.core.services.membership import (
    MembershipError,
    add_org_member,
    add_project_member,
    list_org_members,
    list_project_members,
    remove_org_member,
    remove_project_member,
    set_org_member_role,
    set_project_member_role,
)
from packages.core.uow import SqlAlchemyUnitOfWork

router = APIRouter(tags=["memberships"])


class AddMemberRequest(BaseModel):
    role: str = Field(min_length=1)
    user_id: str | None = None
    username: str | None = Field(default=None, max_length=64)


class SetRoleRequest(BaseModel):
    role: str = Field(min_length=1)


_FORBIDDEN = {"ORG_ADMIN_REQUIRED", "PROJECT_MANAGER_REQUIRED", "OWNER_ROLE_RESERVED", "LAST_ADMIN_GUARD"}
_NOT_FOUND = {"USER_NOT_FOUND", "PROJECT_NOT_FOUND"}


def _error(exc: MembershipError) -> HTTPException:
    if exc.code in _NOT_FOUND:
        status_code = 404
    elif exc.code in _FORBIDDEN:
        status_code = 403
    else:
        status_code = 400
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": exc.message})


# --- organization members ----------------------------------------------------

@router.get("/organizations/{org_id}/members")
def org_members(
    org_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> list[dict[str, Any]]:
    try:
        return list_org_members(session, actor=principal, org_id=org_id)
    except MembershipError as exc:
        raise _error(exc) from exc


@router.post("/organizations/{org_id}/members", status_code=201)
def org_member_add(
    org_id: str,
    payload: AddMemberRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            result = add_org_member(
                session,
                actor=principal,
                org_id=org_id,
                role=payload.role,
                user_id=payload.user_id,
                username=payload.username,
            )
            uow.commit()
    except MembershipError as exc:
        raise _error(exc) from exc
    return result


@router.patch("/organizations/{org_id}/members/{user_id}")
def org_member_role(
    org_id: str,
    user_id: str,
    payload: SetRoleRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            result = set_org_member_role(
                session,
                actor=principal,
                org_id=org_id,
                user_id=user_id,
                role=payload.role,
            )
            uow.commit()
    except MembershipError as exc:
        raise _error(exc) from exc
    return result


@router.delete("/organizations/{org_id}/members/{user_id}", status_code=204)
def org_member_remove(
    org_id: str,
    user_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> None:
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            remove_org_member(
                session,
                actor=principal,
                org_id=org_id,
                user_id=user_id,
            )
            uow.commit()
    except MembershipError as exc:
        raise _error(exc) from exc


# --- project members ---------------------------------------------------------

@router.get("/projects/{project_id}/members")
def project_members(
    project_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> list[dict[str, Any]]:
    try:
        return list_project_members(session, actor=principal, project_id=project_id)
    except MembershipError as exc:
        raise _error(exc) from exc


@router.post("/projects/{project_id}/members", status_code=201)
def project_member_add(
    project_id: str,
    payload: AddMemberRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            result = add_project_member(
                session,
                actor=principal,
                project_id=project_id,
                role=payload.role,
                user_id=payload.user_id,
                username=payload.username,
            )
            uow.commit()
    except MembershipError as exc:
        raise _error(exc) from exc
    return result


@router.patch("/projects/{project_id}/members/{user_id}")
def project_member_role(
    project_id: str,
    user_id: str,
    payload: SetRoleRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            result = set_project_member_role(
                session,
                actor=principal,
                project_id=project_id,
                user_id=user_id,
                role=payload.role,
            )
            uow.commit()
    except MembershipError as exc:
        raise _error(exc) from exc
    return result


@router.delete("/projects/{project_id}/members/{user_id}", status_code=204)
def project_member_remove(
    project_id: str,
    user_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> None:
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            remove_project_member(
                session,
                actor=principal,
                project_id=project_id,
                user_id=user_id,
            )
            uow.commit()
    except MembershipError as exc:
        raise _error(exc) from exc
