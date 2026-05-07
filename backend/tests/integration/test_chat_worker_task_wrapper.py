from service.chat.infrastructure.chat_worker_tasks import process_agent_message


def test_task_wrapper_calls_handler(monkeypatch):
    called = {}

    class _FakeHandler:
        async def process_for_worker(self, job_id, command):
            called["job_id"] = job_id
            called["thread_id"] = command.thread_id
            return {"status": "success", "reply": "ok", "metadata": {}}

    import service.container as container

    monkeypatch.setattr(container, "get", lambda name: _FakeHandler())

    result = process_agent_message.run(
        job_id="job-1",
        thread_id="thread-1",
        text="hello",
        user_id=1,
        session_data={"session_id": "thread-1"},
        selected_model=None,
        route_override=None,
        input_type=None,
        web_search=False,
        deep_research=False,
        file_context="",
    )

    assert result["status"] == "success"
    assert called["job_id"] == "job-1"
    assert called["thread_id"] == "thread-1"
