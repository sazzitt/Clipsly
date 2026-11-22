from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from backend.app.core.config import settings
from backend.app.core.logging import logger


class LocalhostSecurityMiddleware(BaseHTTPMiddleware):
    """Enforces sovereign local-only loopback isolation.
    Rejects requests containing external Host headers or originating from remote IP addresses.
    """
    ALLOWED_HOSTS = set(settings.ALLOWED_HOSTS) | {"testserver", "testserver:80", "127.0.0.1", "localhost"}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        host = request.headers.get("host", "").split(":")[0]

        # Verify host header matches localhost / loopback
        if host and host not in {"127.0.0.1", "localhost", "testserver"}:
            logger.warning("Blocked non-local request with forbidden Host header: '%s'", host)
            return JSONResponse(
                status_code=403,
                content={
                    "error_code": "FORBIDDEN_HOST",
                    "detail": "Clipsly is configured strictly for local workstation loopback access (127.0.0.1).",
                    "error": {
                        "code": "FORBIDDEN_HOST",
                        "message": "Clipsly is configured strictly for local workstation loopback access (127.0.0.1)."
                    }
                }
            )

        # Verify client IP is loopback
        client_host = request.client.host if request.client else None
        if client_host and client_host not in {"127.0.0.1", "::1", "testclient"}:
            logger.warning("Blocked remote request from IP: '%s'", client_host)
            return JSONResponse(
                status_code=403,
                content={
                    "error_code": "REMOTE_ACCESS_FORBIDDEN",
                    "detail": "Remote network access is forbidden. Clipsly only accepts loopback connections.",
                    "error": {
                        "code": "REMOTE_ACCESS_FORBIDDEN",
                        "message": "Remote network access is forbidden. Clipsly only accepts loopback connections."
                    }
                }
            )

        return await call_next(request)
