from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from service.models.key_value import ProcessingStatus
from service.services.jobs.application.dto import StartJobRequest, TaskStatusResponse


class JobResponse(BaseModel):
    job_id: Annotated[UUID, Field(..., description="Unique job identifier")]
    status: Annotated[ProcessingStatus, Field(..., description="Current job processing status")]
    result_file_url: Annotated[
        str | None, Field(None, description="URL to download the processed file result")
    ]
    wait_time_sec: Annotated[
        int,
        Field(..., description="Elapsed time in seconds for PROCESSING jobs, or default wait time"),
    ]
    celery_task_id: Annotated[
        str | None, Field(None, description="Celery task ID for async tracking")
    ]


__all__ = [
    "StartJobRequest",
    "TaskStatusResponse",
    "JobResponse",
]
