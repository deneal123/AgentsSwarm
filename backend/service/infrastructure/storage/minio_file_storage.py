import logging

from service.settings import MinioConfig

from .abstract_file_storage import AbstractFileStorage

logger = logging.getLogger(__name__)


class MinioFileStorage(AbstractFileStorage):
    """S3/MinIO storage backend with presigned URLs support.

    Uses MinioConfig from settings for configuration.
    Supports:
    - File upload/download/delete
    - Presigned URLs for secure direct access
    - Automatic bucket creation
    - Retry logic with exponential backoff
    """

    def __init__(self, config: MinioConfig) -> None:
        try:
            from minio import Minio  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "Minio client not installed. Please `pip install minio` to use MinioFileStorage"
            ) from e

        self.config = config
        self._bucket = config.bucket
        self._retry_attempts = config.retry_attempts
        self._retry_backoff = config.retry_backoff
        self._presign_expiry = config.presign_expiry
        self._public_endpoint = config.public_endpoint

        # Initialize MinIO client
        self._client = Minio(
            endpoint=config.endpoint,
            access_key=config.access_key,
            secret_key=config.secret_key,
            secure=config.secure,
            region=config.region,
        )

        # Ensure bucket exists (idempotent)
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Create bucket if it doesn't exist"""
        try:
            if not self._client.bucket_exists(self._bucket):
                self._client.make_bucket(self._bucket, location=self.config.region)
                logger.info(f"Created MinIO bucket: {self._bucket}")
            else:
                logger.debug(f"MinIO bucket exists: {self._bucket}")
        except Exception as e:
            logger.error(f"Failed to ensure bucket exists: {e}")
            raise RuntimeError(f"Failed to create/verify MinIO bucket {self._bucket}") from e

    def build_file_path(self, folder: str, mode: str, file_name: str) -> str:
        """Build S3 object key from folder, mode, and filename"""
        return f"{folder}/{mode}/{file_name}"

    async def upload_file(self, *, file_key: str, file_data: bytes) -> str:
        """Upload file to MinIO with retry logic"""
        import asyncio
        from io import BytesIO

        last_exc: Exception | None = None
        for i in range(max(1, self._retry_attempts)):
            try:
                data = BytesIO(file_data)
                length = len(file_data)
                result = self._client.put_object(
                    bucket_name=self._bucket,
                    object_name=file_key,
                    data=data,
                    length=length,
                )
                logger.info(
                    f"Uploaded file to MinIO: {file_key} (etag: {result.etag}, size: {length} bytes)"
                )
                return f"s3://{self._bucket}/{file_key}"
            except Exception as e:  # noqa: BLE001
                last_exc = e
                logger.warning(f"MinIO upload attempt {i + 1}/{self._retry_attempts} failed: {e}")
                if i < self._retry_attempts - 1:
                    await asyncio.sleep(self._retry_backoff * (2**i))
                else:
                    logger.error(
                        f"Failed to upload file {file_key} after {self._retry_attempts} attempts"
                    )
                    raise

        # Should not reach here
        if last_exc:
            raise last_exc
        return f"s3://{self._bucket}/{file_key}"

    async def delete_file(self, *, file_key: str) -> None:
        """Delete file from MinIO with retry logic"""
        import asyncio

        for i in range(max(1, self._retry_attempts)):
            try:
                self._client.remove_object(self._bucket, file_key)
                logger.info(f"Deleted file from MinIO: {file_key}")
                return
            except Exception as e:
                logger.warning(f"MinIO delete attempt {i + 1}/{self._retry_attempts} failed: {e}")
                if i < self._retry_attempts - 1:
                    await asyncio.sleep(self._retry_backoff * (2**i))
                else:
                    # Non-fatal for cleanup flows
                    logger.error(f"Failed to delete file {file_key}, but continuing")
                    return

    async def get_presigned_url(self, *, file_key: str, expiry_sec: int | None = None) -> str:
        """Generate presigned URL for direct file download.

        The URL is rewritten to use public_endpoint so it's accessible from browser.
        """
        from datetime import timedelta
        from urllib.parse import urlparse

        expiry = expiry_sec if expiry_sec is not None else self._presign_expiry

        try:
            url = self._client.presigned_get_object(
                bucket_name=self._bucket,
                object_name=file_key,
                expires=timedelta(seconds=max(1, int(expiry))),
            )
            logger.debug(f"Original presigned URL: {url}")

            # Replace internal endpoint with public endpoint for browser access
            if self._public_endpoint:
                # Build possible internal base URLs to replace
                internal_bases = [
                    f"http://{self.config.endpoint}",
                    f"https://{self.config.endpoint}",
                ]

                for internal_base in internal_bases:
                    if url.startswith(internal_base):
                        url = url.replace(internal_base, self._public_endpoint.rstrip("/"), 1)
                        break

                # Ensure the URL is absolute (has protocol)
                parsed = urlparse(url)
                if not parsed.scheme:
                    # URL doesn't have protocol, prepend public_endpoint
                    url = f"{self._public_endpoint.rstrip('/')}/{url.lstrip('/')}"

            logger.debug(f"Final presigned URL for {file_key}: {url}")
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {file_key}: {e}")
            # Fallback to s3:// style reference if presign fails
            return f"s3://{self._bucket}/{file_key}"

    async def get_presigned_upload_url(
        self, *, file_key: str, expiry_sec: int | None = None
    ) -> str:
        """Generate presigned URL for direct file upload (future use)"""
        from datetime import timedelta

        expiry = expiry_sec if expiry_sec is not None else self._presign_expiry

        try:
            url = self._client.presigned_put_object(
                bucket_name=self._bucket,
                object_name=file_key,
                expires=timedelta(seconds=max(1, int(expiry))),
            )
            logger.debug(f"Generated presigned upload URL for {file_key} (expires in {expiry}s)")
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned upload URL for {file_key}: {e}")
            raise

    def file_exists(self, file_key: str) -> bool:
        """Check if file exists in MinIO"""
        try:
            self._client.stat_object(self._bucket, file_key)
            return True
        except Exception:
            return False

    async def get_file(self, file_key: str) -> bytes:
        """Download file from MinIO"""
        try:
            response = self._client.get_object(self._bucket, file_key)
            data = response.read()
            response.close()
            response.release_conn()
            logger.debug(f"Downloaded file from MinIO: {file_key} ({len(data)} bytes)")
            return data
        except Exception as e:
            logger.error(f"Failed to download file {file_key}: {e}")
            raise
