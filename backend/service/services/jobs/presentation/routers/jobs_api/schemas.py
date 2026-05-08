from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from service.models.key_value import ProcessingStatus, ServiceType


class StartJobRequest(BaseModel):
    file_id: Annotated[
        UUID | None, Field(None, description="Legacy file identifier to process (dataset id)")
    ]
    target_column: Annotated[
        str | None, Field(None, description="Optional target column name for training")
    ]
    type: Annotated[ServiceType, Field(..., description="Type of service to apply")]

    @model_validator(mode="after")
    def _ensure_source(self) -> "StartJobRequest":
        if not self.file_id and not getattr(self, "dataset_id", None):
            raise ValueError("Either dataset_id or file_id must be provided")
        return self


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


class TaskStatusResponse(BaseModel):
    task_id: Annotated[str, Field(..., description="Celery task identifier")]
    state: Annotated[
        str, Field(..., description="Task state: PENDING, STARTED, TRAINING, SUCCESS, FAILURE")
    ]
    progress: Annotated[int | None, Field(None, description="Progress percentage (0-100)")]
    status: Annotated[str | None, Field(None, description="Human-readable status message")]
    result: Annotated[dict[str, Any] | None, Field(None, description="Task result if completed")]
    error: Annotated[str | None, Field(None, description="Error message if failed")]
