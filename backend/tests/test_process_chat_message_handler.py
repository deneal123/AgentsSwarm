from service.chat.domain.process_chat_message_handler import ProcessChatMessageHandler


def test_normalize_result_payload_adds_selected_model_and_keeps_reply_format() -> None:
    result = {
        "status": "success",
        "reply": "Hello",
        "metadata": {"source": "worker"},
        "file_url": None,
    }

    normalized = ProcessChatMessageHandler.normalize_result_payload(
        result,
        thread_id="thread-1",
        selected_model="mws-gpt-alpha",
    )

    assert normalized.reply == "Hello"
    assert normalized.thread_id == "thread-1"
    assert normalized.metadata == {
        "source": "worker",
        "selected_model": "mws-gpt-alpha",
    }


def test_normalize_result_payload_marks_provider_unavailable_for_empty_reply() -> None:
    result = {
        "status": "success",
        "reply": "",
        "metadata": {"provider_error": "timeout"},
    }

    normalized = ProcessChatMessageHandler.normalize_result_payload(
        result,
        thread_id="thread-2",
        selected_model=None,
    )

    assert normalized.reply
    assert normalized.metadata["provider_unavailable"] is True
    assert normalized.metadata["provider_error"] == "timeout"
