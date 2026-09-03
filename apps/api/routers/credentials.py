from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.auth import get_current_principal
from apps.api.dependencies import get_db_session
from packages.core.auth import Principal
from packages.core.services.credentials import (
    CredentialError,
    issue_api_credential,
    list_credential_metadata,
    rotate_api_credential,
)
from packages.core.uow import SqlAlchemyUnitOfWork

router = APIRouter(prefix="/users", tags=["credentials"])


class IssueCredentialRequest(BaseModel):
    kind: str = Field(min_length=1)
    label: str | None = Field(default=None, max_length=128)
    expires_at: str | None = None


_FORBIDDEN = {"ORG_ADMIN_REQUIRED", "KIND_NOT_ALLOWED"}
_NOT_FOUND = {"USER_NOT_FOUND", "CREDENTIAL_NOT_FOUND"}


def _error(exc: CredentialError) -> HTTPException:
    if exc.code in _NOT_FOUND:
        status_code = 404
    elif exc.code in _FORBIDDEN:
        status_code = 403
    else:
        status_code = 400
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": exc.message})


def _parse_expiry(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "EXPIRY_INVALID", "message": "expires_at must be an ISO-8601 datetime"},
        ) from exc


@router.get("/{user_id}/credentials")
def credentials_list(
    user_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> list[dict[str, Any]]:
    try:
        return list_credential_metadata(session, actor=principal, user_id=user_id)
    except CredentialError as exc:
        raise _error(exc) from exc


@router.post("/{user_id}/credentials", status_code=201)
def credentials_issue(
    user_id: str,
    payload: IssueCredentialRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    expires_at = _parse_expiry(payload.expires_at)
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            result = issue_api_credential(
                session,
                actor=principal,
                user_id=user_id,
                kind=payload.kind,
                label=payload.label,
                expires_at=expires_at,
            )
            uow.commit()
    except CredentialError as exc:
        raise _error(exc) from exc
    return result


@router.post("/{user_id}/credentials/{credential_id}/rotate")
def credentials_rotate(
    user_id: str,
    credential_id: str,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            result = rotate_api_credential(
                session,
                actor=principal,
                user_id=user_id,
                credential_id=credential_id,
            )
            uow.commit()
    except CredentialError as exc:
        raise _error(exc) from exc
    return result
