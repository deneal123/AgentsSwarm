import logging
import time
from typing import Callable, Optional, Type

logger = logging.getLogger(__name__)


class RetryStrategy:
    def __init__(
        self,
        max_retries: int = 3,
        retry_for_exceptions: Optional[tuple[Type[Exception], ...]] = None,
    ):
        self.max_retries = max_retries
        self.retry_for_exceptions = retry_for_exceptions or (Exception,)

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        if attempt >= self.max_retries:
            return False
        return isinstance(exception, self.retry_for_exceptions)

    def get_delay(self, attempt: int) -> float:
        raise NotImplementedError


class ExponentialBackoffRetry(RetryStrategy):
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
        retry_for_exceptions: Optional[tuple[Type[Exception], ...]] = None,
    ):
        super().__init__(max_retries, retry_for_exceptions)
        self.base_delay = base_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay

    def get_delay(self, attempt: int) -> float:
        delay = self.base_delay * (self.backoff_factor**attempt)
        return min(delay, self.max_delay)


class ConstantRetry(RetryStrategy):
    def __init__(
        self,
        max_retries: int = 5,
        delay: float = 5.0,
        retry_for_exceptions: Optional[tuple[Type[Exception], ...]] = None,
    ):
        super().__init__(max_retries, retry_for_exceptions)
        self.delay = delay

    def get_delay(self, attempt: int) -> float:
        return self.delay


class CustomRetry(RetryStrategy):
    def __init__(
        self,
        max_retries: int = 3,
        delay_func: Optional[Callable[[int], float]] = None,
        retry_for_exceptions: Optional[tuple[Type[Exception], ...]] = None,
        retry_on_result: Optional[Callable[[any], bool]] = None,
    ):
        super().__init__(max_retries, retry_for_exceptions)
        self.delay_func = delay_func or (lambda attempt: 1.0)
        self.retry_on_result = retry_on_result

    def get_delay(self, attempt: int) -> float:
        return self.delay_func(attempt)

    def should_retry_on_result(self, result: any) -> bool:
        if self.retry_on_result:
            return self.retry_on_result(result)
        return False
