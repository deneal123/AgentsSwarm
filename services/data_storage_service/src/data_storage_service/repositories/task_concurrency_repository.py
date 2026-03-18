"""Repository for task concurrency management - tracks occupied threads."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from service.models.db.task_models import TaskConcurrency
from service.models.enums import TaskType
from service.repositories.base_repository import BaseRepository
from service.repositories.decorators.decorators import log_operation
from service.repositories.decorators.session_processor import connection
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from service.utils.logger import get_logger

logger = get_logger(__name__)


class TaskConcurrencyRepository(BaseRepository):
    """Repository for managing task thread allocation and concurrency limits.
    
    Tracks how many threads are currently occupied by running tasks.
    Used to enforce max_project_threads limit.
    """

    @log_operation(log_level=logging.DEBUG)
    @connection()
    async def reserve_threads(
        self,
        task_id: UUID,
        task_type: TaskType,
        threads_needed: int,
        session: AsyncSession | None = None,
    ) -> TaskConcurrency | None:
        """Reserve threads for a task.
        
        Note: This method assumes that max_project_threads check 
        was already performed by TaskOrchestratorService.
        
        Args:
            task_id: Task ID
            task_type: Type of task
            threads_needed: Number of threads to reserve
            session: DB session
            
        Returns:
            TaskConcurrency record or None if failed
        """
        assert session is not None, "DB session is required"
        
        # Check if already reserved
        existing = await self.get_by_task_id(task_id, session=session)
        if existing:
            logger.warning(f"Threads already reserved for task {task_id}")
            return existing
        
        concurrency_record = TaskConcurrency(
            task_id=task_id,
            task_type=task_type.value,
            threads_used=threads_needed,
            started_at=datetime.now(timezone.utc),
        )
        
        session.add(concurrency_record)
        await session.flush()
        
        logger.info(
            f"Reserved {threads_needed} threads for task {task_id} "
            f"(type: {task_type.value})"
        )
        return concurrency_record

    @log_operation(log_level=logging.DEBUG)
    @connection()
    async def release_threads(
        self,
        task_id: UUID,
        session: AsyncSession | None = None,
    ) -> bool:
        """Release threads for a completed task.
        
        Args:
            task_id: Task ID
            session: DB session
            
        Returns:
            True if threads were released
        """
        assert session is not None, "DB session is required"
        
        record = await self.get_by_task_id(task_id, session=session)
        if not record:
            logger.warning(f"No concurrency record found for task {task_id}")
            return False
        
        record.completed_at = datetime.now(timezone.utc)
        await session.flush()
        
        logger.info(
            f"Released {record.threads_used} threads for task {task_id}"
        )
        return True

    @connection()
    async def get_by_task_id(
        self,
        task_id: UUID,
        session: AsyncSession | None = None,
    ) -> TaskConcurrency | None:
        """Get concurrency record by task ID."""
        assert session is not None, "DB session is required"
        
        return await self.get_one_or_none(
            session=session,
            model=TaskConcurrency,
            filters={"task_id": task_id},
        )

    @connection()
    async def count_active_threads(
        self,
        session: AsyncSession | None = None,
    ) -> int:
        """Count total threads currently in use.
        
        Returns:
            Sum of threads_used for all active (not completed) records
        """
        assert session is not None, "DB session is required"
        
        stmt = (
            select(func.coalesce(func.sum(TaskConcurrency.threads_used), 0))
            .where(TaskConcurrency.completed_at.is_(None))
        )
        result = await session.execute(stmt)
        return result.scalar_one()

    @connection()
    async def count_active_threads_by_type(
        self,
        task_type: TaskType,
        session: AsyncSession | None = None,
    ) -> int:
        """Count threads in use by specific task type.
        
        Args:
            task_type: Task type to filter by
            session: DB session
            
        Returns:
            Sum of threads for this task type
        """
        assert session is not None, "DB session is required"
        
        stmt = (
            select(func.coalesce(func.sum(TaskConcurrency.threads_used), 0))
            .where(TaskConcurrency.task_type == task_type.value)
            .where(TaskConcurrency.completed_at.is_(None))
        )
        result = await session.execute(stmt)
        return result.scalar_one()

    @connection()
    async def get_active_tasks(
        self,
        session: AsyncSession | None = None,
        limit: int = 100,
    ) -> list[TaskConcurrency]:
        """Get all active concurrency records.
        
        Args:
            session: DB session
            limit: Maximum records to return
            
        Returns:
            List of active concurrency records
        """
        assert session is not None, "DB session is required"
        
        stmt = (
            select(TaskConcurrency)
            .where(TaskConcurrency.completed_at.is_(None))
            .order_by(TaskConcurrency.started_at)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @connection()
    async def has_active_pipeline_for_user(
        self,
        user_id: UUID | None,
        guest_session_id: UUID | None,
        session: AsyncSession | None = None,
    ) -> bool:
        """Check if user has an active pipeline task.
        
        Used to enforce sequential pipeline execution per user.
        
        Args:
            user_id: User ID (if registered)
            guest_session_id: Guest session ID (if guest)
            session: DB session
            
        Returns:
            True if user has active pipeline
        """
        assert session is not None, "DB session is required"
        
        if not user_id and not guest_session_id:
            raise ValueError("Either user_id or guest_session_id must be provided")
        
        from service.models.db.task_models import Task
        
        stmt = (
            select(func.count())
            .select_from(TaskConcurrency)
            .join(Task, TaskConcurrency.task_id == Task.id)
            .where(TaskConcurrency.task_type == TaskType.PIPELINE.value)
            .where(TaskConcurrency.completed_at.is_(None))
        )
        
        if user_id:
            stmt = stmt.where(Task.user_id == user_id)
        else:
            stmt = stmt.where(Task.guest_session_id == guest_session_id)
        
        result = await session.execute(stmt)
        count = result.scalar_one()
        return count > 0

    @log_operation(log_level=logging.INFO)
    @connection()
    async def cleanup_old_records(
        self,
        days_old: int = 7,
        session: AsyncSession | None = None,
    ) -> int:
        """Clean up completed concurrency records older than specified days.
        
        Args:
            days_old: Age threshold in days
            session: DB session
            
        Returns:
            Number of records deleted
        """
        assert session is not None, "DB session is required"
        
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - __import__(
            'datetime'
        ).timedelta(days=days_old)
        
        stmt = (
            delete(TaskConcurrency)
            .where(TaskConcurrency.completed_at.isnot(None))
            .where(TaskConcurrency.completed_at < cutoff)
        )
        result = await session.execute(stmt)
        await session.flush()
        
        count = result.rowcount
        logger.info(f"Cleaned up {count} old concurrency records (>{days_old} days)")
        return count

    @connection()
    async def get_statistics(
        self,
        session: AsyncSession | None = None,
    ) -> dict:
        """Get concurrency statistics.
        
        Returns:
            Dict with total_active_threads, by_type breakdown, etc.
        """
        assert session is not None, "DB session is required"
        
        total = await self.count_active_threads(session)
        
        stats = {
            "total_active_threads": total,
            "by_type": {},
        }
        
        for task_type in TaskType:
            count = await self.count_active_threads_by_type(task_type, session=session)
            if count > 0:
                stats["by_type"][task_type.value] = count
        
        return stats
