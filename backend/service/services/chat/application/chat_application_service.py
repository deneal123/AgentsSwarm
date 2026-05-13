from __future__ import annotations

import logging
import re
from pathlib import Path

from fastapi import HTTPException

from service.services.agents.domain.client import list_available_models
from service.services.agents.domain.tools.pptx import generate_pptx
from service.services.agents.domain.tools.web_search import parse_url, web_search
from service.services.chat.application.error_handling import (
    map_to_http_exception,
    normalize_response_metadata,
)
from service.services.chat.application.use_cases.chat_use_cases import (
    CreateThreadUseCase,
    PostMessageUseCase,
)
from service.services.chat.domain.chat_service import ChatService
from service.settings import config

logger = logging.getLogger(__name__)


class ChatApplicationService:
    DEFAULT_STORAGE_ROOT = "/var/lib/app/storage"

    def __init__(self, chat_service: ChatService, file_service) -> None:
        self.chat_service = chat_service
        self.file_service = file_service

    @staticmethod
    def filter_chat_models(models: list[str]) -> list[str]:
        blocked_markers = ("bge", "e5", "gte", "embed", "embedding", "rerank", "ranker")
        return [
            m
            for m in (models or [])
            if not any(marker in str(m).lower() for marker in blocked_markers)
        ]

    async def post_message(self, thread_id: str, payload) -> dict:
        use_case = PostMessageUseCase(self.chat_service)
        try:
            result = await use_case.execute(thread_id=thread_id, payload=payload)
        except Exception as exc:
            logger.exception("ChatService failed to handle message: %s", exc)
            raise map_to_http_exception(exc) from exc
        return {
            "reply": result.reply,
            "thread_id": result.thread_id,
            "metadata": normalize_response_metadata(
                result.metadata.data, selected_model=payload.model
            ),
        }

    async def create_thread(self, user_id: str | None, title: str | None) -> dict:
        res = await CreateThreadUseCase(self.chat_service).execute(user_id=user_id, title=title)
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
            return await self.chat_service.get_messages(
                thread_id=thread_id, page=page, per_page=per_page
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid pagination parameters") from exc
        except Exception as exc:
            from service.shared.repositories.exceptions import RepositoryNotFoundError

            if isinstance(exc, RepositoryNotFoundError):
                raise HTTPException(status_code=404, detail="Thread not found") from exc
            logger.exception("Failed to fetch messages: %s", exc)
            raise HTTPException(status_code=503, detail="DB unavailable") from exc

    async def list_threads(self, user_id: str | None, page: int, per_page: int) -> dict:
        try:
            return await self.chat_service.list_threads(
                user_id=user_id, page=page, per_page=per_page
            )
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
        normalized_key = self._normalize_download_file_key(file_key)
        file_service = self.file_service

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
        raw = str(file_key or "").strip()
        if not raw:
            raise HTTPException(status_code=400, detail="file_key is required")
        storage_root = (config.storage.root or ChatApplicationService.DEFAULT_STORAGE_ROOT).rstrip(
            "/"
        )
        if raw.startswith(f"{storage_root}/"):
            raw = raw[len(storage_root) + 1 :]
        elif raw.startswith(f"{ChatApplicationService.DEFAULT_STORAGE_ROOT}/"):
            raw = raw[len(ChatApplicationService.DEFAULT_STORAGE_ROOT) + 1 :]
        raw = raw.lstrip("/")
        path_obj = Path(raw)
        if ".." in path_obj.parts:
            raise HTTPException(status_code=400, detail="Invalid file_key")
        if not raw:
            raise HTTPException(status_code=400, detail="Invalid file_key")
        return raw

    async def run_web_search(self, query: str, num_results: int = 5) -> dict:
        query_value = query.strip()
        if not query_value:
            raise HTTPException(status_code=400, detail="Query is required")
        results = await web_search(query_value, num_results=min(num_results, 10))
        return {"query": query_value, "results": results, "count": len(results)}

    async def parse_url_content(self, url: str) -> dict:
        url_value = url.strip()
        if not url_value:
            raise HTTPException(status_code=400, detail="URL is required")
        try:
            return await parse_url(url_value)
        except Exception:  # noqa: BLE001
            logger.exception("URL parsing failed")
            raise HTTPException(
                status_code=502,
                detail="Unable to fetch or parse URL content",
            )

    async def generate_topic_pptx(self, topic: str) -> dict:
        topic_value = topic.strip()
        if not topic_value:
            raise HTTPException(status_code=400, detail="Topic is required")

        models = await list_available_models()
        text_re = re.compile(r"(gpt|qwen|llama|mistral|alpha|instruct|chat)", re.I)
        model = next((m for m in models if text_re.search(m)), models[0] if models else None)
        if not model:
            raise HTTPException(status_code=503, detail="No models available")

        pptx_bytes, _ = await generate_pptx(topic_value, model)
        filename = (
            re.sub(r"[^\w\s-]", "", topic_value)[:40].strip().replace(" ", "_") or "presentation"
        )
        return {"payload": pptx_bytes, "filename": f"{filename}.pptx"}
