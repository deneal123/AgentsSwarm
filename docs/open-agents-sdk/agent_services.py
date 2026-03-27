import asyncio
import logging
from typing import Dict

from service.agents.pydantic.models import AgentsQuery, AgentsResponse
from fastapi import HTTPException, status
from service.agents.modules.buffers import buffer_llm_query, buffer_llm_responses

logger = logging.getLogger(__name__)


# TODO: Consider encapsulating this into a class to avoid module-level global state and
# support clean shutdown in tests / application lifecycle.
response_waiting_pool: Dict[str, asyncio.Future] = {}
background_task: asyncio.Task | None = None


async def agents_query(query: AgentsQuery) -> AgentsResponse:
    """Submit an agents query and wait for the LLM pipeline to produce a response.

    Behavior:
    - Ensure the background consumer is running
    - Put query into queue and wait on a Future keyed by user_id
    - Timeout after 60s with 504
    """
    global background_task

    # Ensure background consumer is started
    if background_task is None or background_task.done():
        background_task = asyncio.create_task(process_response_queue())

    fut: asyncio.Future = asyncio.get_event_loop().create_future()
    response_waiting_pool[str(query.user_id)] = fut

    buffer_llm_query.put(query)
    logger.info("Added request to LLM queue: %s", query)

    try:
        response = await asyncio.wait_for(fut, timeout=60.0)
        response_waiting_pool.pop(str(query.user_id), None)
        return response
    except asyncio.TimeoutError:
        response_waiting_pool.pop(str(query.user_id), None)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Время ожидания ответа от ассистента истекло",
        )


async def process_response_queue():
    """Background consumer that pulls responses from buffer and matches them to waiting futures.

    Gracefully handles failures and yields to event loop.
    """
    logger.info("Starting response consumer")
    try:
        while True:
            try:
                if not buffer_llm_responses.empty():
                    response = buffer_llm_responses.get()
                    matched = False

                    user_id = getattr(response, "user_id", None)
                    if user_id and user_id in response_waiting_pool:
                        future = response_waiting_pool[user_id]
                        if not future.done():
                            future.set_result(response)
                            matched = True

                    if not matched:
                        logger.info("No waiting consumer for response, returning to queue: %s", response)
                        buffer_llm_responses.put(response)
                        await asyncio.sleep(0.5)
            except Exception:
                logger.exception("Error processing response queue")

            await asyncio.sleep(0.1)
    finally:
        logger.info("Response consumer stopped")