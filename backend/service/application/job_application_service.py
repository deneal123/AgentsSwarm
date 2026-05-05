from __future__ import annotations

import os
from uuid import UUID

from fastapi import HTTPException, status

from service.infrastructure.messaging.celery_app import celery_app
from service.models.auth_models import AuthProfile
from service.presentation.routers.jobs_api.schemas import StartJobRequest, TaskStatusResponse
from service.services.job_service import JobService

USE_CELERY = os.getenv("USE_CELERY", "").strip().lower() in {"1", "true", "yes", "on"}


class JobApplicationService:
    def __init__(self, job_service: JobService) -> None:
        self.job_service = job_service

    async def start_job(self, profile: AuthProfile, request_body: StartJobRequest):
        return await self.job_service.create_job(profile.user_id, request_body)

    async def fetch_result(self, profile: AuthProfile, job_id: str):
        return await self.job_service.fetch_job_result(profile.user_id, UUID(job_id))

    async def get_task_status(self, task_id: str) -> TaskStatusResponse:
        if not USE_CELERY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Celery task tracking is not enabled",
            )
        from celery.result import AsyncResult

        result = AsyncResult(task_id, app=celery_app)
        response = TaskStatusResponse(
            task_id=task_id,
            state=result.state,
            progress=None,
            status=None,
            result=None,
            error=None,
        )

        if result.state == "PENDING":
            response.status = "Task is waiting to be executed"
        elif result.state == "STARTED":
            response.status = "Task has started"
        else:
            meta = result.info or {}
            try:
                response.progress = int(meta.get("progress", 0))
            except Exception:
                response.progress = None
            response.status = meta.get("status", f"State: {result.state}")

        if result.state == "SUCCESS":
            response.status = "Task completed successfully"
            response.result = result.result if isinstance(result.result, dict) else None
            response.progress = 100
        elif result.state == "FAILURE":
            response.status = "Task failed"
            response.error = str(result.result) if result.result else "Unknown error"
        elif result.state == "REVOKED":
            response.status = "Task was cancelled"

        return response

    async def cancel_task(self, task_id: str) -> dict:
        if not USE_CELERY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Celery task management is not enabled",
            )
        from celery.result import AsyncResult

        result = AsyncResult(task_id, app=celery_app)
        result.revoke(terminate=True)
        return {"task_id": task_id, "status": "cancelled"}
