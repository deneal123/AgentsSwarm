"""Cross‑cutting logging decorators used throughout the codebase.

Originally the `log_operation` decorator lived in
``service/repositories/decorators/decorators.py`` and was intended to be used
only by repository methods. When services, tasks and other layers need
consistent call‑/result‑logging we ended up with a mix of manual
``logger.debug``/``info`` calls and the repository decorator.  To eliminate
this fragmentation we pull the decorator into the ``service.utils`` package so
that it can be imported from anywhere.

The decorator automatically picks a logger based on the module where the
wrapped function is defined; it also provides options to skip the first
``self`` argument (very common on instance methods) and to ignore named
keyword arguments such as ``session`` that are passed implicitly by other
decorators.
"""

from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Callable, Coroutine, Iterable, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def log_operation(
    log_level: int = logging.INFO,
    log_args: bool = False,
    log_result: bool = False,
    skip_first_arg: bool = True,
    skip_kwargs: Iterable[str] = ("session",),
) -> Callable[[Callable[P, Coroutine[Any, Any, R]]], Callable[P, Coroutine[Any, Any, R]]]:
    """Log a function call with optional argument/result details.

    Args:
        log_level: logging level used for all messages.
        log_args: whether to include positional and keyword arguments in the log
            message (excluding those listed in ``skip_kwargs``).
        log_result: whether to log the returned value after successful
            completion.
        skip_first_arg: if True, the first positional argument is omitted from
            the logged argument list (useful for instance methods where
            ``self`` is not interesting).
        skip_kwargs: names of keyword arguments that should not be shown in the
            log output (``session`` is a common one in repository methods).

    The returned decorator is ``async``‑aware and can be applied to any
    coroutine function.  The logger used is determined by
    ``logging.getLogger(func.__module__)`` so that log entries are grouped by
    the module where the original function lives.

    The implementation is intentionally lightweight; exception handling is
    limited to logging the stack trace and re‑raising the original exception.
    """

    def decorator(
        func: Callable[P, Coroutine[Any, Any, R]]
    ) -> Callable[P, Coroutine[Any, Any, R]]:
        logger = logging.getLogger(func.__module__)

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            name = func.__name__
            if log_args:
                parts: list[str] = []
                # positional args except ``self`` if requested
                start = 1 if skip_first_arg and len(args) > 0 else 0
                for a in args[start:]:
                    parts.append(repr(a))
                # keyword args, skipping any configured names
                for k, v in kwargs.items():
                    if k in skip_kwargs:
                        continue
                    parts.append(f"{k}={v!r}")
                logger.log(log_level, f"Calling {name}({', '.join(parts)})")
            else:
                logger.log(log_level, f"Calling {name}")

            try:
                result = await func(*args, **kwargs)
                if log_result:
                    logger.log(log_level, f"{name} completed successfully: {result!r}")
                else:
                    logger.log(log_level, f"{name} completed successfully")
                return result
            except Exception:
                logger.exception(f"{name} failed")
                raise

        return wrapper

    return decorator
