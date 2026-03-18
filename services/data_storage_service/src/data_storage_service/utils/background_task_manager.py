import asyncio
import logging

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """Manages background tasks with automatic restart on failure."""

    def __init__(self):
        self.tasks: list[asyncio.Task] = []
        self.running = False

    async def start_task_with_restart(self, coro_func, task_name: str, restart_delay: int = 5):

        async def task_wrapper():
            restart_count = 0
            while self.running:
                try:
                    logger.info(f"Starting background task: {task_name}")
                    await coro_func()
                except asyncio.CancelledError:
                    logger.info(f"Background task {task_name} was cancelled")
                    break
                except Exception:
                    restart_count += 1
                    logger.exception(
                        f"Background task {task_name} failed (attempt #{restart_count})"
                    )

                    if self.running:
                        logger.info(f"Restarting {task_name} in {restart_delay} seconds...")
                        await asyncio.sleep(restart_delay)
                    else:
                        break

            logger.info(f"Background task {task_name} stopped")

        task = asyncio.create_task(task_wrapper())
        task.set_name(task_name)
        self.tasks.append(task)
        return task

    async def start(self):
        self.running = True

    async def stop(self):
        self.running = False

        logger.info("Stopping all background tasks...")
        for task in self.tasks:
            task.cancel()

        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)

        self.tasks.clear()
        logger.info("All background tasks stopped")
