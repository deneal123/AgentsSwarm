"""Unified task orchestration service for Pushi platform.

This service is the single entry point for all background task operations.
It handles:
- Task creation in database
- Concurrency management (thread allocation)
- File handling (configs, datasets)
- Celery task dispatch
- Queue position tracking for pipeline tasks
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import HTTPException, status
from service.models.db.task_models import Task
from service.models.enums import FileType, TaskStatus, TaskType
from service.repositories.file_repository import FileRepository
from service.repositories.pipeline_slot_repository import PipelineSlotRepository
from service.repositories.task_concurrency_repository import TaskConcurrencyRepository
from service.repositories.task_repository import TaskRepository
from service.services.base_service import BaseService
from service.services.file_saver_service import FileSaverService
from service.services.pushi_service import PlaygroundService, PipelineService
from service.settings import TaskConfig

if TYPE_CHECKING:
    from service.infrastructure.messaging.app.celery_app import Celery

logger = logging.getLogger(__name__)


class ConcurrencyLimitExceededError(Exception):
    """Raised when task cannot be started due to concurrency limits."""
    pass


class PipelineSlotFullError(Exception):
    """Raised when user already has an active pipeline."""
    pass


class TaskOrchestratorService(BaseService[TaskRepository]):
    """Unified service for task orchestration with concurrency control.
    
    This service replaces CommunicationService for new tasks and provides
    a single interface for all background operations.
    """

    # Celery task paths for dispatch
    CELERY_TASKS = {
        TaskType.PLAYGROUND_SINGLE: "service.infrastructure.messaging.tasks.playground_tasks.process_playground_single",
        TaskType.PLAYGROUND_BATCH: "service.infrastructure.messaging.tasks.playground_tasks.process_playground_batch",
        TaskType.PIPELINE: "service.infrastructure.messaging.tasks.pipeline_tasks.process_pipeline",
        TaskType.FILE_CONFIG_UPLOAD: "service.infrastructure.messaging.tasks.file_tasks.process_config_upload",
        TaskType.FILE_DATASET_UPLOAD: "service.infrastructure.messaging.tasks.file_tasks.process_dataset_upload",
        TaskType.MAINTENANCE: "service.infrastructure.messaging.tasks.maintenance_tasks.process_maintenance",
    }

    # Queue routing
    QUEUE_MAP = {
        TaskType.PLAYGROUND_SINGLE: "playground",
        TaskType.PLAYGROUND_BATCH: "playground",
        TaskType.PIPELINE: "pipeline",
        TaskType.FILE_CONFIG_UPLOAD: "maintenance",
        TaskType.FILE_DATASET_UPLOAD: "maintenance",
        TaskType.MAINTENANCE: "maintenance",
    }

    def __init__(
        self,
        config: TaskConfig,
        repository: TaskRepository,
        concurrency_repository: TaskConcurrencyRepository,
        queue_repository: PipelineSlotRepository,
        file_repository: FileRepository,
        file_saver_service: FileSaverService | None = None,
        playground_service: PlaygroundService | None = None,
        pipeline_service: PipelineService | None = None,
    ) -> None:
        super().__init__(repository)
        self.config = config
        self.concurrency_repo = concurrency_repository
        self.queue_repo = queue_repository
        self.file_repo = file_repository
        self.file_saver = file_saver_service
        self.playground_service = playground_service
        self.pipeline_service = pipeline_service

    # ========================================================================
    # PUBLIC API: Playground Tasks
    # ========================================================================

    async def create_playground_task(
        self,
        communications: list[dict[str, Any]],
        config: dict[str, Any],
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
    ) -> Task:
        """Create and dispatch a playground task (single or batch).
        
        Args:
            communications: List of communication dicts with 'text', 'type', etc.
            config: Task configuration (batch_size, max_parallel_batches, include_risk_ids, etc.)
            user_id: User ID if authenticated
            guest_session_id: Guest session ID if not authenticated
            
        Returns:
            Created Task object
            
        Raises:
            HTTPException: If neither user_id nor guest_session_id provided
            ConcurrencyLimitExceededError: If not enough threads available
        """
        self._validate_ownership(user_id, guest_session_id)
        
        # Determine task type based on communication count
        task_type = (
            TaskType.PLAYGROUND_SINGLE 
            if len(communications) == 1 
            else TaskType.PLAYGROUND_BATCH
        )
        
        # Validate and normalize config
        normalized_config = self._normalize_config(config)
        threads_needed = normalized_config.get("max_parallel_batches", 1)
        
        # Validate against project limit
        if threads_needed > self.config.max_project_threads:
            raise ConcurrencyLimitExceededError(
                f"Requested {threads_needed} threads exceeds project maximum "
                f"of {self.config.max_project_threads}"
            )

        # Check concurrency before creating task
        can_start, current_usage = await self._can_acquire_threads(threads_needed)
        
        # Create task
        task = await self.repository.create_task(
            task_type=task_type,
            status=TaskStatus.PENDING if not can_start else TaskStatus.NEW,
            payload={"communications": communications},
            config=normalized_config,
            user_id=user_id,
            guest_session_id=guest_session_id,
        )
        
        logger.info(
            f"Created {task_type.value} task {task.id} for user={user_id or guest_session_id}, "
            f"communications={len(communications)}, threads_needed={threads_needed}"
        )
        
        if can_start:
            # Reserve threads and dispatch immediately
            await self._acquire_threads(task.id, task_type, threads_needed)
            await self._dispatch_task(task)
        else:
            logger.info(
                f"Task {task.id} queued due to concurrency limits "
                f"(current_usage={current_usage}, needed={threads_needed}, "
                f"max={self.config.max_project_threads})"
            )

        return task

    # ========================================================================
    # PUBLIC API: Pipeline Tasks
    # ========================================================================

    async def create_pipeline_task(
        self,
        dataset_file_id: UUID,
        config: dict[str, Any],
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
    ) -> Task:
        """Create and queue a pipeline task.
        
        Pipeline tasks respect max_parallel_batches from config.
        Task waits until required threads are available.
        
        Args:
            dataset_file_id: ID of uploaded XLSX dataset file
            config: Pipeline configuration (with max_parallel_batches)
            user_id: User ID if authenticated
            guest_session_id: Guest session ID if not authenticated
            
        Returns:
            Created Task object
            
        Raises:
            HTTPException: If ownership not provided
            ConcurrencyLimitExceededError: If requested threads > max_project_threads
        """
        self._validate_ownership(user_id, guest_session_id)
        
        # Normalize config
        normalized_config = self._normalize_config(config)
        threads_needed = normalized_config.get("max_parallel_batches", 1)
        
        # Validate against project limit
        if threads_needed > self.config.max_project_threads:
            raise ConcurrencyLimitExceededError(
                f"Requested {threads_needed} threads exceeds project maximum "
                f"of {self.config.max_project_threads}"
            )

        # Check if can start now
        can_start, current_usage = await self._can_acquire_threads(threads_needed)
        
        # Create task
        task = await self.repository.create_task(
            task_type=TaskType.PIPELINE,
            status=TaskStatus.PENDING if not can_start else TaskStatus.NEW,
            payload={"dataset_file_id": str(dataset_file_id)},
            config=normalized_config,
            user_id=user_id,
            guest_session_id=guest_session_id,
            file_id=dataset_file_id,
        )
        
        logger.info(
            f"Created pipeline task {task.id} for user={user_id or guest_session_id}, "
            f"threads_needed={threads_needed}, can_start={can_start}"
        )
        
        if can_start:
            # Reserve threads and dispatch immediately
            await self._acquire_threads(task.id, TaskType.PIPELINE, threads_needed)
            await self._dispatch_task(task)
        else:
            logger.info(
                f"Pipeline task {task.id} queued due to concurrency limits "
                f"(current_usage={current_usage}, needed={threads_needed}, "
                f"max={self.config.max_project_threads})"
            )
        
        return task

    async def get_pipeline_queue_position(
        self,
        task_id: UUID,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Get queue position for a pipeline task.
        
        Returns:
            Dict with position, estimated_wait, status
        """
        queue_entry = await self.queue_repo.get_queue_entry_by_task_id(task_id)
        if not queue_entry:
            return {"status": "not_found", "position": None}
        
        # If already processing or completed
        if queue_entry.status != "queued":
            return {
                "status": queue_entry.status,
                "position": 0,
                "started_at": queue_entry.started_at,
            }
        
        # Count users ahead in queue
        ahead_count = await self.queue_repo.count_users_ahead(
            user_id=user_id,
            guest_session_id=guest_session_id,
        )
        
        # Estimate wait time (rough estimate: 5 min per pipeline)
        estimated_wait_minutes = ahead_count * 5
        
        return {
            "status": "queued",
            "position": ahead_count + 1,
            "estimated_wait_minutes": estimated_wait_minutes,
            "created_at": queue_entry.created_at,
        }

    # ========================================================================
    # PUBLIC API: File Tasks
    # ========================================================================

    async def create_file_upload_task(
        self,
        file_content: bytes,
        file_name: str,
        file_type: FileType,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
    ) -> Task:
        """Create a task for processing uploaded file.
        
        This handles config files (.yaml, .toml) and dataset files (.xlsx).
        
        Args:
            file_content: Raw file bytes
            file_name: Original file name
            file_type: Type of file (CONFIG or DATASET)
            user_id: User ID if authenticated
            guest_session_id: Guest session ID if not authenticated
            
        Returns:
            Created Task object with associated File record
        """
        self._validate_ownership(user_id, guest_session_id)
        
        # Save file first
        if not self.file_saver:
            raise RuntimeError("FileSaverService not configured")
        
        file_response = await self.file_saver.save(
            file_name=file_name,
            file_content=file_content,
            file_type=file_type,
            user_id=user_id,
            guest_session_id=guest_session_id,
        )
        
        # Determine task type
        task_type = (
            TaskType.FILE_CONFIG_UPLOAD
            if file_type in (FileType.CONFIG, FileType.CONFIG_YAML)
            else TaskType.FILE_DATASET_UPLOAD
        )

        # Create task
        task = await self.repository.create_task(
            task_type=task_type,
            status=TaskStatus.PENDING,
            payload={"original_file_name": file_name},
            file_id=file_response.id,
            user_id=user_id,
            guest_session_id=guest_session_id,
        )
        
        logger.info(
            f"Created {task_type.value} task {task.id} for file {file_name}"
        )
        
        # Dispatch (file tasks use 1 thread)
        await self._dispatch_task(task)
        
        return task

    # ========================================================================
    # PUBLIC API: Task Lifecycle
    # ========================================================================

    async def get_task(self, task_id: UUID) -> Task | None:
        """Get task by ID."""
        return await self.repository.get_task_by_id(task_id)

    async def get_user_tasks(
        self,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
        task_type: TaskType | None = None,
        status: TaskStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        """Get tasks for user with optional filtering."""
        return await self.repository.get_tasks_by_user(
            user_id=user_id,
            guest_session_id=guest_session_id,
            task_type=task_type,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def cancel_task(self, task_id: UUID) -> bool:
        """Cancel a task and release resources."""
        task = await self.repository.get_task_by_id(task_id)
        if not task:
            return False
        
        # Revoke Celery task if dispatched
        if task.celery_task_id:
            celery_app = self._get_celery_app()
            celery_app.control.revoke(task.celery_task_id, terminate=True)
        
        # Release threads if reserved
        await self._release_threads(task_id)
        
        # Update status
        await self.repository.update_task_fields(
            task_id=task_id,
            status=TaskStatus.CANCELLED,
            completed_at=datetime.now(timezone.utc),
            error_message="Cancelled by user",
        )
        
        logger.info(f"Cancelled task {task_id}")
        return True

    async def update_task_artifacts(
        self,
        task_id: UUID,
        artifact_paths: list[str],
    ) -> bool:
        """Update task with generated artifact paths.
        
        Called by Celery workers after pipeline completion.
        """
        return await self.repository.update_task_artifacts(task_id, artifact_paths)

    async def get_concurrency_statistics(self) -> dict[str, Any]:
        """Get current concurrency statistics."""
        return await self.concurrency_repo.get_statistics()

    # ========================================================================
    # INTERNAL: Concurrency Management
    # ========================================================================

    async def _can_acquire_threads(self, threads_needed: int) -> tuple[bool, int]:
        """Check if threads can be acquired.
        
        Returns:
            Tuple of (can_acquire, current_usage)
        """
        current_usage = await self.concurrency_repo.count_active_threads()
        available = self.config.max_project_threads - current_usage
        return available >= threads_needed, current_usage

    async def _acquire_threads(
        self,
        task_id: UUID,
        task_type: TaskType,
        threads_needed: int,
    ) -> None:
        """Reserve threads for task execution."""
        await self.concurrency_repo.reserve_threads(
            task_id=task_id,
            task_type=task_type,
            threads_needed=threads_needed,
        )

    async def _release_threads(self, task_id: UUID) -> None:
        """Release reserved threads."""
        await self.concurrency_repo.release_threads(task_id)

    # ========================================================================
    # INTERNAL: Task Dispatch
    # ========================================================================

    async def _dispatch_task(self, task: Task) -> None:
        """Send task to Celery for execution."""
        celery_app = self._get_celery_app()
        task_type = TaskType(task.task_type)
        
        celery_task_path = self.CELERY_TASKS.get(task_type)
        if not celery_task_path:
            raise ValueError(f"Unknown task type: {task_type}")
        
        queue = self.QUEUE_MAP.get(task_type, "default")
        
        # Send to Celery
        celery_result = celery_app.send_task(
            celery_task_path,
            args=(str(task.id),),
            queue=queue,
            priority=task.priority or self.config.default_priority,
        )
        
        # Update task with Celery ID
        await self.repository.update_task_fields(
            task_id=task.id,
            status=TaskStatus.PROCESSING,
            celery_task_id=celery_result.id,
            started_at=datetime.now(timezone.utc),
        )
        
        logger.info(f"Dispatched task {task.id} to Celery (queue={queue}, celery_id={celery_result.id})")

    # ========================================================================
    # INTERNAL: Helpers
    # ========================================================================

    def _validate_ownership(
        self,
        user_id: UUID | None,
        guest_session_id: UUID | None,
    ) -> None:
        """Validate that either user_id or guest_session_id is provided."""
        if not user_id and not guest_session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either user_id or guest_session_id must be provided",
            )

    def _normalize_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Normalize and validate configuration.
        
        Both playground and pipeline use the same config structure:
        - batch_size: items per batch
        - max_parallel_batches: threads to use (capped at max_project_threads)
        - include_risk_ids: optional risk filter
        - llm_provider: LLM provider to use
        """
        normalized = dict(config)
        
        # Set defaults
        normalized.setdefault("batch_size", self.config.default_batch_size)
        normalized.setdefault(
            "max_parallel_batches", 
            self.config.default_max_parallel_batches
        )
        normalized.setdefault("include_risk_ids", None)
        normalized.setdefault("llm_provider", None)
        
        # Clamp max_parallel_batches to project limit
        normalized["max_parallel_batches"] = min(
            normalized["max_parallel_batches"],
            self.config.max_project_threads
        )
        
        return normalized

    @staticmethod
    def _get_celery_app() -> Celery:
        """Get Celery app instance."""
        from service.infrastructure.messaging.app.celery_app import celery_app
        return celery_app
