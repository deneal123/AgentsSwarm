"""Repository for pipeline queue entries.

Provides methods used by task orchestration and pipeline processing logic.
"""

import logging
from typing import Optional
from uuid import UUID

from service.models.db.pipeline_slot_models import PipelineSlot
from service.repositories.base_repository import BaseRepository
from service.repositories.decorators.decorators import log_operation
from service.repositories.decorators.session_processor import connection
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from service.utils.logger import get_logger

logger = get_logger(__name__)


class PipelineSlotRepository(BaseRepository):
    """Repository encapsulating pipeline_slot table operations."""

    @log_operation(log_level=logging.DEBUG)
    @connection()
    async def get_queue_entry_by_task_id(
        self, task_id: UUID, session: AsyncSession | None = None
    ) -> Optional[PipelineSlot]:
        assert session is not None, "DB session is required"
        stmt = select(PipelineSlot).where(PipelineSlot.task_id == task_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @log_operation(log_level=logging.DEBUG)
    @connection()
    async def count_users_ahead(
        self,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
        session: AsyncSession | None = None,
    ) -> int:
        """Count number of queued entries for the same user/guest.

        This is a simplified implementation used by the orchestration layer
        to estimate queue position. It does *not* take current task into
        account; the calling code will add 1 when presenting position.
        """
        assert session is not None, "DB session is required"
        stmt = select(func.count()).select_from(PipelineSlot).where(
            PipelineSlot.status == "queued"
        )
        if user_id:
            stmt = stmt.where(PipelineSlot.user_id == user_id)
        elif guest_session_id:
            stmt = stmt.where(PipelineSlot.guest_session_id == guest_session_id)
        result = await session.execute(stmt)
        return result.scalar_one() or 0

    @log_operation(log_level=logging.INFO)
    @connection()
    async def update_status(
        self,
        task_id: UUID,
        status: str,
        error_message: Optional[str] = None,
        session: AsyncSession | None = None,
    ) -> None:
        """Update queue entry status and timestamps."""
        assert session is not None, "DB session is required"
        values = {"status": status}
        if status == "processing":
            values["started_at"] = func.now()
        if status in ("completed", "failed", "cancelled"):
            values["finished_at"] = func.now()
        # ignore error_message for now; no column exists
        stmt = update(PipelineSlot).where(PipelineSlot.task_id == task_id).values(**values)
        await session.execute(stmt)
        await session.flush()
