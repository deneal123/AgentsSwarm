import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from service.shared.error_handling.error_mapper import map_exception_to_error_response, map_exception_to_status
from service.shared.repositories.exceptions import RepositoryError

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    logger.warning(
        "HTTP Exception occurred: %s - %s for request: %s %s",
        exc.status_code,
        exc.detail,
        request.method,
        request.url,
    )
    payload = map_exception_to_error_response(exc)
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.warning(
        "Validation error occurred for request: %s %s - %s",
        request.method,
        request.url,
        exc.errors(),
    )
    errors = []
    for error in exc.errors():
        item = {
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        if "input" in error:
            item["input"] = error["input"]
        errors.append(item)
    exception = HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "code": "validation_error",
            "message": "Validation error",
            "type": "ValidationError",
            "details": errors,
        },
    )
    payload = map_exception_to_error_response(exception)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=payload.model_dump()
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception occurred for request: %s %s", request.method, request.url)
    status_code = map_exception_to_status(exc)
    payload = map_exception_to_error_response(exc)
    return JSONResponse(status_code=status_code, content=payload.model_dump())


async def repository_exception_handler(request: Request, exc: RepositoryError) -> JSONResponse:
    status_code = map_exception_to_status(exc)
    logger.warning(
        "%s occurred for request %s %s: %s",
        exc.__class__.__name__,
        request.method,
        request.url,
        exc,
    )
    payload = map_exception_to_error_response(exc)
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def setup_exception_handlers(app: FastAPI):
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,
    )  # type: ignore[arg-type]
    app.add_exception_handler(RepositoryError, repository_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, general_exception_handler)  # type: ignore[arg-type]
