from __future__ import annotations

import logging
from pathlib import Path

from fastapi import HTTPException, status

from service.agents.client import list_available_models
from service.services.chat_contracts import ChatRequestContext
from service.services.chat_exceptions import map_chat_exception_to_http
from service.services.chat_service import ChatService

logger = logging.getLogger(__name__)


class ChatApplicationService:
    def __init__(self, chat_service: ChatService | None = None) -> None:
        self.chat_service = chat_service or ChatService()

    @staticmethod
    def filter_chat_models(models: list[str]) -> list[str]:
        blocked_markers = ("bge", "e5", "gte", "embed", "embedding", "rerank", "ranker")
        return [m for m in (models or []) if not any(marker in str(m).lower() for marker in blocked_markers)]

    async def post_message(self, thread_id: str, payload) -> dict:
        try:
            result = await self.chat_service.post_message(
                ChatRequestContext(
                    thread_id=thread_id,
                    text=payload.text,
                    user_id=payload.user_id,
                    selected_model=payload.model,
                    route_override=payload.route_override,
                    input_type=payload.input_type,
                    web_search=payload.web_search,
                    deep_research=payload.deep_research,
                    file_context=payload.file_context,
                )
            )
        except Exception as exc:
            logger.exception("ChatService failed to handle message: %s", exc)
            raise map_chat_exception_to_http(exc) from exc
        return {
            "reply": result.reply,
            "thread_id": result.thread_id,
            "metadata": result.metadata.data,
        }

    async def create_thread(self, user_id: str | None, title: str | None) -> dict:
        res = await self.chat_service.create_thread(user_id=user_id, title=title)
        return {
            "thread_id": res["thread_id"],
            "title": res["title"],
            "created_at": res.get("created_at"),
        }

    async def get_models(self) -> list[str]:
        models = await list_available_models()
        return self.filter_chat_models(models)

    async def get_thread_messages(self, thread_id: str, page: int, per_page: int) -> dict:
        try:
            return await self.chat_service.get_messages(thread_id=thread_id, page=page, per_page=per_page)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid pagination parameters") from exc
        except Exception as exc:
            from service.repositories.exceptions import RepositoryNotFoundError

            if isinstance(exc, RepositoryNotFoundError):
                raise HTTPException(status_code=404, detail="Thread not found") from exc
            logger.exception("Failed to fetch messages: %s", exc)
            raise HTTPException(status_code=503, detail="DB unavailable") from exc

    async def list_threads(self, user_id: str | None, page: int, per_page: int) -> dict:
        try:
            return await self.chat_service.list_threads(user_id=user_id, page=page, per_page=per_page)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid pagination parameters") from exc
        except Exception as exc:
            logger.exception("Failed to list threads: %s", exc)
            raise HTTPException(status_code=503, detail="DB unavailable") from exc

    async def delete_thread(self, thread_id: str) -> None:
        try:
            ok = await self.chat_service.delete_thread(thread_id)
            if not ok:
                raise HTTPException(status_code=404, detail="Thread not found")
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Failed to delete thread: %s", exc)
            raise HTTPException(status_code=503, detail="DB unavailable") from exc

    async def download_generated_file(self, file_key: str, filename: str | None) -> dict:
        from service import container

        normalized_key = self._normalize_download_file_key(file_key)
        file_service = container.get_current_container().services.file_saver_service

        try:
            download_url = await file_service.get_presigned_url_by_key(file_key=normalized_key)
        except Exception:
            download_url = None

        if isinstance(download_url, str) and download_url.startswith(("http://", "https://")):
            return {"redirect_url": download_url}

        payload = await file_service.get_file_by_key(file_key=normalized_key)
        if payload is None:
            raise HTTPException(status_code=404, detail="File not found")

        suggested_name = (filename or Path(normalized_key).name or "download.bin").strip()
        return {"payload": payload, "filename": suggested_name}

    @staticmethod
    def _normalize_download_file_key(file_key: str) -> str:
        import os

        raw = str(file_key or "").strip()
        if not raw:
            raise HTTPException(status_code=400, detail="file_key is required")
        storage_root = os.getenv("STORAGE_ROOT", "/var/lib/app/storage").rstrip("/")
        if raw.startswith(f"{storage_root}/"):
            raw = raw[len(storage_root) + 1 :]
        elif raw.startswith("/var/lib/app/storage/"):
            raw = raw[len("/var/lib/app/storage/") :]
        raw = raw.lstrip("/")
        path_obj = Path(raw)
        if ".." in path_obj.parts:
            raise HTTPException(status_code=400, detail="Invalid file_key")
        if not raw:
            raise HTTPException(status_code=400, detail="Invalid file_key")
        return raw
