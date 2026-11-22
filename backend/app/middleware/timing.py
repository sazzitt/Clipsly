import time
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from backend.app.core.logging import logger


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Measures request execution time and logs structured HTTP metrics."""
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()
        request_id = getattr(request.state, "request_id", "N/A")

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Process-Time-Ms"] = str(duration_ms)

        # Do not flood logs with health poll spam unless status is non-200
        path = request.url.path
        if path == "/api/v1/system/health" and response.status_code == 200:
            logger.debug("[%s] %s %s -> %d (%sms)", request_id, request.method, path, response.status_code, duration_ms)
        else:
            logger.info("[%s] %s %s -> %d (%sms)", request_id, request.method, path, response.status_code, duration_ms)

        return response
