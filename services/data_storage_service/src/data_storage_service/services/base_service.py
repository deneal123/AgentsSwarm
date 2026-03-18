"""
Base service class with common functionality
"""

import logging
from typing import Generic, TypeVar
from uuid import UUID

from service.repositories.base_repository import BaseRepository
from service.repositories.exceptions import RepositoryNotFoundError

T = TypeVar("T", bound=BaseRepository)


class BaseService(Generic[T]):
    """Base class for all services with common functionality.

    Provides:
    - Automatic logger initialization
    - Repository access
    - Common utility methods
    - Standard error handling patterns
    """

    def __init__(self, repository: T):
        """Initialize base service.

        Args:
            repository: Repository instance for data access
        """
        self.repo = repository
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    def repository(self) -> T:
        """Typed alias for the underlying repository instance (convention used across services)."""
        return self.repo

    def _log_operation(self, operation: str, entity_type: str, entity_id: str | UUID | int) -> None:
        """Log service operation.

        Args:
            operation: Operation name (create, update, delete, etc.)
            entity_type: Entity type name
            entity_id: Entity identifier
        """
        self.logger.info(f"{operation.capitalize()} {entity_type}: {entity_id}")

    def _log_error(self, operation: str, error: Exception, context: dict | None = None) -> None:
        """Log service error with context.

        Args:
            operation: Operation that failed
            error: Exception that occurred
            context: Additional context information
        """
        context_str = f" | Context: {context}" if context else ""
        self.logger.error(f"Error in {operation}: {error}{context_str}", exc_info=True)

    def _validate_not_found(
        self, entity: object | None, entity_type: str, entity_id: str | UUID | int
    ) -> None:
        """Validate entity exists, raise RepositoryNotFoundError if not.

        Args:
            entity: Entity object or None
            entity_type: Entity type name
            entity_id: Entity identifier

        Raises:
            RepositoryNotFoundError: If entity is None
        """
        if entity is None:
            raise RepositoryNotFoundError(entity_type, entity_id)

    async def _safe_execute(
        self,
        operation: str,
        func,
        *args,
        error_handler=None,
        **kwargs,
    ):
        """Execute operation with error handling.

        Args:
            operation: Operation name for logging
            func: Function to execute
            *args: Positional arguments for func
            error_handler: Optional custom error handler
            **kwargs: Keyword arguments for func

        Returns:
            Result of func execution

        Raises:
            Exception: Re-raises exception after logging
        """
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            self._log_error(operation, e, {"args": args, "kwargs": kwargs})
            if error_handler:
                return error_handler(e)
            raise

    @staticmethod
    def _validate_pagination(limit: int, offset: int, max_limit: int = 100) -> tuple[int, int]:
        """Validate and normalize pagination parameters.

        Args:
            limit: Requested limit
            offset: Requested offset
            max_limit: Maximum allowed limit

        Returns:
            Tuple of (normalized_limit, normalized_offset)

        Raises:
            ValueError: If parameters are invalid
        """
        if limit < 1:
            raise ValueError("Limit must be at least 1")
        if offset < 0:
            raise ValueError("Offset must be non-negative")
        if limit > max_limit:
            raise ValueError(f"Limit cannot exceed {max_limit}")

        return limit, offset

    @staticmethod
    def _normalize_string(value: str | None, max_length: int | None = None) -> str | None:
        """Normalize string value (trim, lowercase, limit length).

        Args:
            value: String to normalize
            max_length: Maximum allowed length

        Returns:
            Normalized string or None
        """
        if not value:
            return None

        normalized = value.strip()
        if max_length and len(normalized) > max_length:
            normalized = normalized[:max_length]

        return normalized if normalized else None
