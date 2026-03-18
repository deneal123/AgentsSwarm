"""File saver service for uploads, storage, and cleanup."""

from __future__ import annotations

import mimetypes
import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from PIL import Image, UnidentifiedImageError
from service.infrastructure.scanning import BasicFileScanner, FileScanner
from service.infrastructure.storage import AbstractFileStorage, LocalFileStorage
from service.models.db.file_models import File
from service.models.enums import FileType, StorageType
from service.models.pydantic.file import FileResponse
from service.repositories.file_repository import FileRepository
from service.services.base_service import BaseService
from service.settings import FileConfig


class FileSaverService(BaseService[FileRepository]):
    """Service for file upload, storage, and management with security scanning."""

    def __init__(
        self,
        repository: FileRepository,
        folder_name: str,
        file_storage: AbstractFileStorage | None = None,
        file_scanner: FileScanner | None = None,
        file_config: FileConfig | None = None,
        storage_backend: str | None = None,
    ) -> None:
        """Initialize file saver service.

        Args:
            repository: File repository for metadata persistence
            folder_name: Root folder name for file organization
            file_storage: Storage backend (defaults to LocalFileStorage)
            file_scanner: File scanner for security checks (defaults to BasicFileScanner)
            file_config: File configuration block
            storage_backend: Name of the backend used (affects metadata)
        """
        super().__init__(repository)
        self.storage = file_storage or LocalFileStorage()
        self.folder = folder_name
        self.scanner = file_scanner or BasicFileScanner(self.storage)
        self.file_config = file_config or FileConfig()
        backend = (storage_backend or "local").strip().lower()
        self.storage_backend = backend
        self.allowed_extensions = {ext.lower() for ext in self.file_config.allowed_extensions}

    @staticmethod
    def detect_mime_type(file_name: str) -> str:
        """Detect MIME type from file extension."""
        mime_type, _ = mimetypes.guess_type(file_name)
        return mime_type or "application/octet-stream"

    @staticmethod
    def generate_file_name(file_name: str) -> str:
        """Generate unique masked file name preserving extension."""
        return uuid.uuid4().hex + Path(file_name).suffix.lower()

    async def fetch_all_user_files(
        self,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
        file_type: FileType | None = None,
    ) -> list[FileResponse]:
        """Fetch all files for user or guest."""
        if user_id:
            self._log_operation("fetch_user_files", "User", user_id)
            files = await self.repository.get_files_by_user(user_id, file_type)
        elif guest_session_id:
            self._log_operation("fetch_guest_files", "GuestSession", guest_session_id)
            files = await self.repository.get_files_by_guest(guest_session_id, file_type)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either user_id or guest_session_id must be provided",
            )

        self._log_operation("fetch_files_completed", "Files", len(files))
        return [FileResponse.model_validate(f) for f in files]

    async def save(
        self,
        file_name: str,
        file_content: bytes,
    file_type: FileType = FileType.RESULT_JSON,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
        skip_scan: bool = False,
    ) -> FileResponse:
        """Save file to storage with security scanning and create metadata."""
        if not user_id and not guest_session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either user_id or guest_session_id must be provided",
            )

        uploader = user_id or guest_session_id
        self._log_operation("save_file", "Uploader", uploader)
        file_size = len(file_content)
        self._enforce_size_limit(file_size)
        extension = Path(file_name).suffix.lower()
        if not extension or extension not in self.allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Extension '{extension or '<unknown>'}' is not allowed",
            )

        mime_type = self.detect_mime_type(file_name)
        optimized, image_info, image_format = self._prepare_image(file_content, mime_type)
        file_size = len(optimized)
        await self._enforce_quota(user_id, file_size)

        masked_file_name = self.generate_file_name(file_name)
        file_key = self.storage.build_file_path(self.folder, file_type.value, masked_file_name)
        file_url = await self.storage.upload_file(file_key=file_key, file_data=optimized)

        scan_result = await self._run_scan(file_key, skip_scan)

        thumbnail_path = None
        thumbnail_url = None
        if image_info:
            thumb_bytes = self._generate_thumbnail(optimized, image_format)
            if thumb_bytes:
                thumbnail_path = self._build_thumbnail_key(file_key)
                thumbnail_url = await self.storage.upload_file(
                    file_key=thumbnail_path, file_data=thumb_bytes
                )

        metadata = self._build_metadata(
            scan_result=scan_result,
            extension=extension,
            mime_type=mime_type,
            storage_path=file_key,
            file_url=file_url,
            size_bytes=file_size,
            image_info=image_info,
            thumbnail_path=thumbnail_path,
            thumbnail_url=thumbnail_url,
        )

        file_record = File(
            file_name=file_name,
            file_path=file_key,
            storage_type=self._resolve_storage_type(),
            file_size=file_size,
            mime_type=mime_type,
            file_type=file_type.value,
            uploaded_by_user_id=user_id,
            uploaded_by_guest_id=guest_session_id,
            is_public=False,
            metadata_json=metadata,
        )

        saved_file = await self.repository.create_file(file_record)
        self._log_operation("file_saved", "File", saved_file.id)
        return FileResponse.model_validate(saved_file)

    async def get_presigned_url_by_key(
        self, *, file_key: str, expiry_sec: int = 3600
    ) -> str | None:
        """Get presigned URL for file access."""
        getter = getattr(self.storage, "get_presigned_url", None)
        if callable(getter):
            return await getter(file_key=file_key, expiry_sec=expiry_sec)
        return None

    async def get_access_path(self, file_id: UUID, expiry_sec: int = 3600) -> str | None:
        """Return the access path appropriate for the current storage backend.

        For **local** storage the physical filesystem path is returned so that
        the pushi library can open the file directly with ``Path(path)``.

        For **MinIO / S3** a time-limited presigned URL is returned so that any
        HTTP-capable loader (requests, httpx, etc.) can fetch the file without
        requiring local disk access.

        Args:
            file_id: UUID of the file record.
            expiry_sec: Presigned URL validity window in seconds (remote only).

        Returns:
            Path string / presigned URL, or ``None`` if the file is not found.
        """
        file = await self.repository.get_file_by_id(file_id)
        if not file:
            return None

        if self.storage_backend in ("minio", "s3"):
            url = await self.get_presigned_url_by_key(
                file_key=file.file_path, expiry_sec=expiry_sec
            )
            # Fall back to the raw key if presigned URL generation failed
            return url or file.file_path

        # Local storage — return the filesystem path directly
        return file.file_path

    async def get_file_by_key(self, *, file_key: str) -> bytes | None:
        """Get file content by storage key."""
        getter = getattr(self.storage, "get_file", None)
        if callable(getter):
            try:
                return await getter(file_key)
            except Exception as e:
                self._log_error("get_file_by_key", e, {"file_key": file_key})
                return None
        return None

    async def delete(
        self,
        file_id: UUID,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
    ) -> None:
        """Delete file from storage and metadata."""
        file = await self.repository.get_file_by_id(file_id)
        if not file:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

        # Check ownership
        if user_id and file.uploaded_by_user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        if guest_session_id and file.uploaded_by_guest_id != guest_session_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        if not user_id and not guest_session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either user_id or guest_session_id must be provided",
            )

        await self.repository.delete_file(file_id)
        await self.storage.delete_file(file_key=file.file_path)
        thumbnail_path = (file.metadata_json or {}).get("thumbnail_path")
        if thumbnail_path:
            await self.storage.delete_file(file_key=thumbnail_path)
        self._log_operation("delete_file", "File", file_id)

    async def fetch_file_metadata(
        self,
        file_id: UUID,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
    ) -> FileResponse:
        """Fetch file metadata by ID."""
        self._log_operation("fetch_file_metadata", "File", file_id)

        file = await self.repository.get_file_by_id(file_id)
        self._validate_not_found(file, "File", file_id)

        # Check ownership
        if user_id and file.uploaded_by_user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        if guest_session_id and file.uploaded_by_guest_id != guest_session_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

        return FileResponse.model_validate(file)

    async def scan_file(self, file_id: UUID) -> dict:
        """Scan existing file for security threats."""
        self._log_operation("scan_file", "File", file_id)

        file = await self.repository.get_file_by_id(file_id)
        self._validate_not_found(file, "File", file_id)

        scan_result = await self.scanner.scan(file.file_path)
        if scan_result.get("status") == "ok":
            self._log_operation("scan_file_ok", "File", file_id)
        else:
            self._log_error(
                "scan_file_failed",
                Exception(scan_result.get("reason", "Unknown")),
                {"file_id": file_id, "scan_result": scan_result},
            )
        return scan_result

    async def cleanup_temporary_files(self) -> int:
        """Remove temporary files older than the retention window."""
        if self.file_config.temporary_retention_days <= 0:
            return 0

        cutoff = datetime.now(timezone.utc) - timedelta(
            days=self.file_config.temporary_retention_days
        )
        files = await self.repository.list_files_older_than(
            cutoff,
            include_public=False,
            limit=self.file_config.temporary_cleanup_batch_size,
        )

        removed = 0
        for file in files:
            try:
                await self.storage.delete_file(file_key=file.file_path)
                thumbnail_path = (file.metadata_json or {}).get("thumbnail_path")
                if thumbnail_path:
                    await self.storage.delete_file(file_key=thumbnail_path)
                await self.repository.delete_file(file.id)
                removed += 1
            except Exception as exc:
                self.logger.exception("Temporary cleanup failed for %s: %s", file.id, exc)

        if removed:
            self.logger.info("Cleaned up %s temporary files", removed)
        return removed

    def _resolve_storage_type(self) -> StorageType:
        return StorageType.S3 if self.storage_backend in ("minio", "s3") else StorageType.LOCAL

    def _enforce_size_limit(self, size: int) -> None:
        max_bytes = self.file_config.max_size_mb * 1024 * 1024
        if max_bytes > 0 and size > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds limit of {self.file_config.max_size_mb}MB",
            )

    async def _enforce_quota(self, user_id: UUID | None, incoming: int) -> None:
        quota = self.file_config.storage_quota_mb * 1024 * 1024
        if quota <= 0 or not user_id:
            return
        used = await self.repository.get_user_storage_usage(user_id)
        if used + incoming > quota:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="User storage quota exceeded",
            )

    async def _run_scan(self, file_key: str, skip_scan: bool) -> dict:
        if skip_scan or not self.file_config.scan_on_upload:
            return {"status": "skipped", "reason": "scan disabled"}
        try:
            result = await self.scanner.scan(file_key)
            if result.get("status") == "error":
                await self.storage.delete_file(file_key=file_key)
            return result
        except Exception as exc:
            self._log_error("file_scan_error", exc, {"file_key": file_key})
            return {"status": "error", "reason": str(exc)}

    def _prepare_image(
        self, data: bytes, mime_type: str
    ) -> tuple[bytes, dict[str, int] | None, str | None]:
        if not mime_type.startswith("image/") or not self.file_config.optimize_images:
            return data, None, None
        try:
            with Image.open(BytesIO(data)) as im:
                original_format = im.format or "JPEG"
                width, height = im.size
                im.thumbnail(
                    (self.file_config.image_max_width, self.file_config.image_max_height),
                    Image.LANCZOS,
                )
                buffer = BytesIO()
                save_kwargs: dict[str, Any] = {"format": original_format}
                if original_format.upper() in ("JPEG", "JPG"):
                    save_kwargs.update(
                        {"quality": self.file_config.image_quality, "optimize": True}
                    )
                im.save(buffer, **save_kwargs)
                optimized = buffer.getvalue()
                return optimized, {"width": width, "height": height}, original_format
        except (UnidentifiedImageError, OSError):
            return data, None, None

    def _generate_thumbnail(self, data: bytes, image_format: str | None) -> bytes | None:
        if not data:
            return None
        try:
            with Image.open(BytesIO(data)) as im:
                im.thumbnail(
                    (self.file_config.thumbnail_size, self.file_config.thumbnail_size),
                    Image.LANCZOS,
                )
                buffer = BytesIO()
                fmt = (image_format or im.format or "JPEG").upper()
                save_kwargs: dict[str, Any] = {"format": fmt}
                if fmt in ("JPEG", "JPG"):
                    save_kwargs.update(
                        {"quality": self.file_config.thumbnail_quality, "optimize": True}
                    )
                im.save(buffer, **save_kwargs)
                return buffer.getvalue()
        except (UnidentifiedImageError, OSError):
            return None

    def _build_thumbnail_key(self, primary_key: str) -> str:
        path = Path(primary_key)
        return str(path.parent / self.file_config.thumbnail_folder / path.name)

    def _build_metadata(
        self,
        *,
        scan_result: dict,
        extension: str,
        mime_type: str,
        storage_path: str,
        file_url: str,
        size_bytes: int,
        image_info: dict[str, int] | None,
        thumbnail_path: str | None,
        thumbnail_url: str | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "scan_result": scan_result,
            "extension": extension,
            "mime_type": mime_type,
            "storage_backend": self.storage_backend,
            "storage_path": storage_path,
            "file_url": file_url,
            "size_bytes": size_bytes,
        }
        if image_info:
            payload["image"] = image_info
        if thumbnail_path:
            payload["thumbnail_path"] = thumbnail_path
        if thumbnail_url:
            payload["thumbnail_url"] = thumbnail_url
        return payload
