import logging

logger = logging.getLogger(__name__)


class ChatWsMetrics:
    def __init__(self) -> None:
        try:
            from prometheus_client import Counter, Gauge

            self.connections_active = Gauge(
                "chat_connections_active", "Number of active chat WebSocket connections"
            )
            self.messages_received_total = Counter(
                "chat_messages_received_total", "Number of messages received via WebSocket"
            )
            self.events_sent_total = Counter(
                "chat_events_sent_total", "Number of events sent to WebSocket clients"
            )
            self.replay_sent_total = Counter(
                "chat_replay_sent_total", "Number of replay entries sent to websocket"
            )
            self.claimed_sent_total = Counter(
                "chat_claimed_sent_total",
                "Number of claimed entries successfully sent to websocket",
            )
            self.claimed_left_unacked_total = Counter(
                "chat_claimed_left_unacked_total",
                "Number of claimed entries that couldn't be sent and left unacked (chat)",
            )
            self.xack_errors_total = Counter(
                "chat_xack_errors_total", "Number of xack errors in chat websocket"
            )
            self.connection_errors_total = Counter(
                "chat_connection_errors_total", "Number of WebSocket connection errors"
            )
        except Exception:
            self.connections_active = None
            self.messages_received_total = None
            self.events_sent_total = None
            self.replay_sent_total = None
            self.claimed_sent_total = None
            self.claimed_left_unacked_total = None
            self.xack_errors_total = None
            self.connection_errors_total = None

    def inc(self, metric_name: str, value: float = 1.0) -> None:
        metric = getattr(self, metric_name, None)
        if metric is None:
            return
        try:
            if value == 1.0:
                metric.inc()
            else:
                metric.inc(value)
        except Exception:
            logger.debug("Failed to increment metric %s", metric_name, exc_info=True)

    def dec(self, metric_name: str) -> None:
        metric = getattr(self, metric_name, None)
        if metric is None:
            return
        try:
            metric.dec()
        except Exception:
            logger.debug("Failed to decrement metric %s", metric_name, exc_info=True)
