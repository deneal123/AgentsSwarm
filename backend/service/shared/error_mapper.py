from __future__ import annotations

from fastapi import HTTPException, status

from service.repositories.exceptions import (
    RepositoryError,
    RepositoryIntegrityError,
    RepositoryMultipleResultsError,
    RepositoryNotFoundError,
    RepositoryOperationalError,
)
from service.shared.context import get_correlation_id, get_trace_id
from service.shared.dto import AppErrorResponse, ErrorDetail
from service.shared.exceptions import ApplicationError


def map_exception_to_status(error: Exception) -> int:
    if isinstance(error, ApplicationError):
        return error.status_code
    if isinstance(error, RepositoryNotFoundError):
        return status.HTTP_404_NOT_FOUND
    if isinstance(error, RepositoryIntegrityError):
        return status.HTTP_400_BAD_REQUEST
    if isinstance(error, RepositoryMultipleResultsError):
        return status.HTTP_500_INTERNAL_SERVER_ERROR
    if isinstance(error, RepositoryOperationalError):
        return status.HTTP_503_SERVICE_UNAVAILABLE
    if isinstance(error, RepositoryError):
        return status.HTTP_500_INTERNAL_SERVER_ERROR
    if isinstance(error, HTTPException):
        return error.status_code
    return status.HTTP_500_INTERNAL_SERVER_ERROR


def map_exception_to_error_response(error: Exception, default_message: str = "Internal server error") -> AppErrorResponse:
    if isinstance(error, HTTPException):
        detail = error.detail if isinstance(error.detail, dict) else {"message": str(error.detail)}
        message = detail.get("message", default_message)
        code = str(detail.get("code", "http_error"))
        error_type = str(detail.get("type", "HTTPException"))
        details = detail.get("details")
    elif isinstance(error, ApplicationError):
        message = error.message
        code = error.code
        error_type = error.__class__.__name__
        details = error.details or None
    else:
        message = str(error) if str(error) else default_message
        code = getattr(error, "code", error.__class__.__name__.lower())
        error_type = error.__class__.__name__
        details = None

    return AppErrorResponse(
        error=ErrorDetail(
            code=str(code),
            message=message,
            type=error_type,
            details=details,
            correlation_id=get_correlation_id(),
            trace_id=get_trace_id(),
        )
    )
