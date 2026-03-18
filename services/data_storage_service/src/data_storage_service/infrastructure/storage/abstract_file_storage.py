from __future__ import annotations

from typing import Protocol


class AbstractFileStorage(Protocol):
    """Protocol for file storage backends.

    Defines the contract for different storage implementations:
    - LocalFileStorage: Local filesystem
    - MinioFileStorage: S3/MinIO object storage

    All methods are async to support both local and remote storage.
    """

    def build_file_path(self, folder: str, mode: str, file_name: str) -> str:
        """Build storage key from folder, mode, and filename.

        Args:
            folder: Root folder name
            mode: File mode/type (e.g., 'document', 'image')
            file_name: File name

        Returns:
            Storage key (path)
        """
        ...

    async def upload_file(self, *, file_key: str, file_data: bytes) -> str:
        """Upload file to storage.

        Args:
            file_key: Storage key (path)
            file_data: File binary content

        Returns:
            File URL or storage reference
        """
        ...

    async def delete_file(self, *, file_key: str) -> None:
        """Delete file from storage.

        Args:
            file_key: Storage key (path)
        """
        ...

    async def get_file(self, file_key: str) -> bytes:
        """Download file from storage.

        Args:
            file_key: Storage key (path)

        Returns:
            File binary content

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        ...
