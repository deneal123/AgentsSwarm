from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    attempts: int = 3
    backoff_sec: float = 0.5
    max_backoff_sec: float = 5.0


@dataclass(frozen=True, slots=True)
class TimeoutPolicy:
    timeout_sec: float
