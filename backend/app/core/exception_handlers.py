from typing import Any, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.exceptions import AppException
from backend.app.core.logging import logger


def build_error_response(status_code: int, error_code: str, detail: str, details: Optional[Any] = None) -> JSONResponse:
    """Builds a standardized error envelope matching both ClipslyApiError and docs/05-API.md."""
    content = {
        "error_code": error_code,
        "detail": detail,
        "error": {
            "code": error_code,
            "message": detail,
            "details": details,
        }
    }
    return JSONResponse(status_code=status_code, content=content)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    req_id = getattr(request.state, "request_id", "N/A")
    logger.warning("[%s] AppException %d: %s (%s)", req_id, exc.status_code, exc.detail, exc.error_code)
    return build_error_response(exc.status_code, exc.error_code, exc.detail, exc.details)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    req_id = getattr(request.state, "request_id", "N/A")
    errors = exc.errors()
    detail = "Request validation failed."
    if errors:
        first = errors[0]
        field = " -> ".join(str(loc) for loc in first.get("loc", []))
        msg = first.get("msg", "invalid")
        detail = f"Validation failed at '{field}': {msg}"
    logger.warning("[%s] RequestValidationError 422: %s", req_id, detail)
    return build_error_response(status.HTTP_422_UNPROCESSABLE_CONTENT, "VALIDATION_ERROR", detail, errors)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    req_id = getattr(request.state, "request_id", "N/A")
    error_code = "HTTP_ERROR"
    if exc.status_code == 404:
        error_code = "RESOURCE_NOT_FOUND"
    elif exc.status_code == 405:
        error_code = "METHOD_NOT_ALLOWED"
    elif exc.status_code == 408:
        error_code = "REQUEST_TIMEOUT"

    detail = str(exc.detail) if exc.detail else "An HTTP error occurred."
    logger.warning("[%s] StarletteHTTPException %d: %s", req_id, exc.status_code, detail)
    return build_error_response(exc.status_code, error_code, detail)


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    req_id = getattr(request.state, "request_id", "N/A")
    logger.error("[%s] Database error: %s", req_id, str(exc), exc_info=True)
    return build_error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "DATABASE_ERROR",
        "A database transaction error occurred. The operation has been rolled back."
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    req_id = getattr(request.state, "request_id", "N/A")
    logger.error("[%s] Unhandled server exception: %s", req_id, str(exc), exc_info=True)
    return build_error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "INTERNAL_SERVER_ERROR",
        "An unexpected internal error occurred on the workstation."
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Registers global exception handlers on the FastAPI application."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
