"""Repository for managing background tasks in Pushi platform."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from service.models.db.task_models import Task
from service.models.enums import TaskStatus, TaskType
from service.repositories.base_repository import BaseRepository
from service.repositories.decorators.decorators import log_operation, validate_params
from service.repositories.decorators.session_processor import connection
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from service.utils.logger import get_logger

logger = get_logger(__name__)


class TaskRepository(BaseRepository):
    """Repository for task tracking and management in Pushi platform."""

    @log_operation(log_level=logging.INFO)
    @connection()
    async def create_task(
        self,
        data: dict | None = None,
        *,
        task_type: TaskType | str | None = None,
        status: TaskStatus | str | None = None,
        payload: dict | None = None,
        config: dict | None = None,
        priority: int | None = None,
        scheduled_at: datetime | None = None,
        max_retries: int | None = None,
        communication_task_id: UUID | None = None,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
        file_id: UUID | None = None,
        parent_task_id: UUID | None = None,
        session: AsyncSession | None = None,
    ) -> Task:
        """Create a new task record.
        
        Unified method supporting both legacy (CommunicationTask-based) 
        and new (Task-based) task creation.
        """
        assert session is not None, "DB session is required"

        task_data = dict(data or {})
        
        resolved_task_type = None
        if task_type is not None:
            resolved_task_type = task_type.value if isinstance(task_type, TaskType) else task_type
        resolved_task_type = resolved_task_type or task_data.get("task_type")
        if not resolved_task_type:
            raise ValueError("task_type is required")

        resolved_status = None
        if status is not None:
            resolved_status = status.value if isinstance(status, TaskStatus) else status
        resolved_status = (
            resolved_status or task_data.get("status") or TaskStatus.PENDING.value
        )

        resolved_payload = payload if payload is not None else task_data.get("payload", {})
        resolved_config = config if config is not None else task_data.get("config")
        priority_value = priority if priority is not None else task_data.get("priority", 0)
        scheduled_value = (
            scheduled_at if scheduled_at is not None else task_data.get("scheduled_at")
        )
        max_retries_value = (
            max_retries if max_retries is not None else task_data.get("max_retries", 3)
        )
        
        # Ownership - legacy or new
        comm_task_id = (
            communication_task_id
            if communication_task_id is not None
            else task_data.get("communication_task_id")
        )
        resolved_user_id = user_id if user_id is not None else task_data.get("user_id")
        resolved_guest_session_id = guest_session_id if guest_session_id is not None else task_data.get("guest_session_id")
        resolved_file_id = file_id if file_id is not None else task_data.get("file_id")
        resolved_parent_task_id = parent_task_id if parent_task_id is not None else task_data.get("parent_task_id")

        payload = dict(resolved_payload or {})
        depends = payload.get("depends_on")
        if depends:
            payload["depends_on"] = [str(dep) for dep in depends]

        task_kwargs = {
            "task_type": resolved_task_type,
            "status": resolved_status,
            "payload": payload,
            "config": resolved_config,
            "priority": priority_value,
            "scheduled_at": scheduled_value,
            "communication_task_id": comm_task_id,
            "user_id": resolved_user_id,
            "guest_session_id": resolved_guest_session_id,
            "file_id": resolved_file_id,
            "parent_task_id": resolved_parent_task_id,
        }
        if hasattr(Task, "max_retries"):
            task_kwargs["max_retries"] = max_retries_value

        task = Task(**task_kwargs)
        session.add(task)
        await session.flush()
        
        logger.info(f"Task created: {task.id}, type={resolved_task_type}, status={resolved_status}")
        return task

    @connection()
    async def get_task_by_id(
        self, task_id: UUID, session: AsyncSession | None = None
    ) -> Task | None:
        """Retrieve a task by UUID."""
        assert session is not None, "DB session is required"
        return await self.get_one_or_none(
            session=session,
            model=Task,
            filters={"id": task_id},
        )

    @connection()
    async def get_task_by_celery_id(
        self, celery_task_id: str, session: AsyncSession | None = None
    ) -> Task | None:
        """Retrieve a task by Celery task ID.
        
        Args:
            celery_task_id: Celery task ID string
            session: DB session
            
        Returns:
            Task or None if not found
        """
        assert session is not None, "DB session is required"
        
        stmt = select(Task).where(Task.celery_task_id == celery_task_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @connection()
    async def get_tasks_by_user(
        self,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
        task_type: TaskType | None = None,
        status: TaskStatus | None = None,
        limit: int = 50,
        offset: int = 0,
        session: AsyncSession | None = None,
    ) -> list[Task]:
        """Get tasks for a specific user (registered or guest).
        
        Args:
            user_id: User ID (if registered)
            guest_session_id: Guest session ID (if guest)
            task_type: Filter by task type
            status: Filter by status
            limit: Maximum results
            offset: Pagination offset
            session: DB session
            
        Returns:
            List of matching tasks
        """
        assert session is not None, "DB session is required"
        assert user_id or guest_session_id, "Either user_id or guest_session_id required"
        
        stmt = select(Task)
        
        if user_id:
            stmt = stmt.where(Task.user_id == user_id)
        else:
            stmt = stmt.where(Task.guest_session_id == guest_session_id)
        
        if task_type:
            stmt = stmt.where(Task.task_type == task_type.value)
        if status:
            stmt = stmt.where(Task.status == status.value)
        
        stmt = stmt.order_by(Task.created_at.desc()).limit(limit).offset(offset)
        
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @connection()
    async def update_task_artifacts(
        self,
        task_id: UUID,
        artifact_paths: list[str],
        session: AsyncSession | None = None,
    ) -> bool:
        """Update task artifacts (for pipeline tasks).
        
        Args:
            task_id: Task ID
            artifact_paths: List of artifact file paths
            session: DB session
            
        Returns:
            True if updated
        """
        assert session is not None, "DB session is required"
        
        stmt = (
            update(Task)
            .where(Task.id == task_id)
            .values(artifact_paths=artifact_paths)
            .execution_options(synchronize_session="fetch")
        )
        result = await session.execute(stmt)
        await session.flush()
        
        success = result.rowcount > 0
        if success:
            logger.info(f"Task artifacts updated: {task_id} ({len(artifact_paths)} artifacts)")
        
        return success

    @validate_params(limit=lambda x: 1 <= x <= 500)
    @connection()
    async def get_tasks_by_communication_task(
        self,
        communication_task_id: UUID,
        status: TaskStatus | None = None,
        task_type: TaskType | None = None,
        limit: int = 50,
        offset: int = 0,
        session: AsyncSession | None = None,
    ) -> list[Task]:
        """List tasks associated with a communication task."""
        assert session is not None, "DB session is required"
        
        stmt = select(Task).where(Task.communication_task_id == communication_task_id)
        if status:
            stmt = stmt.where(Task.status == status.value)
        if task_type:
            stmt = stmt.where(Task.task_type == task_type.value)
        stmt = stmt.order_by(Task.created_at.desc()).limit(limit).offset(offset)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    @connection()
    async def update_task_fields(
        self,
        task_id: UUID,
        status: TaskStatus | None = None,
        result: dict | None = None,
        error_message: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        progress: int | None = None,
        celery_task_id: str | None = None,
        retry_count: int | None = None,
        scheduled_at: datetime | None = None,
        session: AsyncSession | None = None,
    ) -> Task | None:
        """Update task metadata fields."""
        assert session is not None, "DB session is required"
        
        updates: dict = {}
        if status:
            updates[Task.status] = status.value
        if result is not None:
            updates[Task.result] = result
        if error_message is not None:
            updates[Task.error_message] = error_message
        if started_at is not None:
            updates[Task.started_at] = started_at
        if completed_at is not None:
            updates[Task.completed_at] = completed_at
        if celery_task_id is not None:
            updates[Task.celery_task_id] = celery_task_id
        if retry_count is not None:
            updates[Task.retry_count] = retry_count
        if scheduled_at is not None:
            updates[Task.scheduled_at] = scheduled_at
        if progress is not None:
            result_payload = updates.get(Task.result) or {}
            result_payload = dict(result_payload)
            result_payload["progress"] = progress
            updates[Task.result] = result_payload

        if not updates:
            return await self.get_task_by_id(task_id, session=session)

        stmt = (
            update(Task)
            .where(Task.id == task_id)
            .values(updates)
            .execution_options(synchronize_session="fetch")
        )
        await session.execute(stmt)
        await session.flush()

        logger.info(f"Task updated: {task_id}")
        return await self.get_task_by_id(task_id, session=session)

    @log_operation(log_level=logging.DEBUG)
    @connection()
    async def update_task_status(
        self,
        task_id: UUID,
        new_status: TaskStatus,
        session: AsyncSession | None = None,
    ) -> bool:
        """Update task status flag."""
        assert session is not None, "DB session is required"
        
        stmt = (
            update(Task)
            .where(Task.id == task_id)
            .values(status=new_status.value)
            .execution_options(synchronize_session="fetch")
        )
        result = await session.execute(stmt)
        await session.flush()
        
        success = result.rowcount > 0
        if success:
            logger.info(f"Task status updated: {task_id} -> {new_status.value}")
        
        return success

    @validate_params(limit=lambda x: 1 <= x <= 500)
    @connection()
    async def get_scheduled_tasks(
        self, limit: int = 50, session: AsyncSession | None = None
    ) -> list[Task]:
        """Return tasks scheduled to run up to the current moment."""
        assert session is not None, "DB session is required"
        
        now = datetime.now(timezone.utc)
        stmt = (
            select(Task)
            .where(Task.status == TaskStatus.NEW.value)
            .where(Task.scheduled_at.isnot(None))
            .where(Task.scheduled_at <= now)
            .order_by(Task.scheduled_at.asc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @connection()
    async def retry_failed_task(
        self,
        task_id: UUID,
        session: AsyncSession | None = None,
    ) -> bool:
        """Re-enqueue a failed task by bumping retry count and resetting status."""
        assert session is not None, "DB session is required"
        
        stmt = (
            update(Task)
            .where(Task.id == task_id)
            .where(Task.status == TaskStatus.FAILED.value)
            .values(
                status=TaskStatus.NEW.value,
                retry_count=Task.retry_count + 1,
            )
            .execution_options(synchronize_session="fetch")
        )
        result = await session.execute(stmt)
        await session.flush()
        
        success = result.rowcount > 0
        if success:
            logger.info(f"Task retry initiated: {task_id}")
        
        return success

    @connection()
    async def list_tasks_waiting_for_dependencies(
        self, session: AsyncSession | None = None
    ) -> list[Task]:
        """Return tasks that are waiting on dependencies (status=PENDING)."""
        assert session is not None, "DB session is required"
        
        stmt = select(Task).where(Task.status == TaskStatus.PENDING.value)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @validate_params(limit=lambda x: 1 <= x <= 500)
    @connection()
    async def list_failed_tasks_for_retry(
        self,
        max_retries: int,
        limit: int = 20,
        session: AsyncSession | None = None,
    ) -> list[Task]:
        """Return failed tasks that can be retried."""
        assert session is not None, "DB session is required"
        
        stmt = (
            select(Task)
            .where(Task.status == TaskStatus.FAILED.value)
            .where(Task.retry_count < func.coalesce(Task.max_retries, max_retries))
            .order_by(Task.retry_count.asc(), Task.created_at.asc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @connection()
    async def increment_retry_count(
        self, task_id: UUID, session: AsyncSession | None = None
    ) -> None:
        """Increment retry counter for a task."""
        assert session is not None, "DB session is required"
        
        stmt = (
            update(Task)
            .where(Task.id == task_id)
            .values(retry_count=Task.retry_count + 1)
            .execution_options(synchronize_session="fetch")
        )
        await session.execute(stmt)
        await session.flush()
        
        logger.debug(f"Task retry count incremented: {task_id}")

    @log_operation(log_level=logging.INFO)
    @connection()
    async def delete_tasks_older_than(
        self, cutoff: datetime, session: AsyncSession | None = None
    ) -> int:
        """Clean up tasks that completed before the cutoff."""
        assert session is not None, "DB session is required"
        
        eligible_statuses = [
            TaskStatus.COMPLETED.value,
            TaskStatus.FAILED.value,
            TaskStatus.CANCELLED.value,
        ]
        stmt = (
            delete(Task).where(Task.completed_at < cutoff).where(Task.status.in_(eligible_statuses))
        )
        result = await session.execute(stmt)
        await session.flush()
        
        count = result.rowcount
        logger.info(f"Deleted {count} old tasks completed before {cutoff}")
        return count

    @connection()
    async def count_tasks_by_status(
        self, status: TaskStatus, session: AsyncSession | None = None
    ) -> int:
        """Count tasks with a specific status."""
        assert session is not None, "DB session is required"
        
        stmt = select(func.count()).select_from(Task).where(Task.status == status.value)
        result = await session.execute(stmt)
        return result.scalar_one() or 0

    @connection()
    async def get_task_statistics(
        self, session: AsyncSession | None = None
    ) -> dict[str, int]:
        """Get task statistics by status."""
        assert session is not None, "DB session is required"
        
        stats = {}
        for status in TaskStatus:
            count = await self.count_tasks_by_status(status, session=session)
            stats[status.value] = count
        
        return stats

    @connection()
    async def cancel_task(self, task_id: UUID, session: AsyncSession | None = None) -> bool:
        """Cancel a pending or running task."""
        assert session is not None, "DB session is required"
        
        stmt = (
            update(Task)
            .where(Task.id == task_id)
            .where(Task.status.in_([TaskStatus.PENDING.value, TaskStatus.RUNNING.value, TaskStatus.NEW.value]))
            .values(
                status=TaskStatus.CANCELLED.value,
                completed_at=datetime.now(timezone.utc),
            )
        )
        result = await session.execute(stmt)
        await session.flush()
        
        success = result.rowcount > 0
        if success:
            logger.info(f"Task cancelled: {task_id}")
        
        return success
