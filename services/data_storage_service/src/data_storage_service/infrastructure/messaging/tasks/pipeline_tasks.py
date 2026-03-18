"""Tasks for Pipeline - dataset analysis processing.

Uses PipelineService from pushi_service.py for proper integration.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from celery import shared_task

from service.infrastructure.messaging.tasks.base_task import PushiBaseTask
from service.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# Celery Task Functions
# ============================================================================

@shared_task(bind=True, base=PushiBaseTask, max_retries=2)
def process_pipeline(self, task_id: str) -> dict:
    """Process dataset through Pipeline using PipelineService.
    
    Celery task entry point.
    """
    processor = PipelineTaskProcessor()
    return processor.process(task_id)


# ============================================================================
# Task Processor
# ============================================================================

class PipelineTaskProcessor:
    """Processor for Pipeline tasks using PipelineService."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._task_repo = None
        self._concurrency_repo = None
        self._queue_repo = None
        self._file_saver_svc = None
        self._pipeline_service = None
        self._connector = None  # shared connector for the current task's event loop

    def _run_async(self, coro):
        """Run a coroutine in a fresh, isolated event loop.

        Each Celery task invocation gets its own loop so that asyncpg
        connections (which are loop-bound) are never shared across loops.
        """
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            finally:
                loop.close()
                asyncio.set_event_loop(None)

    def process(self, task_id: str) -> dict:
        """Process dataset through pipeline."""
        return self._run_async(self._process_async(task_id))
    
    async def _process_async(self, task_id: str) -> dict:
        """Async implementation using PipelineService."""
        task_uuid = UUID(task_id)
        self.logger.info(f"Starting pipeline: {task_id}")
        
        task_repo, concurrency_repo, queue_repo = self._get_repositories()
        
        # Load task
        task = await task_repo.get_task_by_id(task_uuid)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Update queue status
        await queue_repo.update_status(
            task_id=task_uuid,
            status="processing",
        )
        
        # Extract data
        payload = task.payload or {}
        config = task.config or {}
        dataset_file_id = payload.get("dataset_file_id")
        
        if not dataset_file_id:
            raise ValueError("No dataset_file_id in payload")
        
        # Load dataset file — use FileSaverService to get backend-appropriate path
        # (presigned URL for MinIO/S3, filesystem path for local storage)
        file_saver = self._get_file_saver_service()
        dataset_path = await file_saver.get_access_path(UUID(dataset_file_id))
        if not dataset_path:
            raise ValueError(f"Dataset file {dataset_file_id} not found")
        self.logger.info(f"Dataset path: {dataset_path}")

        # Get config path: prefer already-resolved path, fall back to file lookup
        config_file_id = config.get("config_file_id")
        config_path = config.get("config_path")
        if not config_path and config_file_id:
            config_path = await file_saver.get_access_path(UUID(config_file_id))
        
        # Get rules snapshot and format from task config
        rules_list = config.get("rules", [])
        format_file = config.get("format_file", "xlsx")
        
        # Update progress
        await task_repo.update_task_fields(
            task_id=task_uuid,
            result={
                "status": "processing",
                "stage": "analysis",
                "dataset_path": dataset_path,
            },
        )
        
        # Run pipeline via PipelineService
        pipeline_service = self._get_pipeline_service()
        
        try:
            # PipelineService returns context dict from pipeline.run()
            result_context = await pipeline_service.process_pipe(
                dataset_path=dataset_path,
                rules_list=rules_list,
                config_path=config_path,
                format_file=format_file,
            )

            # Extract experiment directory from result context
            exp_dir = (
                result_context.get("exp_dir")
                or result_context.get("output_dir")
                or result_context.get("exp_path")
                or ""
            )
            
            # Collect artifact paths from exp_dir
            artifact_paths = self._collect_artifacts(exp_dir) if exp_dir else []
            
            # Store artifact paths
            await task_repo.update_task_artifacts(task_uuid, artifact_paths)
            
            # Update queue status
            await queue_repo.update_status(
                task_id=task_uuid,
                status="completed",
            )
            
            # Release thread
            await concurrency_repo.release_threads(task_uuid)
            
            self.logger.info(
                f"Pipeline completed: {task_id}, artifacts: {len(artifact_paths)}"
            )
            
            return {
                "status": "completed",
                "task_id": task_id,
                "exp_dir": exp_dir,
                "artifact_paths": artifact_paths,
            }
            
        except Exception as e:
            self.logger.exception(f"Pipeline failed: {e}")
            
            # Update queue status
            await queue_repo.update_status(
                task_id=task_uuid,
                status="failed",
                error_message=str(e),
            )
            
            raise
    
    def _collect_artifacts(self, exp_dir: str) -> list[str]:
        """Collect artifact paths from experiment directory.
        
        Args:
            exp_dir: Experiment directory path returned by pipeline
            
        Returns:
            List of artifact file paths
        """
        import os
        
        artifact_paths = []
        exp_path = Path(exp_dir)
        
        if not exp_path.exists():
            self.logger.warning(f"Experiment directory not found: {exp_dir}")
            return artifact_paths
        
        # Collect all files in exp_dir
        for root, dirs, files in os.walk(exp_dir):
            for file in files:
                full_path = os.path.join(root, file)
                artifact_paths.append(full_path)
        
        self.logger.info(f"Collected {len(artifact_paths)} artifacts from {exp_dir}")
        return artifact_paths
    
    def _get_repositories(self):
        """Create fresh repositories bound to the current event loop.

        Each Celery task runs in its own event loop (created by _run_async).
        We must create a brand-new PgConnector with force_new=True so the
        SQLAlchemy async engine and asyncpg connection pool are tied to that
        loop — not to some older loop cached on the class.
        """
        if self._task_repo is None:
            from service.infrastructure.database.postgresql import PgConnector
            from service.repositories.pipeline_slot_repository import PipelineSlotRepository
            from service.repositories.task_concurrency_repository import TaskConcurrencyRepository
            from service.repositories.task_repository import TaskRepository
            from service.settings import Config

            self._connector = PgConnector(Config().pg, force_new=True)
            self._task_repo = TaskRepository(self._connector)
            self._concurrency_repo = TaskConcurrencyRepository(self._connector)
            self._queue_repo = PipelineSlotRepository(self._connector)
        return self._task_repo, self._concurrency_repo, self._queue_repo

    def _get_file_saver_service(self):
        """Create FileSaverService with a fresh FileRepository bound to the current loop."""
        if self._file_saver_svc is None:
            from service.infrastructure.storage.local_file_storage import LocalFileStorage
            from service.repositories.file_repository import FileRepository
            from service.services.file_saver_service import FileSaverService
            from service.settings import Config

            # Reuse same connector (already bound to this task's loop)
            if self._connector is None:
                self._get_repositories()
            config = Config()
            file_repo = FileRepository(self._connector)
            # Determine storage backend
            backend = config.storage.backend.strip().lower()
            try:
                if backend == "minio":
                    from service.infrastructure.storage.minio_file_storage import MinioFileStorage
                    storage = MinioFileStorage(config.minio)
                else:
                    storage = LocalFileStorage()
            except Exception:
                storage = LocalFileStorage()
            self._file_saver_svc = FileSaverService(
                repository=file_repo,
                folder_name="uploads",
                file_storage=storage,
            )
        return self._file_saver_svc
    
    def _get_pipeline_service(self):
        """Lazy load PipelineService."""
        if self._pipeline_service is None:
            from service.services.pushi_service import PipelineService
            self._pipeline_service = PipelineService()
        return self._pipeline_service