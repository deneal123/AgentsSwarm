"""
Unit tests for MinioFileStorage backend
Uses mocks to avoid requiring actual MinIO instance
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from service.settings import MinioConfig


@pytest.fixture
def mock_minio_config():
    """Create mock MinIO configuration"""
    config = MinioConfig(
        endpoint="minio:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        bucket="test-bucket",
        region="us-east-1",
        secure=False,
        public_endpoint="http://localhost:9000",
        retry_attempts=3,
        retry_backoff=0.5,
        presign_expiry=3600,
    )
    return config


@pytest.fixture
def minio_storage(mock_minio_config):
    """Create MinioFileStorage instance with mocked Minio client"""
    # Patch the import inside __init__ method
    with patch("minio.Minio") as mock_minio_class:
        # Create mock client
        mock_client = MagicMock()
        mock_minio_class.return_value = mock_client

        # Mock bucket_exists to return True (bucket already exists)
        mock_client.bucket_exists.return_value = True

        # Import here after patching
        from service.infrastructure.storage.minio_file_storage import MinioFileStorage

        # Create storage instance
        storage = MinioFileStorage(mock_minio_config)

        # Replace client with our mock
        storage._client = mock_client

        yield storage


class TestMinioFileStorageInit:
    """Tests for MinioFileStorage initialization"""

    def test_init_creates_bucket_if_not_exists(self, mock_minio_config):
        """Test that bucket is created if it doesn't exist"""
        with patch("minio.Minio") as mock_minio_class:
            mock_client = MagicMock()
            mock_minio_class.return_value = mock_client

            # Mock bucket doesn't exist
            mock_client.bucket_exists.return_value = False

            from service.infrastructure.storage.minio_file_storage import MinioFileStorage

            _ = MinioFileStorage(mock_minio_config)

            # Verify bucket creation was called
            mock_client.make_bucket.assert_called_once_with(
                "test-bucket", location="us-east-1"
            )

    def test_init_skips_bucket_creation_if_exists(self, mock_minio_config):
        """Test that bucket creation is skipped if bucket exists"""
        with patch("minio.Minio") as mock_minio_class:
            mock_client = MagicMock()
            mock_minio_class.return_value = mock_client

            # Mock bucket exists
            mock_client.bucket_exists.return_value = True

            from service.infrastructure.storage.minio_file_storage import MinioFileStorage

            _ = MinioFileStorage(mock_minio_config)

            # Verify bucket creation was NOT called
            mock_client.make_bucket.assert_not_called()

    def test_init_raises_on_bucket_error(self, mock_minio_config):
        """Test that RuntimeError is raised if bucket operations fail"""
        with patch("minio.Minio") as mock_minio_class:
            mock_client = MagicMock()
            mock_minio_class.return_value = mock_client

            # Mock bucket_exists raises exception
            mock_client.bucket_exists.side_effect = Exception("Connection error")

            from service.infrastructure.storage.minio_file_storage import MinioFileStorage

            with pytest.raises(RuntimeError, match="Failed to create/verify MinIO bucket"):
                MinioFileStorage(mock_minio_config)


class TestMinioFileStorageBuildFilePath:
    """Tests for build_file_path method"""

    def test_build_file_path_basic(self, minio_storage):
        """Test basic file path construction"""
        path = minio_storage.build_file_path("datasets", "user123", "test.csv")
        assert path == "datasets/user123/test.csv"


class TestMinioFileStorageUpload:
    """Tests for upload_file method"""

    @pytest.mark.asyncio
    async def test_upload_file_with_bytes(self, minio_storage):
        """Test uploading file from bytes"""
        file_data = b"test,data\n1,2\n3,4\n"
        file_key = "datasets/user123/test.csv"

        # Mock successful upload
        mock_result = Mock()
        mock_result.etag = "abc123def456"
        minio_storage._client.put_object.return_value = mock_result

        result = await minio_storage.upload_file(file_key=file_key, file_data=file_data)

        assert result == "s3://test-bucket/datasets/user123/test.csv"
        minio_storage._client.put_object.assert_called_once()

        # Verify put_object was called with correct parameters
        call_args = minio_storage._client.put_object.call_args
        assert call_args[1]["bucket_name"] == "test-bucket"
        assert call_args[1]["object_name"] == file_key
        assert call_args[1]["length"] == len(file_data)

    @pytest.mark.asyncio
    async def test_upload_file_retry_on_failure(self, minio_storage):
        """Test that upload retries on failure"""
        file_data = b"test data"
        file_key = "test.txt"

        # Mock failure on first attempt, success on second
        mock_result = Mock()
        mock_result.etag = "success"
        minio_storage._client.put_object.side_effect = [
            Exception("Network error"),
            mock_result,
        ]

        result = await minio_storage.upload_file(file_key=file_key, file_data=file_data)

        assert result == "s3://test-bucket/test.txt"
        # Should have been called twice (1 failure + 1 success)
        assert minio_storage._client.put_object.call_count == 2

    @pytest.mark.asyncio
    async def test_upload_file_fails_after_retries(self, minio_storage):
        """Test that upload raises exception after all retries fail"""
        file_data = b"test data"
        file_key = "test.txt"

        # Mock failure on all attempts
        minio_storage._client.put_object.side_effect = Exception("Persistent error")

        with pytest.raises(Exception, match="Persistent error"):
            await minio_storage.upload_file(file_key=file_key, file_data=file_data)

        # Should have been called retry_attempts times
        assert minio_storage._client.put_object.call_count == minio_storage._retry_attempts


