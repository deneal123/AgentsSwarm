class TaskExecutionError(Exception):
    pass


class TaskRetryableError(Exception):
    pass


class TaskFatalError(Exception):
    pass


class PublisherError(Exception):
    pass


class ConsumerError(Exception):
    pass


class WorkerShutdownError(Exception):
    pass


class StreamPublishError(PublisherError):
    pass


class StreamConsumerError(ConsumerError):
    pass
