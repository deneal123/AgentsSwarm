from __future__ import annotations

from typing import Protocol


class AbstractFileStorage(Protocol):
    """Простой контракт для бэкендов хранения файлов."""

    def build_file_path(
        self, folder: str, mode: str, file_name: str
    ) -> str:  # pragma: no cover - trivial
        ...

    async def upload_file(self, *, file_key: str, file_data: bytes) -> str: ...

    async def delete_file(self, *, file_key: str) -> None: ...
