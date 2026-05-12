import hashlib
import logging

from service.services.files.application.ports.interfaces import FileStoragePort

logger = logging.getLogger(__name__)


class FileScanner:
    """Contract for file scanners."""

    async def scan(self, file_key: str) -> dict:
        raise NotImplementedError


class BasicFileScanner(FileScanner):
    """Simple scanner that reads file content and computes basic metadata (size, sha256).

    This is intentionally lightweight: in production it should call an antivirus engine or
    content analysis pipeline and produce structured results.
    """

    def __init__(self, storage: FileStoragePort):
        self.storage = storage

    async def scan(self, file_key: str) -> dict:
        try:
            # Try storage.get_file if available
            getter = getattr(self.storage, "get_file", None)
            if callable(getter):
                data = await getter(file_key)
            else:
                # If storage doesn't support download, try presigned URL as a fallback (not ideal)
                logger.warning(
                    "Storage does not support get_file for scanning: %s", type(self.storage)
                )
                return {"status": "skipped", "reason": "no_download"}

            size = len(data) if data is not None else 0
            sha256 = hashlib.sha256(data).hexdigest() if data else None

            result = {"status": "ok", "size": size, "sha256": sha256}
            try:
                from service.monitoring import metrics as monmetrics

                monmetrics.FILE_SCANS_TOTAL.inc()
            except Exception:
                logger.debug("Failed to increment FILE_SCANS_TOTAL metric", exc_info=True)
            return result
        except Exception as e:
            try:
                from service.monitoring import metrics as monmetrics

                monmetrics.FILE_SCANS_FAILED_TOTAL.inc()
            except Exception:
                logger.debug("Failed to increment FILE_SCANS_FAILED_TOTAL metric", exc_info=True)
            logger.exception("File scan failed for %s: %s", file_key, e)
            return {"status": "error", "reason": str(e)}
