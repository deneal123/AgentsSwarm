"""
File scanning infrastructure for security and content analysis
"""

import hashlib
import logging
from abc import ABC, abstractmethod

from service.infrastructure.storage.abstract_file_storage import AbstractFileStorage

logger = logging.getLogger(__name__)


class FileScanner(ABC):
    """Abstract base class for file scanners."""

    @abstractmethod
    async def scan(self, file_key: str) -> dict:
        """Scan file and return results.

        Args:
            file_key: File key/path in storage

        Returns:
            Dictionary with scan results
        """
        pass


class BasicFileScanner(FileScanner):
    """Basic file scanner that computes size and SHA256 hash.

    This is a lightweight implementation. In production, this should:
    - Call an antivirus engine (ClamAV, VirusTotal, etc.)
    - Perform content analysis
    - Check file type and MIME type
    - Validate file integrity
    """

    def __init__(self, storage: AbstractFileStorage):
        """Initialize scanner.

        Args:
            storage: File storage instance
        """
        self.storage = storage

    async def scan(self, file_key: str) -> dict:
        """Scan file and compute metadata.

        Args:
            file_key: File key in storage

        Returns:
            Dictionary with scan results:
            - status: 'ok', 'error', 'skipped'
            - size: File size in bytes
            - sha256: SHA256 hash
            - reason: Error/skip reason if applicable
        """
        try:
            # Get file content from storage
            getter = getattr(self.storage, "get_file", None)
            if not callable(getter):
                logger.warning(f"Storage {type(self.storage).__name__} does not support get_file")
                return {"status": "skipped", "reason": "no_download_support"}

            data = await getter(file_key)
            if data is None:
                return {"status": "error", "reason": "file_not_found"}

            # Compute metadata
            size = len(data)
            sha256 = hashlib.sha256(data).hexdigest()

            return {
                "status": "ok",
                "size": size,
                "sha256": sha256,
                "file_key": file_key,
            }

        except Exception as e:
            logger.exception(f"File scan failed for {file_key}: {e}")
            return {
                "status": "error",
                "reason": str(e),
                "file_key": file_key,
            }


class AntivirusScanner(FileScanner):
    """Antivirus scanner using external service.

    TODO: Implement integration with:
    - ClamAV (local)
    - VirusTotal API
    - AWS GuardDuty
    """

    def __init__(self, storage: AbstractFileStorage, av_endpoint: str | None = None):
        """Initialize antivirus scanner.

        Args:
            storage: File storage instance
            av_endpoint: Antivirus service endpoint
        """
        self.storage = storage
        self.av_endpoint = av_endpoint

    async def scan(self, file_key: str) -> dict:
        """Scan file with antivirus.

        Args:
            file_key: File key in storage

        Returns:
            Dictionary with scan results
        """
        # TODO: Implement AV integration
        logger.warning("AntivirusScanner not implemented, using BasicFileScanner")
        basic_scanner = BasicFileScanner(self.storage)
        result = await basic_scanner.scan(file_key)
        result["av_status"] = "not_implemented"
        return result


class CompositeScannerStrategy(FileScanner):
    """Composite scanner that runs multiple scanners in sequence."""

    def __init__(self, scanners: list[FileScanner]):
        """Initialize composite scanner.

        Args:
            scanners: List of scanner instances
        """
        self.scanners = scanners

    async def scan(self, file_key: str) -> dict:
        """Run all scanners and aggregate results.

        Args:
            file_key: File key in storage

        Returns:
            Dictionary with aggregated scan results
        """
        results = []

        for scanner in self.scanners:
            try:
                result = await scanner.scan(file_key)
                results.append(
                    {
                        "scanner": scanner.__class__.__name__,
                        "result": result,
                    }
                )
            except Exception as e:
                logger.exception(f"Scanner {scanner.__class__.__name__} failed: {e}")
                results.append(
                    {
                        "scanner": scanner.__class__.__name__,
                        "result": {"status": "error", "reason": str(e)},
                    }
                )

        # Determine overall status
        all_ok = all(r["result"]["status"] == "ok" for r in results)
        any_error = any(r["result"]["status"] == "error" for r in results)

        return {
            "status": "ok" if all_ok else ("error" if any_error else "partial"),
            "file_key": file_key,
            "scans": results,
        }
