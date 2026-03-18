"""Mock decorators to simplify repository testing."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Coroutine, Iterable, Mapping


class AsyncDecoratorMock:
    """Track calls to async decorators and expose noop wrappers."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[Mapping[str, Any]] = []

    def _wrap(self, func: Callable[..., Coroutine[Any, Any, Any]], options: Mapping[str, Any]) -> Callable[..., Coroutine[Any, Any, Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            self.calls.append({"options": options, "args": args, "kwargs": kwargs})
            return await func(*args, **kwargs)

        return wrapper

    def __call__(self, *args: Any, **kwargs: Any) -> Callable[[Callable[..., Coroutine[Any, Any, Any]]], Callable[..., Coroutine[Any, Any, Any]]]:
        if args and callable(args[0]) and not kwargs:
            return self._wrap(args[0], {"args": (), "kwargs": {}})

        options = {"args": args, "kwargs": kwargs}

        def decorator(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
            return self._wrap(func, options)

        return decorator


@dataclass
class RepositoryDecoratorMocks:
    """Container for decorator spies used in tests."""

    cache: AsyncDecoratorMock = field(default_factory=lambda: AsyncDecoratorMock("cache"))
    retry: AsyncDecoratorMock = field(default_factory=lambda: AsyncDecoratorMock("retry"))
    monitor_performance: AsyncDecoratorMock = field(default_factory=lambda: AsyncDecoratorMock("monitor_performance"))
    connection: AsyncDecoratorMock = field(default_factory=lambda: AsyncDecoratorMock("connection"))

    @property
    def all(self) -> Iterable[AsyncDecoratorMock]:
        return (self.cache, self.retry, self.monitor_performance, self.connection)


def patch_repository_decorators(monkeypatch: Any) -> RepositoryDecoratorMocks:
    """Apply noop mocks to repository decorators and return trackers."""

    mocks = RepositoryDecoratorMocks()

    import service.repositories.decorators as repo_decorators
    from service.infrastructure.monitoring.decorators import (
        repository_decorators as monitoring_decorators,
    )

    monkeypatch.setattr(repo_decorators, "cache", mocks.cache)
    monkeypatch.setattr(repo_decorators, "retry", mocks.retry)
    monkeypatch.setattr(repo_decorators, "monitor_performance", mocks.monitor_performance)
    monkeypatch.setattr(repo_decorators, "connection", mocks.connection)
    monkeypatch.setattr(monitoring_decorators, "monitor_repository", mocks.monitor_performance)
    monkeypatch.setattr(monitoring_decorators, "monitor_performance", mocks.monitor_performance)

    return mocks
