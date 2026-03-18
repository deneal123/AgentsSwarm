"""Repository for file management in Pushi platform."""

import logging
from datetime import datetime
from uuid import UUID

from service.models.db import File
from service.models.enums import FileType
from service.repositories.base_repository import BaseRepository
from service.repositories.decorators.decorators import (
    cache,
    log_operation,
    validate_params,
)
from service.repositories.decorators.session_processor import connection
from service.utils.logger import get_logger
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class FileRepository(BaseRepository):
    """Repository for file management in Pushi platform."""

    @log_operation(log_level=logging.INFO)
    @connection()
    async def create_file(self, file: File, session: AsyncSession | None = None) -> File:
        """Create new file record."""
        assert session is not None, "DB session is required"

        logger.debug(f"Creating file: {file.id}")
        session.add(file)
        await session.flush()

        logger.info(f"File created: {file.id}")
        return file

    @cache(ttl=120.0, namespace="files")
    @connection()
    async def get_file_by_id(
        self, file_id: UUID, session: AsyncSession | None = None
    ) -> File | None:
        """Get file by ID (cached)."""
        assert session is not None, "DB session is required"

        return await self.get_one_or_none(
            session=session,
            model=File,
            filters={"id": file_id},
        )

    @cache(ttl=120.0, namespace="files")
    @connection()
    async def get_file_by_storage_path(
        self, storage_path: str, session: AsyncSession | None = None
    ) -> File | None:
        """Get file by storage path (cached)."""
        assert session is not None, "DB session is required"

        return await self.get_one_or_none(
            session=session,
            model=File,
            filters={"storage_path": storage_path},
        )

    @cache(ttl=60.0, namespace="files")
    @validate_params(limit=lambda x: 1 <= x <= 1000)
    @connection()
    async def get_files_by_type(
        self, file_type: FileType, limit: int = 100, session: AsyncSession | None = None
    ) -> list[File]:
        """Get files by type with limit (cached)."""
        assert session is not None, "DB session is required"

        result = await session.execute(select(File).where(File.file_type == file_type).limit(limit))
        return list(result.scalars().all())

    @validate_params(limit=lambda x: 1 <= x <= 1000)
    @connection()
    async def get_files_by_user(
        self,
        user_id: UUID,
        file_type: FileType | None = None,
        limit: int = 100,
        offset: int = 0,
        session: AsyncSession | None = None,
    ) -> list[File]:
        """Get files uploaded by a specific user."""
        assert session is not None, "DB session is required"

        stmt = select(File).where(File.uploaded_by_user_id == user_id)
        if file_type:
            stmt = stmt.where(File.file_type == file_type)
        stmt = stmt.order_by(File.created_at.desc()).limit(limit).offset(offset)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    @validate_params(limit=lambda x: 1 <= x <= 1000)
    @connection()
    async def get_files_by_guest(
        self,
        guest_session_id: UUID,
        file_type: FileType | None = None,
        limit: int = 100,
        offset: int = 0,
        session: AsyncSession | None = None,
    ) -> list[File]:
        """Get files uploaded by a guest session."""
        assert session is not None, "DB session is required"

        stmt = select(File).where(File.uploaded_by_guest_id == guest_session_id)
        if file_type:
            stmt = stmt.where(File.file_type == file_type)
        stmt = stmt.order_by(File.created_at.desc()).limit(limit).offset(offset)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    @connection()
    async def get_user_storage_usage(
        self, user_id: UUID, session: AsyncSession | None = None
    ) -> int:
        """Calculate total bytes stored for a specific user."""
        assert session is not None, "DB session is required"

        stmt = select(func.coalesce(func.sum(File.file_size), 0)).where(
            File.uploaded_by_user_id == user_id
        )
        result = await session.execute(stmt)
        return result.scalar_one() or 0

    @connection()
    async def get_guest_storage_usage(
        self, guest_session_id: UUID, session: AsyncSession | None = None
    ) -> int:
        """Calculate total bytes stored for a guest session."""
        assert session is not None, "DB session is required"

        stmt = select(func.coalesce(func.sum(File.file_size), 0)).where(
            File.uploaded_by_guest_id == guest_session_id
        )
        result = await session.execute(stmt)
        return result.scalar_one() or 0

    @log_operation(log_level=logging.DEBUG)
    @connection()
    async def update_file_metadata(
        self, file_id: UUID, updates: dict, session: AsyncSession | None = None
    ) -> File | None:
        """Update file metadata."""
        assert session is not None, "DB session is required"

        logger.debug(f"Updating file metadata: file_id={file_id}")
        
        # Remove protected fields
        protected_fields = {"id", "created_at", "uploaded_by_user_id", "uploaded_by_guest_id"}
        update_values = {k: v for k, v in updates.items() if k not in protected_fields}
        
        if not update_values:
            return await self.get_file_by_id(file_id, session=session)
        
        stmt = update(File).where(File.id == file_id).values(**update_values).returning(File)
        result = await session.execute(stmt)
        await session.flush()

        file = result.scalar_one_or_none()
        if file:
            logger.info(f"File metadata updated: {file_id}")

        return file

    @log_operation(log_level=logging.INFO)
    @connection()
    async def delete_file(self, file_id: UUID, session: AsyncSession | None = None) -> bool:
        """Delete file record and invalidate cache."""
        assert session is not None, "DB session is required"

        logger.debug(f"Deleting file: file_id={file_id}")
        result = await session.execute(delete(File).where(File.id == file_id))
        await session.flush()

        success = result.rowcount > 0
        if success:
            logger.info(f"File deleted: {file_id}")
            # Invalidate Redis cache for this file
            try:
                from service.repositories.decorators.decorators import get_redis_cache
                redis_cache = get_redis_cache()
                if redis_cache:
                    await redis_cache.invalidate("files", f"get_file_by_id:{file_id}:")
            except Exception as exc:
                logger.warning(f"Failed to invalidate file cache after delete: {exc}")

        return success

    @validate_params(limit=lambda x: x is None or (1 <= x <= 1000))
    @connection()
    async def list_files_older_than(
        self,
        cutoff: datetime,
        include_public: bool | None = False,
        limit: int | None = None,
        session: AsyncSession | None = None,
    ) -> list[File]:
        """List files that were created before the cutoff."""
        assert session is not None, "DB session is required"

        stmt = select(File).where(File.created_at < cutoff)
        if include_public is False:
            stmt = stmt.where(File.is_public.is_(False))
        if limit is not None:
            stmt = stmt.limit(limit)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    @connection()
    async def cleanup_orphaned_files(
        self, cutoff_days: int = 30, session: AsyncSession | None = None
    ) -> int:
        """Delete files that are not referenced and older than cutoff days."""
        assert session is not None, "DB session is required"

        cutoff = datetime.utcnow().replace(tzinfo=None) - timedelta(days=cutoff_days)
        
        stmt = delete(File).where(
            File.created_at < cutoff,
            File.is_public.is_(False),
        )
        
        result = await session.execute(stmt)
        await session.flush()
        
        count = result.rowcount
        logger.info(f"Cleaned up {count} orphaned files older than {cutoff_days} days")
        return count

    @connection()
    async def mark_file_as_public(
        self, file_id: UUID, session: AsyncSession | None = None
    ) -> bool:
        """Mark file as publicly accessible."""
        assert session is not None, "DB session is required"

        stmt = update(File).where(File.id == file_id).values(is_public=True)
        result = await session.execute(stmt)
        await session.flush()

        success = result.rowcount > 0
        if success:
            logger.info(f"File marked as public: {file_id}")

        return success

    @connection()
    async def mark_file_as_private(
        self, file_id: UUID, session: AsyncSession | None = None
    ) -> bool:
        """Mark file as private."""
        assert session is not None, "DB session is required"

        stmt = update(File).where(File.id == file_id).values(is_public=False)
        result = await session.execute(stmt)
        await session.flush()

        success = result.rowcount > 0
        if success:
            logger.info(f"File marked as private: {file_id}")

        return success

