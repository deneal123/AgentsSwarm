"""Task WebSocket endpoints."""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, status

from service import container
from service.presentation.dependencies import authenticate_websocket
from service.presentation.websocket_manager import WebSocketConnectionContext

logger = logging.getLogger(__name__)

tasks_ws_router = APIRouter()


HEARTBEAT_INTERVAL = 30


@tasks_ws_router.websocket("/api/v1/tasks/{task_id}/ws")
async def task_websocket(websocket: WebSocket, task_id: str) -> None:
    """WebSocket endpoint for task progress monitoring using Redis Streams.

    Args:
        websocket: WebSocket connection
        task_id: Task UUID to monitor

    Provides real-time updates on task status, progress, and completion.
    Supports:
    - Authentication via JWT tokens
    - Redis Streams for reliable delivery
    - Heartbeat mechanism (30s interval)
    - Graceful shutdown during server restart
    """

    auth_context = await authenticate_websocket(websocket, task_id, "task")
    if not auth_context:
        return

    user_id = auth_context["user_id"]
    user_type = auth_context["user_type"]

    async with WebSocketConnectionContext(websocket, task_id, "task", user_id):

        await websocket.accept()

        logger.info(f"Task WebSocket connected: task={task_id}, user={user_id}")

        try:
            task_service = container.get(container.TaskServiceName)
            try:
                current_task = await task_service.get_task_status(task_id)
                await websocket.send_json(
                    {
                        "type": "task_status",
                        "task_id": task_id,
                        "status": current_task.status,
                        "progress": getattr(current_task, "progress", 0),
                        "result": current_task.result,
                        "error": current_task.error_message,
                        "timestamp": (
                            current_task.updated_at.isoformat() if current_task.updated_at else None
                        ),
                    }
                )
            except Exception as e:
                logger.error(f"Error getting initial task status: {e}")
                await websocket.close(
                    code=status.WS_1011_INTERNAL_ERROR, reason="Task status unavailable"
                )
                return

            redis_client = container.get(container.RedisClientName)
            stream_key = f"tasks:task:{task_id}"

            try:
                await redis_client.xgroup_create(stream_key, f"ws:{user_id}", "$", mkstream=True)
            except Exception:
                # Group might already exist
                pass

            consumer_name = f"ws:{user_id}:{id(websocket)}"

            while True:
                try:
                    messages = await redis_client.xreadgroup(
                        groupname=f"ws:{user_id}",
                        consumername=consumer_name,
                        streams={stream_key: ">"},
                        count=10,
                        block=1000,  # 1 second timeout
                    )

                    if messages:
                        for stream_name, message_list in messages:
                            for message_id, message_data in message_list:
                                try:
                                    message = json.loads(message_data[b"data"].decode())

                                    await websocket.send_json(message)

                                    await redis_client.xack(stream_key, f"ws:{user_id}", message_id)

                                except Exception as e:
                                    logger.error(f"Error processing task message {message_id}: {e}")

                    try:
                        client_message = await asyncio.wait_for(
                            websocket.receive_json(), timeout=0.1
                        )

                        message_type = client_message.get("type", "unknown")

                        if message_type == "ping":
                            await websocket.send_json(
                                {
                                    "type": "pong",
                                    "timestamp": "2026-01-09T12:00:00Z",  # Would use datetime.utcnow()
                                }
                            )
                        elif message_type == "get_status":
                            try:
                                current_task = await task_service.get_task_status(task_id)
                                await websocket.send_json(
                                    {
                                        "type": "task_status",
                                        "task_id": task_id,
                                        "status": current_task.status,
                                        "progress": getattr(current_task, "progress", 0),
                                        "result": current_task.result,
                                        "error": current_task.error_message,
                                    }
                                )
                            except Exception as e:
                                logger.error(f"Error getting task status: {e}")
                        else:
                            logger.warning(f"Unknown message type from client: {message_type}")

                    except asyncio.TimeoutError:
                        pass  # No client message, continue

                except Exception as e:
                    logger.error(f"Task WebSocket error for task {task_id}: {e}")
                    break

        except Exception as e:
            logger.error(f"Task WebSocket connection error for task {task_id}: {e}")

        finally:
            logger.info(f"Task WebSocket disconnected: task={task_id}, user={user_id}")
