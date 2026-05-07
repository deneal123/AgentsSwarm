from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ChatRequestContext:
    thread_id: str
    text: str
    user_id: str | int | None
    selected_model: str | None = None
    input_type: str | None = None
    web_search: bool = False
    deep_research: bool = False
    file_context: str = ""
    route_override: str | None = None


@dataclass(slots=True)
class ChatProcessingMetadata:
    data: dict[str, Any] = field(default_factory=dict)

    def merged(self, extra: dict[str, Any]) -> "ChatProcessingMetadata":
        return ChatProcessingMetadata(data={**self.data, **extra})

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self.data[key]


@dataclass(slots=True)
class ChatRouteDecision:
    selected_model: str | None
    routing_metadata: dict[str, Any] = field(default_factory=dict)
    web_search: bool = False
    deep_research: bool = False
    route_override: str | None = None


@dataclass(slots=True)
class ChatReplyResult:
    reply: str
    thread_id: str | None
    file_url: str | None = None
    metadata: ChatProcessingMetadata = field(default_factory=ChatProcessingMetadata)

    def __post_init__(self) -> None:
        if isinstance(self.metadata, dict):
            self.metadata = ChatProcessingMetadata(data=self.metadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reply": self.reply,
            "thread_id": self.thread_id,
            "file_url": self.file_url,
            "metadata": self.metadata.data,
        }


@dataclass(slots=True)
class JobExecutionResult:
    job_id: Any
    status: Any
    result_file_url: str | None = None
    wait_time_sec: int = 0
    celery_task_id: str | None = None


def build_provider_unavailable_reply(error_message: str | None = None) -> str:
    base = (
        "Сейчас не удалось получить ответ от модели. "
        "Проверьте API-ключ/доступ к провайдеру и повторите запрос."
    )
    if error_message:
        return f"{base} Детали: {error_message}"
    return base
