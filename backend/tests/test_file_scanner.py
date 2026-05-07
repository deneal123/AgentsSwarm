import pytest
import asyncio

from service.files.application.file_scanner_service import BasicFileScanner


class FakeStorage:
    def __init__(self, data: bytes):
        self.data = data

    async def get_file(self, file_key: str) -> bytes:
        return self.data


@pytest.mark.asyncio
async def test_basic_scanner_computes_sha256():
    s = FakeStorage(b"hello")
    scanner = BasicFileScanner(s)

    res = await scanner.scan("folder/file.jpg")
    assert res["status"] == "ok"
    assert res["size"] == 5
    assert res["sha256"] is not None


@pytest.mark.asyncio
async def test_basic_scanner_handles_missing_getter():
    class NoGetStorage:
        pass

    scanner = BasicFileScanner(NoGetStorage())
    res = await scanner.scan("x")
    assert res["status"] == "skipped"
