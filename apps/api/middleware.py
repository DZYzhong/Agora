from uuid import uuid4

from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from apps.api.dependencies import get_runtime_policy


REQUEST_ID_HEADER = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


class HideProductionLocalInitializationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if _is_legacy_local_initialization_path(request.url.path):
            if get_runtime_policy().environment == "production":
                return JSONResponse({"detail": "Not Found"}, status_code=404)
        return await call_next(request)


def _is_legacy_local_initialization_path(path: str) -> bool:
    parts = [part for part in path.split("/") if part]
    if len(parts) < 3 or parts[0] != "projects":
        return False
    if len(parts) == 3 and parts[2] == "initialize-local":
        return True
    return len(parts) == 5 and parts[2] == "initialization-jobs" and parts[4] == "retry"
