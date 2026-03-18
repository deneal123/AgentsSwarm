"""Repository-level exception hierarchy.

These exceptions are raised by data access layer helpers and mapped to
HTTP responses by the FastAPI exception handlers. They are also used by
background workers to distinguish between recoverable persistence
problems and generic runtime errors.
"""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID


class RepositoryError(Exception):
    """Base class for repository-related errors."""

    def __init__(
        self, message: str = "Repository operation failed", details: Optional[dict[str, Any]] = None
    ) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


class RepositoryIntegrityError(RepositoryError):
    """Violation of integrity constraints (unique, FK, etc.)."""

    def __init__(
        self,
        message: str = "Integrity constraint violated",
        constraint: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        details = {}
        if constraint:
            details["constraint"] = constraint
        if model:
            details["model"] = model
        super().__init__(message, details)


class RepositoryNotFoundError(RepositoryError):
    """Requested entity was not found."""

    def __init__(
        self,
        message: str = "Requested record not found",
        model: Optional[str] = None,
        identifier: Optional[Any] = None,
        field: str = "id",
    ) -> None:
        if model and identifier is not None:
            message = f"{model} not found with {field}={identifier}"
        details = {"model": model, "identifier": identifier, "field": field}
        super().__init__(message, details)


class RepositoryMultipleResultsError(RepositoryError):
    """Unexpectedly retrieved multiple rows for a single-row query."""

    def __init__(
        self,
        message: str = "Multiple records found where one was expected",
        model: Optional[str] = None,
        count: Optional[int] = None,
    ) -> None:
        if model and count:
            message = f"Expected 1 {model}, found {count}"
        details = {"model": model, "count": count}
        super().__init__(message, details)


class RepositoryOperationalError(RepositoryError):
    """Database connectivity or transient operational failure."""

    def __init__(
        self,
        message: str = "Database operation failed",
        operation: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        if original_error:
            message = f"{message}: {str(original_error)}"
        details = {
            "operation": operation,
            "original_error": str(original_error) if original_error else None,
        }
        super().__init__(message, details)


class RiskEvaluationError(RepositoryError):
    """Raised when risk evaluation fails."""

    def __init__(
        self,
        message: str = "Risk evaluation failed",
        communication_id: Optional[UUID] = None,
        risk_ids: Optional[list[str]] = None,
        original_error: Optional[Exception] = None,
    ):
        if communication_id:
            message = f"{message} for communication {communication_id}"
        if original_error:
            message = f"{message}: {str(original_error)}"
        details = {
            "communication_id": str(communication_id) if communication_id else None,
            "risk_ids": risk_ids,
            "original_error": str(original_error) if original_error else None,
        }
        super().__init__(message, details)


class PipelineQueueError(RepositoryError):
    """Raised when pipeline queue operation fails."""

    def __init__(
        self,
        message: str = "Pipeline queue operation failed",
        queue_id: Optional[UUID] = None,
        operation: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        if queue_id:
            message = f"{message} for queue {queue_id}"
        if original_error:
            message = f"{message}: {str(original_error)}"
        details = {
            "queue_id": str(queue_id) if queue_id else None,
            "operation": operation,
            "original_error": str(original_error) if original_error else None,
        }
        super().__init__(message, details)


class RuleNotFoundError(RepositoryNotFoundError):
    """Raised when a rule is not found."""

    def __init__(self, rule_id: str, additional_info: Optional[str] = None):
        message = f"Rule not found: {rule_id}"
        if additional_info:
            message = f"{message}. {additional_info}"
        super().__init__(message=message, model="Rule", identifier=rule_id, field="rule_id")


class CommunicationTaskNotFoundError(RepositoryNotFoundError):
    """Raised when a communication task is not found."""

    def __init__(self, task_id: UUID, additional_info: Optional[str] = None):
        message = f"Communication task not found: {task_id}"
        if additional_info:
            message = f"{message}. {additional_info}"
        super().__init__(message=message, model="CommunicationTask", identifier=task_id, field="id")


class AlreadyExistsError(RepositoryError):
    """Raised when attempting to create an entity that already exists."""

    def __init__(
        self,
        model: str,
        identifier: Any,
        field: str = "id",
        additional_info: Optional[str] = None,
    ):
        message = f"{model} already exists with {field}={identifier}"
        if additional_info:
            message = f"{message}. {additional_info}"
        details = {"model": model, "identifier": identifier, "field": field}
        super().__init__(message, details)


class ValidationError(RepositoryError):
    """Raised when data validation fails."""

    def __init__(
        self,
        model: str,
        field: str,
        value: Any,
        reason: str,
        additional_info: Optional[str] = None,
    ):
        message = f"Validation failed for {model}.{field}: {reason}"
        if additional_info:
            message = f"{message}. {additional_info}"
        details = {"model": model, "field": field, "value": value, "reason": reason}
        super().__init__(message, details)


class SoftDeletedError(RepositoryError):
    """Raised when attempting to access or modify a soft-deleted entity."""

    def __init__(self, model: str, identifier: Any, operation: str = "access"):
        message = f"Cannot {operation} {model} with id={identifier}: entity is soft-deleted"
        details = {"model": model, "identifier": identifier, "operation": operation}
        super().__init__(message, details)


class AlreadyDeletedError(RepositoryError):
    """Raised when attempting to delete an already deleted entity."""

    def __init__(self, model: str, identifier: Any):
        message = f"{model} with id={identifier} is already deleted"
        details = {"model": model, "identifier": identifier}
        super().__init__(message, details)


class BulkOperationError(RepositoryError):
    """Raised when a bulk operation fails."""

    def __init__(
        self,
        operation: str,
        model: str,
        total: int,
        failed: int,
        errors: Optional[list[str]] = None,
    ):
        message = f"Bulk {operation} for {model} partially failed: {failed}/{total} items failed"
        details = {
            "operation": operation,
            "model": model,
            "total": total,
            "failed": failed,
            "errors": errors or [],
        }
        super().__init__(message, details)


class DatabaseError(RepositoryError):
    """Raised when a database operation fails."""

    def __init__(
        self,
        operation: str,
        model: str,
        original_error: Optional[Exception] = None,
        additional_info: Optional[str] = None,
    ):
        message = f"Database {operation} failed for {model}"
        if additional_info:
            message = f"{message}: {additional_info}"
        if original_error:
            message = f"{message}. Original error: {str(original_error)}"
        details = {
            "operation": operation,
            "model": model,
            "original_error": str(original_error) if original_error else None,
        }
        super().__init__(message, details)


class ConcurrencyError(RepositoryError):
    """Raised when a concurrent modification is detected."""

    def __init__(self, model: str, identifier: Any, additional_info: Optional[str] = None):
        message = f"Concurrent modification detected for {model} with id={identifier}"
        if additional_info:
            message = f"{message}. {additional_info}"
        details = {"model": model, "identifier": identifier}
        super().__init__(message, details)


class UnsupportedOperationError(RepositoryError):
    """Raised when an operation is not supported by the model."""

    def __init__(self, model: str, operation: str, reason: str):
        message = f"Operation '{operation}' is not supported for {model}: {reason}"
        details = {"model": model, "operation": operation, "reason": reason}
        super().__init__(message, details)


class InvalidFilterError(RepositoryError):
    """Raised when invalid filters are provided."""

    def __init__(
        self, model: str, invalid_fields: list[str], valid_fields: Optional[list[str]] = None
    ):
        message = f"Invalid filter fields for {model}: {', '.join(invalid_fields)}"
        if valid_fields:
            message = f"{message}. Valid fields: {', '.join(valid_fields)}"
        details = {"model": model, "invalid_fields": invalid_fields, "valid_fields": valid_fields}
        super().__init__(message, details)


class PaginationError(RepositoryError):
    """Raised when pagination parameters are invalid."""

    def __init__(self, reason: str, page: Optional[int] = None, page_size: Optional[int] = None):
        message = f"Invalid pagination parameters: {reason}"
        details = {"reason": reason, "page": page, "page_size": page_size}
        super().__init__(message, details)



def raise_not_found(model_name: str, id: UUID | int | str, field: str = "id") -> None:
    """Raise RepositoryNotFoundError with standard formatting."""
    raise RepositoryNotFoundError(model=model_name, identifier=id, field=field)


def raise_already_exists(model_name: str, id: UUID | int | str, field: str = "id") -> None:
    """Raise AlreadyExistsError with standard formatting."""
    raise AlreadyExistsError(model_name, id, field)


def raise_soft_deleted(model_name: str, id: UUID | int, operation: str = "access") -> None:
    """Raise SoftDeletedError with standard formatting."""
    raise SoftDeletedError(model_name, id, operation)


def raise_validation_error(model_name: str, field: str, value: Any, reason: str) -> None:
    """Raise ValidationError with standard formatting."""
    raise ValidationError(model_name, field, value, reason)
