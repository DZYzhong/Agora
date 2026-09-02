from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.auth_session import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    SessionAuthError,
    login,
    reauthenticate,
    resolve_session_principal,
)
from apps.api.dependencies import get_db_session
from packages.core.models import utc_now
from packages.core.repositories.identities import IdentityRepository
from packages.core.repositories.sessions_auth import WebSessionRepository
from packages.core.uow import SqlAlchemyUnitOfWork

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str = Field(min_length=1, max_length=512)


class ReauthRequest(BaseModel):
    password: str = Field(min_length=1, max_length=512)


def _session_cookie(token: str) -> dict[str, Any]:
    return {
        "key": SESSION_COOKIE_NAME,
        "value": token,
        "httponly": True,
        "samesite": "strict",
        "secure": True,
        "path": "/",
        "max_age": 12 * 60 * 60,
    }


def _csrf_cookie(token: str) -> dict[str, Any]:
    return {
        "key": CSRF_COOKIE_NAME,
        "value": token,
        "httponly": False,
        "samesite": "strict",
        "secure": True,
        "path": "/",
        "max_age": 12 * 60 * 60,
    }


def _client_source(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


@router.post("/login")
def login_endpoint(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_db_session),
):
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            result = login(session, username=payload.username, password=payload.password, source=_client_source(request))
            uow.commit()
    except SessionAuthError as exc:
        raise HTTPException(status_code=401, detail={"code": exc.code, "message": exc.message}) from exc
    response.set_cookie(**_session_cookie(result.session_token))
    response.set_cookie(**_csrf_cookie(result.csrf_token))
    return {
        "user": {
            "id": result.user.id,
            "org_id": result.user.org_id,
            "username": result.user.username,
            "display_name": result.user.display_name,
        },
        "csrf_token": result.csrf_token,
        "session_id": result.session_id,
        "expires_at": result.expires_at,
        "session_max_age_seconds": 12 * 60 * 60,
        "idle_timeout_seconds": 30 * 60,
    }


@router.post("/logout")
def logout_endpoint(
    request: Request,
    response: Response,
    session: Session = Depends(get_db_session),
):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        with SqlAlchemyUnitOfWork(session) as uow:
            from packages.core.auth import hash_token

            record = WebSessionRepository(session).get_active_by_token_hash(hash_token(token), now=utc_now())
            if record is not None:
                WebSessionRepository(session).revoke(record, at=utc_now())
            uow.commit()
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/session")
def current_session(
    request: Request,
    session: Session = Depends(get_db_session),
):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    principal = resolve_session_principal(session, session_token=token)
    if principal is None:
        raise HTTPException(status_code=401, detail={"code": "SESSION_REQUIRED", "message": "No active session"})
    user = IdentityRepository(session).get_user(principal.user_id)
    record = WebSessionRepository(session).get(principal.credential_id)
    return {
        "user": {
            "id": principal.user_id,
            "org_id": principal.org_id,
            "username": user.username if user is not None else principal.user_id,
            "display_name": user.display_name if user is not None else None,
        },
        "session_id": principal.credential_id,
        "reauthenticated": record.reauth_expires_at is not None if record is not None else False,
        "csrf_token": request.cookies.get(CSRF_COOKIE_NAME),
    }


@router.post("/reauth")
def reauth_endpoint(
    payload: ReauthRequest,
    request: Request,
    session: Session = Depends(get_db_session),
):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            principal = resolve_session_principal(session, session_token=token)
            if principal is None:
                raise HTTPException(status_code=401, detail={"code": "SESSION_REQUIRED", "message": "No active session"})
            reauthenticate(session, principal=principal, password=payload.password, source=_client_source(request))
            uow.commit()
    except SessionAuthError as exc:
        raise HTTPException(status_code=403, detail={"code": exc.code, "message": exc.message}) from exc
    return {"ok": True, "reauthenticated": True}
