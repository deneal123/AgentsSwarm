from __future__ import annotations

import io
import json

from service.models.key_value import ServiceType
from service.services.agents.application.agent_file_bridge import resolve_user_uuid
from service.services.chat.application.ports.media_analysis_port import MediaAnalysisPort


class UploadFileUseCase:
    def __init__(self, media_analysis_port: MediaAnalysisPort, file_service) -> None:
        self.media_analysis_port = media_analysis_port
        self.file_service = file_service

    async def execute(
        self,
        *,
        filename: str,
        content_type: str | None,
        content_bytes: bytes,
        thread_id: str,
        user_id: str | None,
    ) -> dict:
        if not filename:
            raise ValueError("No file provided")
        if len(content_bytes) > 20 * 1024 * 1024:
            raise OverflowError("File too large (max 20MB)")

        saved_file_id, saved_file_url, saved_file_key = await self._save_file(
            filename, content_bytes, user_id
        )
        extracted_text, file_type = await self._extract_text(filename, content_type, content_bytes)

        if len(extracted_text) > 15000:
            extracted_text = extracted_text[:15000] + "\n...[содержимое обрезано]"

        return {
            "filename": filename,
            "file_type": file_type,
            "size": len(content_bytes),
            "extracted_text": extracted_text,
            "thread_id": thread_id,
            "file_id": saved_file_id,
            "file_url": saved_file_url,
            "file_key": saved_file_key,
            "temp_file": True,
        }

    async def _save_file(
        self, filename: str, content_bytes: bytes, user_id: str | None
    ) -> tuple[str | None, str | None, str | None]:
        try:
            uploader_uuid = resolve_user_uuid(user_id, anonymous_fallback=True)
            if uploader_uuid is None:
                return None, None, None
            saved = await self.file_service.save(
                user_id=uploader_uuid,
                mode=ServiceType.CHAT,
                file_name=filename,
                file_content=content_bytes,
            )
            return str(saved.file_id), saved.file_url, saved.file_key
        except Exception:
            return None, None, None

    async def _extract_text(
        self, filename: str, content_type: str | None, content_bytes: bytes
    ) -> tuple[str, str]:
        lower_name = filename.lower()
        if lower_name.endswith((".txt", ".md", ".csv")):
            return content_bytes.decode("utf-8", errors="replace"), "text"
        if lower_name.endswith(".json"):
            data = json.loads(content_bytes)
            return json.dumps(data, indent=2, ensure_ascii=False)[:10000], "json"
        if lower_name.endswith(".pdf"):
            from PyPDF2 import PdfReader

            reader = PdfReader(io.BytesIO(content_bytes))
            pages_text = [page.extract_text() or "" for page in reader.pages[:30]]
            return "\n\n".join(pages_text), "pdf"
        if lower_name.endswith(".docx"):
            from docx import Document

            doc = Document(io.BytesIO(content_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n".join(paragraphs), "docx"
        if lower_name.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
            return await self.media_analysis_port.analyze_image(
                content_bytes, content_type or "image/png", filename
            ), "image"
        if lower_name.endswith((".mp3", ".wav", ".ogg", ".m4a", ".flac", ".webm")):
            return await self.media_analysis_port.transcribe_audio(content_bytes, filename), "audio"
        try:
            return content_bytes.decode("utf-8", errors="replace")[:5000], "binary"
        except Exception:
            return f"[Файл {filename} загружен, но содержимое не удалось извлечь]", "binary"
