import logging
import uuid
from pathlib import Path

from fastapi import HTTPException, status

from service.infrastructure.storage.local_file_storage import LocalFileStorage
from service.files.application.ports.interfaces import FileStoragePort, MessageBusPort
from service.models.db.db_models import UserFile
from service.models.file_models import FileMetadataLogic
from service.models.key_value import ServiceType
from service.presentation.routers.files_api.schemas import (
    FetchUserFilesResponse,
    FileMetadata,
    UploadResponse,
)
from service.repositories.file_repository import FileRepository

logger = logging.getLogger(__name__)


class FileSaverService:
    def __init__(
        self,
        repository: FileRepository,
        folder_name: str,
        file_storage: FileStoragePort | None = None,
        message_bus: MessageBusPort | None = None,
    ) -> None:
        self.storage = file_storage or LocalFileStorage()
        self.message_bus = message_bus
        self.repository = repository
        self.folder = folder_name

    async def fetch_all_user_files(
        self, user_id: uuid.UUID, mode: ServiceType
    ) -> FetchUserFilesResponse:
        logger.info(f"Fetching all files for user: {user_id}")

        user_files = await self.repository.fetch_user_files_metadata(user_id, mode)

        logger.info(f"Fetched {len(user_files)} files for user: {user_id}")

        if not user_files:
            return FetchUserFilesResponse(files=[])

        logger.debug(f"User files: {user_files}")

        response = FetchUserFilesResponse(
            files=[FileMetadata(file_id=file.id, file_url=file.file_url) for file in user_files]
        )
        return response

    async def save(
        self,
        user_id: uuid.UUID,
        mode: ServiceType,
        file_name: str,
        file_content: bytes,
    ) -> UploadResponse:

        masked_file_name = self._generate_file_name(file_name)

        file_key = self.storage.build_file_path(self.folder, mode.value, masked_file_name)

        file_url = await self.storage.upload_file(
            file_key=file_key,
            file_data=file_content,
        )

        file_metadata = UserFile(
            user_id=user_id,
            type=mode,
            file_name=file_key,
            file_url=file_url,
        )

        saved_metadata = await self.repository.add_file_metadata(file_metadata)
        logger.info(
            f"File metadata saved for user: {user_id}, file: {file_url}, metadata: {saved_metadata.id}"
        )
        return UploadResponse(file_id=saved_metadata.id, file_url=file_url, file_key=file_key)

    async def get_presigned_url_by_key(
        self, *, file_key: str, expiry_sec: int = 3600
    ) -> str | None:
        # Duck-typing: only works if storage supports it
        getter = getattr(self.storage, "get_presigned_url", None)
        if callable(getter):
            return await getter(file_key=file_key, expiry_sec=expiry_sec)
        return None

    async def get_file_by_key(self, *, file_key: str) -> bytes | None:
        """Get file content by storage key.

        Returns file bytes or None if not supported/found.
        """
        getter = getattr(self.storage, "get_file", None)
        if callable(getter):
            try:
                return await getter(file_key)
            except Exception:
                return None
        return None

    async def delete(self, user_id: uuid.UUID, file_id: uuid.UUID) -> None:

        user_file = await self.repository.fetch_user_file_by_id(user_id, file_id)
        if not user_file:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

        await self.repository.delete_file_metadata(user_id=user_id, file_id=file_id)
        storage_file_key = user_file.file_name
        await self.storage.delete_file(file_key=storage_file_key)

    async def fetch_file_metadata(
        self, user_id: uuid.UUID, file_id: uuid.UUID
    ) -> FileMetadataLogic:
        logger.info(f"Fetching file metadata for user: {user_id}, file: {file_id}")
        user_file = await self.repository.fetch_user_file_by_id(user_id, file_id)
        if not user_file:
            logger.error(f"File not found for user: {user_id}, file: {file_id}")
            raise ValueError("File not found")
        return FileMetadataLogic(file_id=user_file.id, file_url=user_file.file_url)

    async def presign_upload(self, user_id, mode: ServiceType, file_name: str, expiry_sec: int | None = None) -> dict:
        """Prepare a presigned upload URL and return temporary identifiers.

        Does not persist metadata; client must call callback to finalize.
        """
        import uuid

        masked_file_name = self._generate_file_name(file_name)
        file_key = self.storage.build_file_path(self.folder, mode.value, masked_file_name)
        # Generate presigned upload URL if storage supports it
        getter = getattr(self.storage, "get_presigned_upload_url", None)
        upload_url = None
        if callable(getter):
            try:
                upload_url = await getter(file_key=file_key, expiry_sec=expiry_sec)
            except Exception:
                logger.exception("Failed to generate presigned upload URL for %s", file_key)
                upload_url = None
        # return temporary id (caller to persist on callback)
        return {"file_id": uuid.uuid4(), "file_key": file_key, "upload_url": upload_url}

    async def finalize_upload(self, user_id, mode: ServiceType, file_id, file_key: str) -> dict:
        """Persist metadata after upload completion and return stored metadata."""
        # Determine public URL: prefer presigned download URL, fallback to storage path
        download_getter = getattr(self.storage, "get_presigned_url", None)
        if callable(download_getter):
            try:
                file_url = await download_getter(file_key=file_key)
            except Exception:
                logger.exception("Failed to obtain presigned download URL for %s", file_key)
                file_url = file_key
        else:
            # Fallback to raw file key or local path
            file_url = file_key

        file_metadata = UserFile(user_id=user_id, type=mode, file_name=file_key, file_url=file_url)
        saved = await self.repository.add_file_metadata(file_metadata)
        if self.message_bus is not None:
            try:
                await self.message_bus.push("file:scan:queue", saved.file_name)
            except Exception:
                logger.debug("Failed to enqueue file scan job", exc_info=True)

        return {"file_id": saved.id, "file_url": saved.file_url}

    def _generate_file_name(self, file_name: str) -> str:
        logger.debug(f"Original file name: {file_name}")

        masked_file_name = uuid.uuid4().hex + Path(file_name).suffix.lower()
        logger.debug(f"Masked file name: {masked_file_name}")

        return masked_file_name
