from typing import Any, Optional
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class SentinelException(Exception):
    """Base exception for all domain errors."""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 400, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class AuthenticationError(SentinelException):
    def __init__(self, message: str = "Invalid credentials or expired session", details: Optional[Any] = None):
        super().__init__(message=message, code="AUTHENTICATION_FAILED", status_code=status.HTTP_401_UNAUTHORIZED, details=details)


class PermissionDeniedError(SentinelException):
    def __init__(self, message: str = "Insufficient statutory authority for this action", details: Optional[Any] = None):
        super().__init__(message=message, code="PERMISSION_DENIED", status_code=status.HTTP_403_FORBIDDEN, details=details)


class NotFoundError(SentinelException):
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            message=f"{resource} identified by '{identifier}' was not found.",
            code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )


class ConflictError(SentinelException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message=message, code="STATE_CONFLICT", status_code=status.HTTP_409_CONFLICT, details=details)


class ValidationError(SentinelException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details=details,
        )


class WorkflowTransitionError(SentinelException):
    def __init__(self, from_state: str, to_state: str, reason: str):
        super().__init__(
            message=f"Invalid statutory transition from '{from_state}' to '{to_state}': {reason}",
            code="INVALID_WORKFLOW_TRANSITION",
            status_code=422,
            details={"from_state": from_state, "to_state": to_state, "reason": reason}
        )


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(SentinelException)
    async def sentinel_exception_handler(request: Request, exc: SentinelException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "code": "VALIDATION_ERROR",
                "message": "Request payload failed schema validation",
                "details": exc.errors(),
            }
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        import traceback
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred during statutory processing.",
                "details": str(exc) if app.debug else None,
            }
        )
