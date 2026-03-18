import logging
from typing import Dict, Set
from uuid import UUID

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:

    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {
            "task": set(),
        }
        self._websocket_metadata: Dict[WebSocket, dict] = {}
        self._shutdown_initiated = False

    def register_connection(
        self,
        websocket: WebSocket,
        resource_id: str,
        resource_type: str = "chat",
        user_id: str | None = None,
    ) -> None:
        """Register an active WebSocket connection.

        Args:
            websocket: The WebSocket connection to register
            resource_id: The resource identifier (thread_id, task_id, etc.)
            resource_type: Type of resource ('chat' or 'task')
            user_id: Optional user identifier for logging
        """
        if resource_type not in self._connections:
            self._connections[resource_type] = set()

        self._connections[resource_type].add(websocket)
        self._websocket_metadata[websocket] = {
            "resource_id": resource_id,
            "resource_type": resource_type,
            "user_id": user_id,
        }

        logger.debug(
            f"WebSocket registered: type={resource_type}, "
            f"resource={resource_id}, user={user_id}, "
            f"total={self.get_total_connections()}"
        )

    def unregister_connection(self, websocket: WebSocket) -> None:
        metadata = self._websocket_metadata.pop(websocket, None)

        if metadata:
            resource_type = metadata["resource_type"]
            if resource_type in self._connections:
                self._connections[resource_type].discard(websocket)

            logger.debug(
                f"WebSocket unregistered: type={resource_type}, "
                f"resource={metadata['resource_id']}, "
                f"user={metadata['user_id']}, "
                f"total={self.get_total_connections()}"
            )

    async def close_all_connections(
        self, code: int = 1001, reason: str = "Server shutdown"
    ) -> None:
        self._shutdown_initiated = True

        total_connections = self.get_total_connections()
        logger.info(f"Closing {total_connections} active WebSocket connections...")

        closed_count = 0
        error_count = 0

        for resource_type, connections in self._connections.items():
            logger.info(f"Closing {len(connections)} {resource_type} WebSocket connections...")

            for websocket in list(
                connections
            ):  # Use list() to avoid set modification during iteration
                try:
                    await websocket.close(code=code, reason=reason)
                    closed_count += 1
                    logger.debug(f"Closed WebSocket: type={resource_type}")
                except Exception as e:
                    error_count += 1
                    logger.warning(f"Error closing WebSocket: {e}")
                finally:
                    self._websocket_metadata.pop(websocket, None)

            connections.clear()

        logger.info(
            f"WebSocket shutdown complete: "
            f"closed={closed_count}, errors={error_count}, total={total_connections}"
        )

    def get_total_connections(self) -> int:
        return sum(len(connections) for connections in self._connections.values())

    def get_connections_by_type(self, resource_type: str) -> int:
        return len(self._connections.get(resource_type, set()))

    def is_shutdown_initiated(self) -> bool:
        return self._shutdown_initiated

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close all connections."""
        await self.close_all_connections()


ws_manager = WebSocketManager()


class WebSocketConnectionContext:
    """Context manager for tracking individual WebSocket connections.

    Usage:
        async with WebSocketConnectionContext(websocket, thread_id, "chat", user_id):
            await websocket.accept()
            # Your WebSocket logic
    """

    def __init__(
        self,
        websocket: WebSocket,
        resource_id: str,
        resource_type: str = "chat",
        user_id: str | None = None,
    ):
        self.websocket = websocket
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.user_id = user_id

    async def __aenter__(self):
        """Register connection on context entry."""
        ws_manager.register_connection(
            self.websocket,
            self.resource_id,
            self.resource_type,
            self.user_id,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        ws_manager.unregister_connection(self.websocket)
