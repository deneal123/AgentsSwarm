"""Base class for logic layer.

The logic layer sits between API routers and services.
It contains business logic and orchestrates service calls.
Logic classes MUST NOT use repositories directly - only services.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from service.container import Container

logger = logging.getLogger(__name__)


class BaseLogic:
    """Base class for all logic components.
    
    Provides:
    - Access to container for service dependency injection
    - Common logging setup
    - Transaction context helpers
    
    Usage:
        class MyLogic(BaseLogic):
            async def do_something(self):
                service = self.container.my_service()
                result = await service.do_work()
                return result
    """

    def __init__(self, container: Container | None = None):
        self._container = container
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @property
    def container(self) -> Container:
        """Get the DI container.
        
        Raises:
            RuntimeError: If container not set
        """
        if self._container is None:
            import service.container as _container_module
            self._container = _container_module
        return self._container
    
    def set_container(self, container: Container) -> None:
        """Set the DI container (for testing)."""
        self._container = container
