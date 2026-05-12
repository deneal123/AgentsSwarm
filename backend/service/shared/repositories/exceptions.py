"""Repository-level exception hierarchy.

These exceptions are raised by data access layer helpers and mapped to
HTTP responses by the FastAPI exception handlers. They are also used by
background workers to distinguish between recoverable persistence
problems and generic runtime errors.
"""

from __future__ import annotations


class RepositoryError(Exception):
    """Base class for repository-related errors."""

    def __init__(self, message: str = "Repository operation failed") -> None:
        self.message = message
        super().__init__(self.message)


class RepositoryIntegrityError(RepositoryError):
    """Violation of integrity constraints (unique, FK, etc.)."""

    def __init__(self, message: str = "Integrity constraint violated") -> None:
        super().__init__(message)


class RepositoryNotFoundError(RepositoryError):
    """Requested entity was not found."""

    def __init__(self, message: str = "Requested record not found") -> None:
        super().__init__(message)


class RepositoryMultipleResultsError(RepositoryError):
    """Unexpectedly retrieved multiple rows for a single-row query."""

    def __init__(self, message: str = "Multiple records found where one was expected") -> None:
        super().__init__(message)


class RepositoryOperationalError(RepositoryError):
    """Database connectivity or transient operational failure."""

    def __init__(self, message: str = "Database operation failed") -> None:
        super().__init__(message)
