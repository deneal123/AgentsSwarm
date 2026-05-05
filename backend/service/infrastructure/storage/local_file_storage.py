import os
from pathlib import Path

from .abstract_file_storage import AbstractFileStorage


class LocalFileStorage(AbstractFileStorage):
    """Простейшее файловое хранилище для пользовательских загрузок.

    Сохраняет файлы в базовую директорию STORAGE_ROOT (env) с ключами вида
    "{folder}/{mode}/{file_name}" и возвращает file_url как абсолютный путь.
    """

    def __init__(self, base_dir: str | Path | None = None) -> None:
        base = base_dir or os.getenv("STORAGE_ROOT", "/var/lib/app/storage")
        self.base_dir = Path(str(base))
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def build_file_path(self, folder: str, mode: str, file_name: str) -> str:
        return f"{folder}/{mode}/{file_name}"

    async def upload_file(self, *, file_key: str, file_data: bytes) -> str:
        path = self.base_dir / file_key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(file_data)
        # Возвращаем абсолютный путь как URL-заменитель; при необходимости заменить на CDN/S3 URL
        return str(path.resolve())

    async def delete_file(self, *, file_key: str) -> None:
        path = self.base_dir / file_key
        try:
            path.unlink(missing_ok=True)
        except TypeError:
            # Для Python <3.8 совместимости можно обойтись проверкой exists
            if path.exists():
                path.unlink()

    async def get_file(self, file_key: str) -> bytes:
        """Download file from local storage by key."""
        path = self.base_dir / file_key
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {file_key}")
        return path.read_bytes()
