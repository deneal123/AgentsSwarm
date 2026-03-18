"""
Storage infrastructure package for file persistence

Provides abstract interface and implementations for file storage:
- AbstractFileStorage: Protocol for storage backends
- LocalFileStorage: Local filesystem storage
- MinioFileStorage: S3/MinIO object storage with presigned URLs
"""

from .abstract_file_storage import AbstractFileStorage
from .local_file_storage import LocalFileStorage
from .minio_file_storage import MinioFileStorage

__all__ = [
    "AbstractFileStorage",
    "LocalFileStorage",
    "MinioFileStorage",
]
