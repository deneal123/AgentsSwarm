import asyncio

from service.agents.application.ports.interfaces import AgentExecutionPort, StreamPort
from service.chat.application.ports.interfaces import ChatCommandPort
from service.files.application.ports.interfaces import FileStoragePort, MessageBusPort
from service.jobs.application.ports.interfaces import JobHandlePort, JobOrchestrationPort, JobQueuePort



class FakeMessageBus:
    def __init__(self):
        self.items = []

    async def push(self, queue: str, payload: str) -> None:
        self.items.append((queue, payload))


class FakeStream:
    def __init__(self):
        self.events = []

    async def publish(self, stream: str, payload: dict) -> None:
        self.events.append((stream, payload))


class FakeStorage:
    def build_file_path(self, folder: str, mode: str, file_name: str) -> str:
        return f"{folder}/{mode}/{file_name}"

    async def upload_file(self, *, file_key: str, file_data: bytes) -> str:
        return f"mem://{file_key}"

    async def delete_file(self, *, file_key: str) -> None:
        return None


class FakeHandle:
    def __init__(self, result: dict):
        self.result = result

    def get(self, timeout: float) -> dict:
        return self.result


class FakeQueue:
    def enqueue_process_agent_message(self, **kwargs):
        return FakeHandle({"status": "success", **kwargs})

    async def process_agent_message(self, **kwargs):
        return {"status": "success", **kwargs}

    def enqueue_calendar_generation(self, args):
        return "task-1"

    def get_task_state(self, task_id: str):
        return True, True, {"calendar_id": "c-1"}, {"progress": 100}, "SUCCESS"


class FakeChatCommand:
    async def dispatch_and_wait(self, command, *, timeout_sec: float = 30.0):
        return {"status": "ok", "command": command, "timeout": timeout_sec}


class FakeJobOrchestration:
    async def create_chat_job(self, user_id, thread_id: str, text: str):
        return {"job_id": "1", "user_id": user_id, "thread_id": thread_id, "text": text}


class FakeAgentExecution:
    async def execute(self, **kwargs):
        return {"status": "ok", **kwargs}


def test_message_bus_port_contract() -> None:
    bus = FakeMessageBus()
    assert isinstance(bus, MessageBusPort)
    asyncio.run(bus.push("q", "v"))
    assert bus.items == [("q", "v")]


def test_stream_port_contract() -> None:
    stream = FakeStream()
    assert isinstance(stream, StreamPort)
    asyncio.run(stream.publish("s", {"a": 1}))
    assert stream.events == [("s", {"a": 1})]


def test_file_storage_port_contract() -> None:
    storage = FakeStorage()
    assert isinstance(storage, FileStoragePort)
    key = storage.build_file_path("uploads", "CHAT", "a.txt")
    assert key == "uploads/CHAT/a.txt"
    assert asyncio.run(storage.upload_file(file_key=key, file_data=b"x")) == "mem://uploads/CHAT/a.txt"
    asyncio.run(storage.delete_file(file_key=key))


def test_job_queue_port_contract() -> None:
    queue = FakeQueue()
    assert isinstance(queue, JobQueuePort)
    handle = queue.enqueue_process_agent_message(job_id="1")
    assert isinstance(handle, JobHandlePort)
    assert handle.get(timeout=1.0)["status"] == "success"
    worker_result = asyncio.run(queue.process_agent_message(job_id="1"))
    assert worker_result["status"] == "success"
    assert queue.enqueue_calendar_generation(["a"]) == "task-1"
    ready, successful, payload, meta, state = queue.get_task_state("task-1")
    assert ready is True
    assert successful is True
    assert payload["calendar_id"] == "c-1"
    assert meta["progress"] == 100
    assert state == "SUCCESS"


def test_chat_command_port_contract() -> None:
    chat_command = FakeChatCommand()
    assert isinstance(chat_command, ChatCommandPort)
    payload = asyncio.run(chat_command.dispatch_and_wait({"id": "1"}, timeout_sec=2.0))
    assert payload["status"] == "ok"


def test_job_orchestration_port_contract() -> None:
    job_orchestration = FakeJobOrchestration()
    assert isinstance(job_orchestration, JobOrchestrationPort)
    payload = asyncio.run(job_orchestration.create_chat_job("u1", "t1", "hello"))
    assert payload["thread_id"] == "t1"


def test_agent_execution_port_contract() -> None:
    agent_execution = FakeAgentExecution()
    assert isinstance(agent_execution, AgentExecutionPort)
    payload = asyncio.run(agent_execution.execute(thread_id="t1"))
    assert payload["thread_id"] == "t1"
