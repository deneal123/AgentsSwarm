"""Tasks for Playground - single and batch processing of communications.

Uses PlaygroundService from pushi_service.py for proper integration.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from celery import shared_task

from service.infrastructure.messaging.tasks.base_task import PushiBaseTask
from service.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# Celery Task Functions
# ============================================================================

@shared_task(bind=True, base=PushiBaseTask, max_retries=3)
def process_playground_single(self, task_id: str) -> dict:
    """Process single communication through Playground.
    
    Celery task entry point.
    """
    processor = PlaygroundTaskProcessor()
    return processor.process_single(task_id)


@shared_task(bind=True, base=PushiBaseTask, max_retries=3)
def process_playground_batch(self, task_id: str) -> dict:
    """Process batch of communications through Playground.
    
    Celery task entry point.
    """
    processor = PlaygroundTaskProcessor()
    return processor.process_batch(task_id)


# ============================================================================
# Task Processor
# ============================================================================

class PlaygroundTaskProcessor:
    """Processor for Playground tasks using PlaygroundService."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._task_repo = None
        self._concurrency_repo = None
        self._pushi_service = None
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

    def process_single(self, task_id: str) -> dict:
        """Process single communication."""
        return self._run_async(self._process_single_async(task_id))
    
    async def _process_single_async(self, task_id: str) -> dict:
        """Async implementation using PlaygroundService."""
        task_uuid = UUID(task_id)
        self.logger.info(f"Processing single communication: {task_id}")
        
        task_repo, concurrency_repo = self._get_repositories()
        
        # Load task
        task = await task_repo.get_task_by_id(task_uuid)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Extract data
        payload = task.payload or {}
        config = task.config or {}
        communications = payload.get("communications", [])
        
        if not communications:
            raise ValueError("No communications in task")
        
        communication = communications[0]
        include_risk_ids = config.get("include_risk_ids")
        config_file_id = config.get("config_file_id")
        
        # Get config path if config file uploaded
        config_path = config.get("config_path")
        if not config_path and config_file_id:
            config_path = await self._get_file_saver_service().get_access_path(
                UUID(config_file_id)
            )

        # Get rules snapshot from task config
        rules_list = config.get("rules", [])
        
        # Process via PlaygroundService
        playground_service = self._get_playground_service()
        
        # For single communication, use batch with 1 item
        results = await playground_service.process_batch(
            communications=[communication],
            rules_list=rules_list,
            config_path=config_path,
        )

        # Persist results to DB
        try:
            comm_svc = self._get_communication_result_service()
            await comm_svc.save_playground_results(task_uuid, results)
        except Exception:
            self.logger.exception("Failed to save communication results for task %s", task_id)
    
        # Store result
        await task_repo.update_task_fields(
            task_id=task_uuid,
            result={
                "status": "completed",
                "communication": communication,
                "analysis": results[0] if results else None,
            },
        )
        
        # Release threads
        await concurrency_repo.release_threads(task_uuid)
        
        self.logger.info(f"Completed single communication: {task_id}")
        
        return {
            "status": "completed",
            "task_id": task_id,
            "result": results[0] if results else None,
        }
    
    def process_batch(self, task_id: str) -> dict:
        """Process batch of communications."""
        return self._run_async(self._process_batch_async(task_id))
    
    async def _process_batch_async(self, task_id: str) -> dict:
        """Async batch implementation using PlaygroundService."""
        task_uuid = UUID(task_id)
        self.logger.info(f"Processing batch: {task_id}")
        
        task_repo, concurrency_repo = self._get_repositories()
        
        # Load task
        task = await task_repo.get_task_by_id(task_uuid)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Extract data
        payload = task.payload or {}
        config = task.config or {}
        communications = payload.get("communications", [])
        
        if not communications:
            raise ValueError("No communications in task")
        
        batch_size = config.get("batch_size", 10)
        config_file_id = config.get("config_file_id")

        # Get config path: prefer already-resolved path, fall back to file lookup
        config_path = config.get("config_path")
        if not config_path and config_file_id:
            config_path = await self._get_file_saver_service().get_access_path(
                UUID(config_file_id)
            )

        # Get rules snapshot from task config
        rules_list = config.get("rules", [])
        
        self.logger.info(
            f"Processing {len(communications)} communications, "
            f"batch_size={batch_size}"
        )
        
        # Process via PlaygroundService
        playground_service = self._get_playground_service()
        
        # Process in batches with progress updates
        all_results = []
        total = len(communications)
        
        for i in range(0, total, batch_size):
            batch = communications[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size
            
            self.logger.info(f"Processing batch {batch_num}/{total_batches}")
            
            # Update progress
            progress = {
                "current_batch": batch_num,
                "total_batches": total_batches,
                "processed": i,
                "total": total,
                "percentage": round(i / total * 100, 1) if total > 0 else 0,
            }
            
            await task_repo.update_task_fields(
                task_id=task_uuid,
                result={
                    "status": "processing",
                    "progress": progress,
                    "partial_results": all_results,
                },
            )
            
            # Process batch via PlaygroundService
            batch_results = await playground_service.process_batch(
                communications=batch,
                rules_list=rules_list,
                config_path=config_path,
            )
            all_results.extend(batch_results)
        
        # Persist all results to DB
        try:
            comm_svc = self._get_communication_result_service()
            saved_count = await comm_svc.save_playground_results(task_uuid, all_results)
            self.logger.info("Saved %d communication results for task %s", saved_count, task_id)
        except Exception:
            self.logger.exception("Failed to save communication results for task %s", task_id)

        # Store final results
        await task_repo.update_task_fields(
            task_id=task_uuid,
            result={
                "status": "completed",
                "total_communications": total,
                "results": all_results,
            },
        )
        
        # Release threads
        await concurrency_repo.release_threads(task_uuid)
        
        self.logger.info(f"Completed batch: {task_id}, {len(all_results)} results")
        
        return {
            "status": "completed",
            "task_id": task_id,
            "total_processed": len(all_results),
            "results": all_results,
        }

    def _get_repositories(self):
        """Create fresh repositories bound to the current event loop.

        Each Celery task runs in its own event loop (created by _run_async).
        We must create a brand-new PgConnector with force_new=True so the
        SQLAlchemy async engine and asyncpg connection pool are tied to that
        loop — not to some older loop cached on the class.
        """
        if self._task_repo is None:
            from service.infrastructure.database.postgresql import PgConnector
            from service.repositories.task_concurrency_repository import TaskConcurrencyRepository
            from service.repositories.task_repository import TaskRepository
            from service.settings import Config

            self._connector = PgConnector(Config().pg, force_new=True)
            self._task_repo = TaskRepository(self._connector)
            self._concurrency_repo = TaskConcurrencyRepository(self._connector)
        return self._task_repo, self._concurrency_repo

    def _get_file_saver_service(self):
        """Create FileSaverService with a fresh FileRepository bound to the current loop."""
        from service.infrastructure.storage.local_file_storage import LocalFileStorage
        from service.repositories.file_repository import FileRepository
        from service.services.file_saver_service import FileSaverService
        from service.settings import Config

        if self._connector is None:
            self._get_repositories()
        config = Config()
        file_repo = FileRepository(self._connector)
        backend = config.storage.backend.strip().lower()
        try:
            if backend == "minio":
                from service.infrastructure.storage.minio_file_storage import MinioFileStorage
                storage = MinioFileStorage(config.minio)
            else:
                storage = LocalFileStorage()
        except Exception:
            storage = LocalFileStorage()
        return FileSaverService(
            repository=file_repo,
            folder_name="uploads",
            file_storage=storage,
        )

    def _get_communication_result_service(self):
        """Create CommunicationResultService with a fresh repository bound to the current loop."""
        from service.repositories.communication_result_repository import CommunicationResultRepository
        from service.services.communication_result_service import CommunicationResultService

        if self._connector is None:
            self._get_repositories()
        comm_repo = CommunicationResultRepository(self._connector)
        return CommunicationResultService(comm_repo)

    def _get_playground_service(self):
        """Lazy load PlaygroundService."""
        if self._pushi_service is None:
            from service.services.pushi_service import PlaygroundService
            self._pushi_service = PlaygroundService()
        return self._pushi_service