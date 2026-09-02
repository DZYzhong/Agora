"""PR1B web session authentication: login, session resolution, CSRF and reauth.

Design: `docs/superpowers/specs/2026-08-28-agora-production-readiness-design.zh-CN.md`
§5.3 — the session ID lives only in a `Secure`/`HttpOnly`/`SameSite=Strict`
cookie; state changes require a CSRF token and Origin validation; login and
password reset are rate-limited per user and source; reauthentication gates
high-risk actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import secrets
import threading
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.core.auth import Principal, hash_token
from packages.core.models import UserModel, WebSessionModel, utc_now
from packages.core.passwords import verify_and_upgrade
from packages.core.repositories.identities import IdentityRepository
from packages.core.repositories.sessions_auth import WebSessionRepository

SESSION_COOKIE_NAME = "agora_session"
CSRF_COOKIE_NAME = "agora_csrf"
SESSION_MAX_AGE = timedelta(hours=12)
SESSION_IDLE_TIMEOUT = timedelta(minutes=30)
REAUTH_WINDOW = timedelta(minutes=5)

LOGIN_RATE_LIMIT = 5
LOGIN_RATE_WINDOW_SECONDS = 60
REAUTH_RATE_LIMIT = 10
REAUTH_RATE_WINDOW_SECONDS = 60

_WEB_SESSION_CREDENTIAL_KIND = "web_session"


class SessionAuthError(ValueError):
    def __init__(self, *, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class LoginResult:
    user: UserModel
    session_token: str
    csrf_token: str
    session_id: str
    expires_at: datetime


class InMemoryRateLimiter:
    """Per-key sliding-window limiter (per process; PR2 may move it to Redis)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: dict[str, list[float]] = {}

    def allow(self, *, key: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        with self._lock:
            events = [ts for ts in self._events.get(key, []) if now - ts < window_seconds]
            if len(events) >= limit:
                self._events[key] = events
                return False
            events.append(now)
            self._events[key] = events
            return True

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


rate_limiter = InMemoryRateLimiter()


def login(session: Session, *, username: str, password: str, source: str) -> LoginResult:
    key = f"login:{username}:{source}"
    if not rate_limiter.allow(key=key, limit=LOGIN_RATE_LIMIT, window_seconds=LOGIN_RATE_WINDOW_SECONDS):
        raise SessionAuthError(
            code="LOGIN_RATE_LIMITED",
            message="Too many login attempts; try again later",
        )
    repo = IdentityRepository(session)
    user = _find_user_by_username(repo, username)
    if user is None or user.status != "active":
        raise SessionAuthError(code="INVALID_CREDENTIALS", message="Invalid username or password")
    ok, upgraded_hash = verify_and_upgrade(password, user.password_hash)
    if not ok:
        raise SessionAuthError(code="INVALID_CREDENTIALS", message="Invalid username or password")
    if upgraded_hash is not None:
        user.password_hash = upgraded_hash
        session.flush()

    session_token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    now = utc_now()
    record = WebSessionRepository(session).create(
        user_id=user.id,
        org_id=user.org_id,
        token_hash=hash_token(session_token),
        csrf_secret_hash=hash_token(csrf_token),
        expires_at=now + SESSION_MAX_AGE,
        idle_expires_at=now + SESSION_IDLE_TIMEOUT,
        now=now,
    )
    return LoginResult(
        user=user,
        session_token=session_token,
        csrf_token=csrf_token,
        session_id=record.id,
        expires_at=record.expires_at,
    )


def resolve_session_principal(
    session: Session,
    *,
    session_token: str | None,
    now: datetime | None = None,
) -> Principal | None:
    """Resolve an active web session to a human principal, sliding the idle window."""
    if not session_token:
        return None
    current = now or utc_now()
    record = WebSessionRepository(session).get_active_by_token_hash(hash_token(session_token), now=current)
    if record is None:
        return None
    user = IdentityRepository(session).get_user(record.user_id)
    if user is None or user.status != "active":
        WebSessionRepository(session).revoke(record, at=current)
        return None
    WebSessionRepository(session).touch(record, now=current, idle_expires_at=current + SESSION_IDLE_TIMEOUT)
    return _principal_from_session(record, user)


def validate_csrf(record: WebSessionModel, csrf_token: str | None) -> bool:
    if not csrf_token:
        return False
    return hash_token(csrf_token) == record.csrf_secret_hash


def reauthenticate(
    session: Session,
    *,
    principal: Principal,
    password: str,
    source: str,
) -> None:
    key = f"reauth:{principal.user_id}:{source}"
    if not rate_limiter.allow(key=key, limit=REAUTH_RATE_LIMIT, window_seconds=REAUTH_RATE_WINDOW_SECONDS):
        raise SessionAuthError(
            code="REAUTH_RATE_LIMITED",
            message="Too many reauthentication attempts; try again later",
        )
    repo = IdentityRepository(session)
    user = repo.get_user(principal.user_id)
    if user is None or user.status != "active":
        raise SessionAuthError(code="INVALID_CREDENTIALS", message="Invalid password")
    ok, _upgraded = verify_and_upgrade(password, user.password_hash)
    if not ok:
        raise SessionAuthError(code="INVALID_CREDENTIALS", message="Invalid password")
    # mark every live session of this user as reauthenticated for the window
    records = _live_sessions_for_user(session, user.id)
    now = utc_now()
    for record in records:
        WebSessionRepository(session).mark_reauthenticated(record, reauth_expires_at=now + REAUTH_WINDOW)


def _live_sessions_for_user(session: Session, user_id: str) -> list[WebSessionModel]:
    statement = select(WebSessionModel).where(
        WebSessionModel.user_id == user_id,
        WebSessionModel.revoked_at.is_(None),
    )
    return list(session.scalars(statement).all())


def _find_user_by_username(repo: IdentityRepository, username: str) -> UserModel | None:
    statement = (
        select(UserModel)
        .where(UserModel.username == username)
        .order_by(UserModel.created_at.asc())
        .limit(1)
    )
    return repo.session.scalars(statement).first()


def _principal_from_session(record: WebSessionModel, user: UserModel) -> Principal:
    return Principal(
        org_id=user.org_id,
        user_id=user.id,
        credential_id=record.id,
        credential_kind=_WEB_SESSION_CREDENTIAL_KIND,
        token_prefix="web-session",
    )