class TestMinioFileStorageDownload:
    """Tests for get_file method"""

    @pytest.mark.asyncio
    async def test_get_file_success(self, minio_storage):
        """Test successful file download"""
        file_key = "test.txt"
        expected_data = b"test file content"

        # Mock successful download
        mock_response = Mock()
        mock_response.read.return_value = expected_data
        mock_response.close = Mock()
        mock_response.release_conn = Mock()
        minio_storage._client.get_object.return_value = mock_response

        result = await minio_storage.get_file(file_key)

        assert result == expected_data
        minio_storage._client.get_object.assert_called_once_with("test-bucket", file_key)
        mock_response.close.assert_called_once()
        mock_response.release_conn.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_file_not_found(self, minio_storage):
        """Test file download when file doesn't exist"""
        file_key = "nonexistent.txt"

        # Mock file not found
        minio_storage._client.get_object.side_effect = Exception("File not found")

        with pytest.raises(Exception, match="File not found"):
            await minio_storage.get_file(file_key)


class TestMinioFileStorageDelete:
    """Tests for delete_file method"""

    @pytest.mark.asyncio
    async def test_delete_file_success(self, minio_storage):
        """Test successful file deletion"""
        file_key = "test.txt"

        # Mock successful deletion
        minio_storage._client.remove_object.return_value = None

        await minio_storage.delete_file(file_key=file_key)

        minio_storage._client.remove_object.assert_called_once_with("test-bucket", file_key)

    @pytest.mark.asyncio
    async def test_delete_file_not_found_no_error(self, minio_storage):
        """Test that deletion doesn't raise error if file doesn't exist"""
        file_key = "nonexistent.txt"

        # Mock file not found (non-fatal)
        minio_storage._client.remove_object.side_effect = Exception("File not found")

        # Should not raise exception (non-fatal for cleanup flows)
        await minio_storage.delete_file(file_key=file_key)

        # Should have attempted deletion retry_attempts times
        assert minio_storage._client.remove_object.call_count == minio_storage._retry_attempts


class TestMinioFileStoragePresignedUrls:
    """Tests for presigned URL generation"""

    @pytest.mark.asyncio
    async def test_get_presigned_url_success(self, minio_storage):
        """Test generating presigned URL for download"""
        file_key = "test.txt"
        expected_url = "http://localhost:9000/test-bucket/test.txt?X-Amz-Signature=..."

        # Mock presigned URL generation
        minio_storage._client.presigned_get_object.return_value = expected_url

        result = await minio_storage.get_presigned_url(file_key=file_key, expiry_sec=7200)

        assert result == expected_url
        minio_storage._client.presigned_get_object.assert_called_once()

        # Verify expiry parameter
        call_args = minio_storage._client.presigned_get_object.call_args
        assert call_args[1]["bucket_name"] == "test-bucket"
        assert call_args[1]["object_name"] == file_key

    @pytest.mark.asyncio
    async def test_get_presigned_url_default_expiry(self, minio_storage):
        """Test that default expiry is used when not specified"""
        file_key = "test.txt"
        expected_url = "http://localhost:9000/test-bucket/test.txt?signature=..."

        minio_storage._client.presigned_get_object.return_value = expected_url

        # Don't specify expiry_sec
        result = await minio_storage.get_presigned_url(file_key=file_key)

        assert result == expected_url

    @pytest.mark.asyncio
    async def test_get_presigned_url_fallback_on_error(self, minio_storage):
        """Test fallback to s3:// URL when presigned generation fails"""
        file_key = "test.txt"

        # Mock presigned URL generation failure
        minio_storage._client.presigned_get_object.side_effect = Exception("Presign failed")

        result = await minio_storage.get_presigned_url(file_key=file_key)

        # Should return fallback s3:// URL
        assert result == "s3://test-bucket/test.txt"

    @pytest.mark.asyncio
    async def test_get_presigned_upload_url_success(self, minio_storage):
        """Test generating presigned URL for upload"""
        file_key = "test.txt"
        expected_url = "http://localhost:9000/test-bucket/test.txt?X-Amz-Signature=..."

        minio_storage._client.presigned_put_object.return_value = expected_url

        result = await minio_storage.get_presigned_upload_url(file_key=file_key, expiry_sec=1800)

        assert result == expected_url
        minio_storage._client.presigned_put_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_presigned_upload_url_raises_on_error(self, minio_storage):
        """Test that upload presigned URL raises exception on failure"""
        file_key = "test.txt"

        minio_storage._client.presigned_put_object.side_effect = Exception("Presign failed")

        with pytest.raises(Exception, match="Presign failed"):
            await minio_storage.get_presigned_upload_url(file_key=file_key)


class TestMinioFileStorageFileExists:
    """Tests for file_exists method"""

    def test_file_exists_true(self, minio_storage):
        """Test file_exists returns True when file exists"""
        file_key = "test.txt"

        # Mock file exists
        mock_stat = Mock()
        minio_storage._client.stat_object.return_value = mock_stat

        result = minio_storage.file_exists(file_key)

        assert result is True
        minio_storage._client.stat_object.assert_called_once_with("test-bucket", file_key)

    def test_file_exists_false(self, minio_storage):
        """Test file_exists returns False when file doesn't exist"""
        file_key = "nonexistent.txt"

        # Mock file doesn't exist
        minio_storage._client.stat_object.side_effect = Exception("Not found")

        result = minio_storage.file_exists(file_key)

        assert result is False
