import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status

from service import container
from service.application.job_application_service import JobApplicationService
from service.models.auth_models import AuthProfile
from service.presentation.dependencies.auth_checker import check_auth
from service.presentation.routers.jobs_api.schemas import (
    JobResponse,
    StartJobRequest,
    TaskStatusResponse,
)
from service.services.jobs.application.job_service import JobService

logger = logging.getLogger(__name__)
jobs_router = APIRouter(prefix="/api/jobs/v1")


def get_job_application_service(
    service: Annotated["JobService", Depends(container.get_job_service)],
) -> JobApplicationService:
    return JobApplicationService(job_service=service)


@jobs_router.post(
    "/start",
    summary="Start a modify job",
    response_model=JobResponse,
)
async def start_processing_job(
    profile: Annotated[AuthProfile, Depends(check_auth)],
    request_body: Annotated[StartJobRequest, Body()],
    service: Annotated[JobApplicationService, Depends(get_job_application_service)],
) -> JobResponse:
    result = await service.start_job(profile, request_body)
    return JobResponse(
        job_id=result.job_id,
        status=result.status,
        result_file_url=result.result_file_url,
        wait_time_sec=result.wait_time_sec,
        celery_task_id=result.celery_task_id,
    )


@jobs_router.get(
    "/result/{job_id}",
    summary="Fetch the result of a modify job",
    response_model=JobResponse,
)
async def fetch_result(
    profile: Annotated[AuthProfile, Depends(check_auth)],
    job_id: Annotated[str, Path(...)],
    service: Annotated[JobApplicationService, Depends(get_job_application_service)],
) -> JobResponse:
    result = await service.fetch_result(profile, job_id)
    return JobResponse(
        job_id=result.job_id,
        status=result.status,
        result_file_url=result.result_file_url,
        wait_time_sec=result.wait_time_sec,
        celery_task_id=result.celery_task_id,
    )


@jobs_router.get(
    "/task/{task_id}/status",
    summary="Get Celery task status",
    response_model=TaskStatusResponse,
)
async def get_task_status(
    profile: Annotated[AuthProfile, Depends(check_auth)],
    task_id: Annotated[str, Path(..., description="Celery task ID")],
    service: Annotated[JobApplicationService, Depends(get_job_application_service)],
) -> TaskStatusResponse:
    try:
        return await service.get_task_status(task_id)
    except Exception as exc:
        logger.exception("Failed to get task status for %s: %s", task_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {exc}",
        )


@jobs_router.post(
    "/task/{task_id}/cancel",
    summary="Cancel a Celery task",
)
async def cancel_task(
    profile: Annotated[AuthProfile, Depends(check_auth)],
    task_id: Annotated[str, Path(..., description="Celery task ID")],
    service: Annotated[JobApplicationService, Depends(get_job_application_service)],
) -> dict:
    try:
        result = await service.cancel_task(task_id)
        logger.info("Task %s cancelled by user %s", task_id, profile.user_id)
        return result
    except Exception as exc:
        logger.exception("Failed to cancel task %s: %s", task_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel task: {exc}",
        )
