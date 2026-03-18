"""File logic - business layer for file operations.

Handles file uploads, validation, and processing tasks.
Uses FileSaverService and TaskOrchestratorService.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from service.logics.base_logic import BaseLogic
from service.models.enums import FileType, TaskStatus


class FileLogic(BaseLogic):
    """Business logic for file operations.
    
    This logic layer:
    1. Validates file uploads
    2. Saves files via FileSaverService
    3. Creates processing tasks for configs and datasets
    4. Manages file metadata
    """

    # Allowed file extensions by type
    ALLOWED_CONFIG_EXTENSIONS = {".yaml", ".toml"}
    ALLOWED_DATASET_EXTENSIONS = {".xlsx"}
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

    async def upload_config(
        self,
        file_content: bytes,
        file_name: str,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Upload and validate a configuration file.
        
        Args:
            file_content: Raw file bytes
            file_name: Original file name
            user_id: User ID if authenticated
            guest_session_id: Guest session ID if guest
            
        Returns:
            Dict with:
                - file_id: saved file ID
                - task_id: validation task ID
                - status: upload status
        """
        # Validate authentication
        if not user_id and not guest_session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Validate file
        self._validate_file_size(file_content)
        self._validate_config_extension(file_name)
        
        # Create upload task
        orchestrator = self.container.task_orchestrator_service()
        
        task = await orchestrator.create_file_upload_task(
            file_content=file_content,
            file_name=file_name,
            file_type=FileType.CONFIG_YAML,
            user_id=user_id,
            guest_session_id=guest_session_id,
        )
        
        return {
            "file_id": task.file_id,
            "task_id": task.id,
            "status": task.status,
            "file_name": file_name,
            "message": "Config file uploaded and queued for validation",
        }
    
    async def upload_dataset(
        self,
        file_content: bytes,
        file_name: str,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Upload and validate a dataset file.
        
        Args:
            file_content: Raw file bytes
            file_name: Original file name
            user_id: User ID if authenticated
            guest_session_id: Guest session ID if guest
            
        Returns:
            Dict with:
                - file_id: saved file ID
                - task_id: validation task ID
                - status: upload status
        """
        # Validate authentication
        if not user_id and not guest_session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Validate file
        self._validate_file_size(file_content)
        self._validate_dataset_extension(file_name)
        
        # Create upload task
        orchestrator = self.container.task_orchestrator_service()
        
        task = await orchestrator.create_file_upload_task(
            file_content=file_content,
            file_name=file_name,
            file_type=FileType.DATASET,
            user_id=user_id,
            guest_session_id=guest_session_id,
        )
        
        return {
            "file_id": task.file_id,
            "task_id": task.id,
            "status": task.status,
            "file_name": file_name,
            "message": "Dataset file uploaded and queued for validation",
        }
    
    async def get_file_info(self, file_id: UUID) -> dict[str, Any] | None:
        """Get information about a file.

        Args:
            file_id: File ID

        Returns:
            File info dict or None if not found
        """
        file_repo = self.container.file_repository()
        file_record = await file_repo.get_file_by_id(file_id)

        if not file_record:
            return None

        return {
            "file_id": file_record.id,
            "file_name": file_record.file_name,
            "file_path": file_record.file_path,
            "file_type": file_record.file_type,
            "file_size": file_record.file_size,
            "mime_type": file_record.mime_type,
            "storage_type": file_record.storage_type,
            "is_public": file_record.is_public,
            "uploaded_by_user_id": file_record.uploaded_by_user_id,
            "uploaded_by_guest_id": file_record.uploaded_by_guest_id,
            "created_at": file_record.created_at,
        }

    async def get_upload_task_status(
        self,
        task_id: UUID,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
    ) -> dict[str, Any] | None:
        """Get status of a file upload processing task.

        Returns full task info including file_id, result (validation errors, etc.)
        and error details if processing failed.

        Args:
            task_id: Task ID returned by upload endpoint
            user_id: Authenticated user ID (for ownership check)
            guest_session_id: Guest session ID (for ownership check)

        Returns:
            Task status dict or None if not found
        """
        orchestrator = self.container.task_orchestrator_service()
        task = await orchestrator.get_task(task_id)

        if not task:
            return None

        # Ownership check
        if user_id and task.user_id and task.user_id != user_id:
            return None
        if guest_session_id and task.guest_session_id and task.guest_session_id != guest_session_id:
            return None

        return {
            "task_id": task.id,
            "file_id": task.file_id,
            "status": task.status,
            "task_type": task.task_type,
            "file_name": (task.payload or {}).get("original_file_name"),
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "error_message": task.error_message,
            "result": task.result,
        }

    async def list_user_files(
        self,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
        file_type: FileType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List files for a user, optionally filtered by file_type.

        Args:
            user_id: Registered user ID
            guest_session_id: Guest session ID
            file_type: Optional FileType filter (e.g. FileType.CONFIG_YAML, FileType.DATASET)
            limit: Max results
            offset: Pagination offset

        Returns:
            List of file info dicts
        """
        file_repo = self.container.file_repository()

        if user_id:
            files = await file_repo.get_files_by_user(
                user_id=user_id,
                file_type=file_type,
                limit=limit,
                offset=offset,
            )
        elif guest_session_id:
            files = await file_repo.get_files_by_guest(
                guest_session_id=guest_session_id,
                file_type=file_type,
                limit=limit,
                offset=offset,
            )
        else:
            files = []

        return [
            {
                "file_id": f.id,
                "file_name": f.file_name,
                "file_path": f.file_path,
                "file_type": f.file_type,
                "file_size": f.file_size,
                "mime_type": f.mime_type,
                "storage_type": f.storage_type,
                "is_public": f.is_public,
                "uploaded_by_user_id": f.uploaded_by_user_id,
                "uploaded_by_guest_id": f.uploaded_by_guest_id,
                "created_at": f.created_at,
            }
            for f in files
        ]
    
    async def delete_file(
        self,
        file_id: UUID,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
    ) -> bool:
        """Delete a file and its associated data.
        
        Args:
            file_id: File ID
            user_id: User ID for verification
            guest_session_id: Guest session ID for verification
            
        Returns:
            True if deleted
        """
        file_repo = self.container.file_repository()
        file_saver = self.container.file_saver_service()

        # Get file
        file_record = await file_repo.get_file_by_id(file_id)
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )

        # Verify ownership
        if (
            file_record.uploaded_by_user_id != user_id
            and file_record.uploaded_by_guest_id != guest_session_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this file"
            )
        
        # Check if file is used by active tasks
        # Tasks stuck in pending/processing for more than 30 minutes are considered stale
        STALE_TASK_THRESHOLD = timedelta(minutes=30)
        now = datetime.now(timezone.utc)

        task_repo = self.container.task_repository()
        active_tasks = await task_repo.get_tasks_by_user(
            user_id=user_id,
            guest_session_id=guest_session_id,
            limit=1000,
        )
        
        for task in active_tasks:
            if task.file_id == file_id and task.status in (
                TaskStatus.PENDING.value,
                TaskStatus.PROCESSING.value,
                TaskStatus.NEW.value,
            ):
                # Allow deletion if task is stale (stuck for more than 30 min)
                task_age = now - task.created_at.replace(tzinfo=timezone.utc)
                if task_age < STALE_TASK_THRESHOLD:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot delete file used by active tasks"
                    )
        
        # Delete physical file and database record via FileSaverService
        # (it handles ownership check, storage deletion, and DB deletion internally)
        await file_saver.delete(file_id, user_id=user_id, guest_session_id=guest_session_id)

        return True
    
    async def read_file_content(
        self,
        file_id: UUID,
    ) -> tuple[bytes, str] | None:
        """Read raw bytes of an already-uploaded file from storage.

        Args:
            file_id: ID of the file record.

        Returns:
            Tuple of (file_bytes, file_name) or None if file not found.
        """
        file_repo = self.container.file_repository()
        file_record = await file_repo.get_file_by_id(file_id)
        if not file_record:
            return None

        file_saver = self.container.file_saver_service()
        file_bytes = await file_saver.get_file_by_key(file_key=file_record.file_path)
        if file_bytes is None:
            return None

        return file_bytes, file_record.file_name

    def _validate_file_size(self, file_content: bytes) -> None:
        """Validate file size.
        
        Args:
            file_content: File bytes
            
        Raises:
            HTTPException: If file too large
        """
        if len(file_content) > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {self.MAX_FILE_SIZE / 1024 / 1024:.0f} MB"
            )
    
    def _validate_config_extension(self, file_name: str) -> None:
        """Validate config file extension.
        
        Args:
            file_name: File name
            
        Raises:
            HTTPException: If invalid extension
        """
        ext = "." + file_name.split(".")[-1].lower() if "." in file_name else ""
        if ext not in self.ALLOWED_CONFIG_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid config file type. Allowed: {', '.join(self.ALLOWED_CONFIG_EXTENSIONS)}"
            )
    
    def _validate_dataset_extension(self, file_name: str) -> None:
        """Validate dataset file extension.
        
        Args:
            file_name: File name
            
        Raises:
            HTTPException: If invalid extension
        """
        ext = "." + file_name.split(".")[-1].lower() if "." in file_name else ""
        if ext not in self.ALLOWED_DATASET_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid dataset file type. Allowed: {', '.join(self.ALLOWED_DATASET_EXTENSIONS)}"
            )
