"""
Messaging infrastructure package.

Provides:
- Celery task management
- Redis Streams publishers/consumers
- Workers management
- Scheduled tasks
- Retry strategies
"""

from service.infrastructure.messaging import stream_helpers
from service.infrastructure.messaging.app import celery_app
from service.infrastructure.messaging.config import messaging_config
from service.infrastructure.messaging.consumers import BaseConsumer
from service.infrastructure.messaging.exceptions import (
    ConsumerError,
    PublisherError,
    StreamConsumerError,
    StreamPublishError,
    TaskExecutionError,
    TaskFatalError,
    TaskRetryableError,
    WorkerShutdownError,
)
from service.infrastructure.messaging.publishers import (
    BasePublisher,
    RedisStreamPublisher,
)
from service.infrastructure.messaging.schedulers import (
    BaseScheduler,
    CleanupScheduler,
)
from service.infrastructure.messaging.strategies import (
    ConstantRetry,
    CustomRetry,
    ExponentialBackoffRetry,
    RetryStrategy,
)

from service.infrastructure.messaging.tasks import (
    BaseTask,
    cleanup_old_streams,
)
from service.infrastructure.messaging.utils import (
    create_event_loop,
    generate_trace_id,
    get_utc_now,
    run_async_in_sync,
    safe_json_dumps,
    serialize_event,
)
from service.infrastructure.messaging.workers import (
    BaseWorker,
    MaintenanceWorker,
    WorkerManager,
)

__all__ = [
    # Core
    "celery_app",
    "messaging_config",
    # Stream helpers
    "stream_helpers",
    # Exceptions
    "TaskExecutionError",
    "TaskRetryableError",
    "TaskFatalError",
    "PublisherError",
    "ConsumerError",
    "StreamPublishError",
    "StreamConsumerError",
    "WorkerShutdownError",
    # Publishers
    "BasePublisher",
    "RedisStreamPublisher",
    # Consumers
    "BaseConsumer",
    # Strategies
    "RetryStrategy",
    "ExponentialBackoffRetry",
    "ConstantRetry",
    "CustomRetry",
    # Tasks
    "BaseTask",
    "cleanup_old_streams",
    # Workers
    "BaseWorker",
    "MaintenanceWorker",
    "WorkerManager",
    # Schedulers
    "BaseScheduler",
    "CleanupScheduler",
    # Utils
    "create_event_loop",
    "generate_trace_id",
    "get_utc_now",
    "run_async_in_sync",
    "safe_json_dumps",
    "serialize_event",
]
