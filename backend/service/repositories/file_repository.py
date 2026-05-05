import logging
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from service.models.db.db_models import UserFile
from service.models.key_value import ServiceType
from service.repositories.base_repository import BseRepository
from service.repositories.decorators.session_processor import connection

logger = logging.getLogger(__name__)


class FileRepository(BseRepository):
    @connection()
    async def fetch_user_files_metadata(
        self, user_id: UUID, mode: ServiceType, session: AsyncSession | None = None
    ) -> list[UserFile]:
        assert session is not None, "DB session is required"
        result = await session.execute(
            select(UserFile).where(UserFile.user_id == user_id, UserFile.type == mode)
        )
        return list(result.scalars().all())

    @connection()
    async def fetch_user_file_by_id(
        self, user_id: UUID, file_id: UUID, session: AsyncSession | None = None
    ) -> UserFile | None:
        assert session is not None, "DB session is required"
        result = await session.execute(
            select(UserFile).where(UserFile.user_id == user_id, UserFile.id == file_id)
        )
        return result.scalar_one_or_none()

    @connection()
    async def fetch_user_file_by_name(
        self, user_id: UUID, file_name: str, session: AsyncSession | None = None
    ) -> UserFile | None:
        assert session is not None, "DB session is required"
        result = await session.execute(
            select(UserFile).where(UserFile.user_id == user_id, UserFile.file_name == file_name)
        )
        return result.scalar_one_or_none()

    @connection()
    async def add_file_metadata(
        self, file_metadata: UserFile, session: AsyncSession | None = None
    ) -> UserFile:
        assert session is not None, "DB session is required"
        logger.debug("Adding file metadata: %s", file_metadata)
        session.add(file_metadata)
        await session.flush()
        logger.debug("File metadata added: %s", file_metadata)
        return file_metadata

    @connection()
    async def delete_file_metadata(
        self, user_id: UUID, file_id: UUID, session: AsyncSession | None = None
    ) -> None:
        assert session is not None, "DB session is required"
        logger.debug(f"Deleting file metadata: user_id={user_id}, file_id={file_id}")
        await session.execute(
            delete(UserFile).where(UserFile.user_id == user_id, UserFile.id == file_id)
        )

    @connection()
    async def delete_file_metadata_by_name(
        self, user_id: UUID, file_name: str, session: AsyncSession | None = None
    ) -> None:
        assert session is not None, "DB session is required"
        logger.debug(f"Deleting file metadata: user_id={user_id}, file_name={file_name}")
        await session.execute(
            delete(UserFile).where(UserFile.user_id == user_id, UserFile.file_name == file_name)
        )
