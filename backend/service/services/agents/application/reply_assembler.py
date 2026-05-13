from __future__ import annotations

import json
from typing import Any


class ReplyAssembler:
    def __init__(self) -> None:
        self.reply_parts: list[str] = []
        self.error_messages: list[str] = []
        self.metadata: dict[str, Any] = {}
        self.structured_output: Any = None

    def consume(
        self, *, event: Any, stream_chunk_type: Any, error_type: Any, structured_output_type: Any
    ) -> None:
        if event.metadata:
            self.metadata.update(event.metadata)
        if event.type == stream_chunk_type and event.data is not None:
            self.reply_parts.append(str(event.data))
        elif event.type == error_type and event.data:
            self.error_messages.append(str(event.data))
        elif event.type == structured_output_type and event.data is not None:
            self.structured_output = event.data
            self.metadata = {**self.metadata, "structured_output": event.data}

    def build_reply(self) -> str:
        reply = "".join(self.reply_parts)
        if reply.strip():
            return reply
        if self.structured_output is None:
            return ""
        if isinstance(self.structured_output, str):
            return self.structured_output
        return json.dumps(self.structured_output, ensure_ascii=False)
