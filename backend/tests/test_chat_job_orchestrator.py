import pytest

from service.services.chat.domain.chat_exceptions import JobExecutionError
from service.services.chat.domain.chat_job_orchestrator import ChatJobOrchestrator


class _Handler:
    def __init__(self, payload):
        self.payload = payload

    async def dispatch_and_wait(self, command, timeout_sec=30.0):
        if self.payload.get("status") == "failed":
            raise JobExecutionError(self.payload.get("error") or "x")
        return self.payload["result"]


@pytest.mark.asyncio
async def test_execute_success() -> None:
    from service.services.chat.domain.chat_contracts import ChatReplyResult, ChatProcessingMetadata

    handler = _Handler(
        {
            "status": "success",
            "result": ChatReplyResult(
                reply="ok",
                thread_id="t1",
                file_url="u",
                metadata=ChatProcessingMetadata(data={"a": 1}),
            ),
        }
    )
    orchestrator = ChatJobOrchestrator(handler=handler)
    result = await orchestrator.execute("t1", "hello", None, None, None, False, False, "", None)
    assert result.reply == "ok"
    assert result.thread_id == "t1"
    assert result.file_url == "u"
    assert result.metadata["a"] == 1


@pytest.mark.asyncio
async def test_execute_failed_status_raises() -> None:
    orchestrator = ChatJobOrchestrator(handler=_Handler({"status": "failed", "error": "x"}))
    with pytest.raises(JobExecutionError):
        await orchestrator.execute("t1", "hello", None, None, None, False, False, "", None)
