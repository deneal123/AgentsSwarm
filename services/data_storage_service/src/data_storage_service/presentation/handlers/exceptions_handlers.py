import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from service.repositories.exceptions import (
    RepositoryError,
    RepositoryIntegrityError,
    RepositoryMultipleResultsError,
    RepositoryNotFoundError,
    RepositoryOperationalError,
)

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    logger.warning(
        f"HTTP Exception occurred: {exc.status_code} - {exc.detail} "
        f"for request: {request.method} {request.url}"
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "HTTPException",
            }
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.warning(
        f"Validation error occurred for request: {request.method} {request.url} - {exc.errors()}"
    )

    errors = []
    for error in exc.errors():
        error_detail = {
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        if "input" in error:
            error_detail["input"] = error["input"]
        errors.append(error_detail)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(
            {
                "error": {
                    "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "message": "Validation error",
                    "type": "ValidationError",
                    "details": errors,
                }
            }
        ),
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"Unhandled exception occurred for request: {request.method} {request.url}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "type": "InternalServerError",
            }
        },
    )


async def pydantic_validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle Pydantic v2 ValidationError."""
    logger.warning(
        f"Pydantic validation error occurred for request: {request.method} {request.url} - {exc.errors()}"
    )

    errors = []
    for error in exc.errors():
        error_detail = {
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        if "input" in error:
            error_detail["input"] = error["input"]
        errors.append(error_detail)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(
            {
                "error": {
                    "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "message": "Validation error",
                    "type": "ValidationError",
                    "details": errors,
                }
            }
        ),
    )


async def repository_exception_handler(request: Request, exc: RepositoryError) -> JSONResponse:
    if isinstance(exc, RepositoryNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
        error_type = "RepositoryNotFoundError"
    elif isinstance(exc, RepositoryIntegrityError):
        status_code = status.HTTP_400_BAD_REQUEST
        error_type = "RepositoryIntegrityError"
    elif isinstance(exc, RepositoryMultipleResultsError):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_type = "RepositoryMultipleResultsError"
    elif isinstance(exc, RepositoryOperationalError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        error_type = "RepositoryOperationalError"
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_type = exc.__class__.__name__

    logger.warning(
        "%s occurred for request %s %s: %s",
        error_type,
        request.method,
        request.url,
        exc,
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": status_code,
                "message": str(exc),
                "type": error_type,
            }
        },
    )


def setup_exception_handlers(app: FastAPI):
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ValidationError, pydantic_validation_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RepositoryError, repository_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, general_exception_handler)  # type: ignore[arg-type]
