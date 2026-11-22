from typing import Any, Optional


class AppException(Exception):
    """Base application exception for Clipsly with structured error coding."""
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str = "INTERNAL_SERVER_ERROR",
        details: Optional[Any] = None
    ):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code
        self.details = details


class NotFoundError(AppException):
    def __init__(self, detail: str = "The requested resource was not found.", details: Optional[Any] = None):
        super().__init__(
            status_code=404,
            detail=detail,
            error_code="RESOURCE_NOT_FOUND",
            details=details
        )


class ValidationError(AppException):
    def __init__(self, detail: str = "Input validation failed.", details: Optional[Any] = None):
        super().__init__(
            status_code=422,
            detail=detail,
            error_code="VALIDATION_ERROR",
            details=details
        )


class ConflictError(AppException):
    def __init__(self, detail: str = "A resource conflict occurred.", details: Optional[Any] = None):
        super().__init__(
            status_code=409,
            detail=detail,
            error_code="CONFLICT",
            details=details
        )


class JobAlreadyRunningError(AppException):
    def __init__(self, detail: str = "Another heavy processing job is currently running on the GPU."):
        super().__init__(
            status_code=409,
            detail=detail,
            error_code="JOB_ALREADY_RUNNING"
        )


class InsufficientStorageError(AppException):
    def __init__(self, detail: str = "Insufficient local SSD storage. At least 10GB free space required."):
        super().__init__(
            status_code=507,
            detail=detail,
            error_code="INSUFFICIENT_STORAGE"
        )


class NotImplementedFeatureError(AppException):
    def __init__(self, detail: str = "This feature is planned for activation in a subsequent phase."):
        super().__init__(
            status_code=501,
            detail=detail,
            error_code="NOT_IMPLEMENTED"
        )
