from uuid import uuid4

from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from apps.api.auth_session import SESSION_COOKIE_NAME
from apps.api.dependencies import get_engine, get_runtime_policy
from packages.core.auth import hash_token
from packages.core.models import utc_now
from packages.core.repositories.sessions_auth import WebSessionRepository
from packages.core.upload_policy import MAX_JSON_BODY_BYTES, redact_sensitive


REQUEST_ID_HEADER = "X-Request-ID"
CSRF_HEADER = "X-CSRF-Token"
STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


class BodyLimitMiddleware(BaseHTTPMiddleware):
    """Reject oversized request bodies with a stable error before parsing."""

    async def dispatch(self, request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > MAX_JSON_BODY_BYTES:
            return JSONResponse(
                {
                    "detail": {
                        "code": "PAYLOAD_TOO_LARGE",
                        "message": f"Request body exceeds the {MAX_JSON_BODY_BYTES} byte limit",
                    }
                },
                status_code=413,
            )
        return await call_next(request)


class CsrfProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF + Origin enforcement for cookie-authenticated state changes.

    Bearer-token (Agent/CI) requests are not browser-cookie flows and are not
    subject to CSRF. Requests that carry the session cookie must present a
    matching `X-CSRF-Token` header (double-submit cookie) and an allowed
    `Origin` before any state change is processed.
    """

    async def dispatch(self, request, call_next):
        if (
            request.method in STATE_CHANGING_METHODS
            and request.cookies.get(SESSION_COOKIE_NAME)
            and not request.headers.get("Authorization")
        ):
            if not _origin_allowed(request):
                return JSONResponse(
                    {"detail": {"code": "CSRF_ORIGIN_REJECTED", "message": "Cross-origin request rejected"}},
                    status_code=403,
                )
            csrf_token = request.headers.get(CSRF_HEADER)
            if not csrf_token or not _csrf_matches_session(request.cookies.get(SESSION_COOKIE_NAME), csrf_token):
                return JSONResponse(
                    {"detail": {"code": "CSRF_TOKEN_REQUIRED", "message": "Valid CSRF token required"}},
                    status_code=403,
                )
        return await call_next(request)


def _origin_allowed(request) -> bool:
    origin = request.headers.get("Origin")
    if not origin:
        return False
    return origin in _allowed_origins(request)


def _allowed_origins(request) -> set[str]:
    import os

    configured = os.environ.get("AGORA_ALLOWED_ORIGINS", "")
    origins = {item.strip() for item in configured.split(",") if item.strip()}
    scheme = request.url.scheme
    host = request.headers.get("Host") or request.url.netloc
    if host:
        origins.add(f"{scheme}://{host}")
    # localhost development origins are accepted so the Web app can run on a
    # different local port from the API during local development.
    origins.update(
        {
            "http://127.0.0.1:3000",
            "http://127.0.0.1:13100",
            "http://127.0.0.1:13120",
            "http://127.0.0.1:13140",
            "http://localhost:3000",
        }
    )
    return origins


def _csrf_matches_session(session_token: str, csrf_token: str) -> bool:
    from sqlalchemy.orm import sessionmaker

    session = sessionmaker(bind=get_engine())()
    try:
        record = WebSessionRepository(session).get_active_by_token_hash(hash_token(session_token), now=utc_now())
        if record is None:
            return False
        return hash_token(csrf_token) == record.csrf_secret_hash
    finally:
        session.close()


class HideProductionLocalInitializationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if _is_legacy_local_initialization_path(request.url.path):
            if get_runtime_policy().environment == "production":
                return JSONResponse({"detail": "Not Found"}, status_code=404)
        return await call_next(request)


def stable_error_response(exc: Exception) -> JSONResponse:
    """Convert an unhandled exception into a stable, redacted 500 response."""
    message = redact_sensitive(str(exc))
    return JSONResponse(
        {
            "detail": {
                "code": "INTERNAL_ERROR",
                "message": "Internal server error",
                "redacted_reason": message[:500] if message else None,
            }
        },
        status_code=500,
    )


def _is_legacy_local_initialization_path(path: str) -> bool:
    parts = [part for part in path.split("/") if part]
    if len(parts) < 3 or parts[0] != "projects":
        return False
    if len(parts) == 3 and parts[2] == "initialize-local":
        return True
    return len(parts) == 5 and parts[2] == "initialization-jobs" and parts[4] == "retry"
