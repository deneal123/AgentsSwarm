"""Utility decorator for retrying transient errors."""

import time
from functools import wraps
from typing import Any, Callable, Sequence, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def retry(
    max_attempts: int = 3,
    delay: float = 0.5,
    backoff: float = 2.0,
    exceptions: Sequence[type[Exception]] | None = None,
) -> Callable[[F], F]:
    """Retry decorator for synchronous helpers."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None
            current_delay = delay
            cls_exceptions = tuple(exceptions) if exceptions else (Exception,)

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except cls_exceptions as exc:
                    last_exception = exc
                    if attempt == max_attempts:
                        break
                    time.sleep(current_delay)
                    current_delay *= backoff

            assert last_exception is not None
            raise last_exception

        return wrapper  # type: ignore[return-value]

    return decorator
