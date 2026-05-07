import logging
import mimetypes
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Body, Query
from fastapi.responses import RedirectResponse, Response
from service.chat.application.chat_application_service import ChatApplicationService

from service.chat.presentation.routers.chat_api.schemas import (
    MessageRequest,
    MessageResponse,
    ModelsResponse,
    ThreadCreate,
    ThreadResponse,
)
from service.models.key_value import ServiceType
from service.services.agent_file_bridge import resolve_user_uuid

logger = logging.getLogger(__name__)


chat_router = APIRouter(prefix="/api/chats")

def get_chat_application_service() -> ChatApplicationService:
    return ChatApplicationService()


@chat_router.get("/files/download")
async def download_generated_file(
    file_key: Annotated[str, Query(..., description="Storage file key or legacy local path")],
    filename: Annotated[str | None, Query(description="Optional download filename")] = None,
):
    service = get_chat_application_service()
    download = await service.download_generated_file(file_key=file_key, filename=filename)
    if "redirect_url" in download:
        return RedirectResponse(url=download["redirect_url"], status_code=307)
    media_type = mimetypes.guess_type(download["filename"])[0] or "application/octet-stream"
    return Response(
        content=download["payload"],
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{download["filename"]}"'},
    )


@chat_router.post("/{thread_id}/message", response_model=MessageResponse)
async def post_message(
    thread_id: str,
    payload: Annotated[MessageRequest, ...],
    service: ChatApplicationService = Depends(get_chat_application_service),
) -> MessageResponse:
    result = await service.post_message(thread_id=thread_id, payload=payload)
    return MessageResponse(reply=result["reply"], thread_id=result["thread_id"], metadata=result["metadata"])


@chat_router.post(
    "/",
    response_model=ThreadResponse,
    status_code=201,
)
async def create_thread(
    payload: Annotated[ThreadCreate, ...] = Body(...),
    service: ChatApplicationService = Depends(get_chat_application_service),
) -> ThreadResponse:
    res = await service.create_thread(user_id=payload.user_id, title=payload.title)
    return ThreadResponse(thread_id=res["thread_id"], title=res["title"], created_at=res.get("created_at"))


@chat_router.get("/models", response_model=ModelsResponse)
async def get_models(service: ChatApplicationService = Depends(get_chat_application_service)) -> ModelsResponse:
    models = await service.get_models()
    return ModelsResponse(models=models)


@chat_router.get("/{thread_id}")
async def get_thread_messages(
    thread_id: str,
    page: int = 1,
    per_page: int = 50,
    service: ChatApplicationService = Depends(get_chat_application_service),
):
    return await service.get_thread_messages(thread_id=thread_id, page=page, per_page=per_page)


@chat_router.get("/")
async def list_threads(
    user_id: str | None = None,
    page: int = 1,
    per_page: int = 50,
    service: ChatApplicationService = Depends(get_chat_application_service),
):
    return await service.list_threads(user_id=user_id, page=page, per_page=per_page)


@chat_router.delete("/{thread_id}", status_code=204)
async def delete_thread(thread_id: str, service: ChatApplicationService = Depends(get_chat_application_service)):
    await service.delete_thread(thread_id)
    return None


@chat_router.post("/upload")
async def upload_file_to_chat(
    file: UploadFile = File(...),
    thread_id: str = Form(""),
    user_id: Optional[str] = Form(None),
):
    """Upload a file and extract text content for chat context.

    Supports: .txt, .pdf, .docx, .csv, .json, .md, images, audio.
    Returns extracted text that can be sent as context with a chat message.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    filename = file.filename.lower()
    content_bytes = await file.read()
    max_size = 20 * 1024 * 1024  # 20MB
    if len(content_bytes) > max_size:
        raise HTTPException(status_code=413, detail="File too large (max 20MB)")

    saved_file_id = None
    saved_file_url = None
    saved_file_key = None
    try:
        from service import container

        file_service = container.get_current_container().services.file_saver_service
        uploader_uuid = resolve_user_uuid(user_id, anonymous_fallback=True)
        if uploader_uuid is not None:
            saved = await file_service.save(
                user_id=uploader_uuid,
                mode=ServiceType.CHAT,
                file_name=file.filename,
                file_content=content_bytes,
            )
            saved_file_id = str(saved.file_id)
            saved_file_url = saved.file_url
            saved_file_key = saved.file_key
    except Exception:
        logger.debug("Failed to persist uploaded chat file, will continue with extracted content only", exc_info=True)

    extracted_text = ""
    file_type = "unknown"

    try:
        if filename.endswith(".txt") or filename.endswith(".md"):
            file_type = "text"
            extracted_text = content_bytes.decode("utf-8", errors="replace")

        elif filename.endswith(".csv"):
            file_type = "csv"
            extracted_text = content_bytes.decode("utf-8", errors="replace")

        elif filename.endswith(".json"):
            file_type = "json"
            import json
            data = json.loads(content_bytes)
            extracted_text = json.dumps(data, indent=2, ensure_ascii=False)[:10000]

        elif filename.endswith(".pdf"):
            file_type = "pdf"
            try:
                import io
                # Try PyPDF2
                try:
                    from PyPDF2 import PdfReader
                    reader = PdfReader(io.BytesIO(content_bytes))
                    pages_text = []
                    for page in reader.pages[:30]:  # Max 30 pages
                        pages_text.append(page.extract_text() or "")
                    extracted_text = "\n\n".join(pages_text)
                except ImportError:
                    # Fallback: basic text extraction
                    text_parts = content_bytes.decode("latin-1", errors="replace")
                    # Extract text between stream/endstream markers
                    import re
                    streams = re.findall(r"stream\s*\n(.*?)\nendstream", text_parts, re.S)
                    extracted_text = " ".join(s for s in streams if s.strip())[:5000]
                    if not extracted_text.strip():
                        extracted_text = "[PDF файл загружен, но текст не удалось извлечь. Установите PyPDF2 для полной поддержки.]"
            except Exception:
                extracted_text = "[Ошибка чтения PDF файла]"

        elif filename.endswith((".docx",)):
            file_type = "docx"
            try:
                import io
                from docx import Document
                doc = Document(io.BytesIO(content_bytes))
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                extracted_text = "\n".join(paragraphs)
            except ImportError:
                extracted_text = "[DOCX поддержка: установите python-docx]"
            except Exception:
                extracted_text = "[Ошибка чтения DOCX файла]"

        elif filename.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
            file_type = "image"
            import base64, re as _re
            b64 = base64.b64encode(content_bytes).decode()
            mime = file.content_type or "image/png"
            image_data_url = f"data:{mime};base64,{b64}"

            # Try VLM analysis
            vlm_description = ""
            try:
                from service.agents.client import list_available_models, get_openai_client
                models = await list_available_models()
                # Find a vision/multimodal model
                vlm_re = _re.compile(r"(vision|vl\b|vlm|multimodal|image|qwen.*vl|llava|gpt-4o|pixtral)", _re.I)
                vlm_model = next((m for m in models if vlm_re.search(m)), None)

                if vlm_model:
                    client = get_openai_client()
                    if client:
                        resp = await client.chat.completions.create(
                            model=vlm_model,
                            messages=[{
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": image_data_url},
                                    },
                                    {
                                        "type": "text",
                                        "text": "Опиши подробно что изображено на этой картинке. Укажи все важные детали, объекты, текст, данные — всё что видишь.",
                                    },
                                ],
                            }],
                            max_tokens=1000,
                        )
                        vlm_description = getattr(resp.choices[0].message, "content", "") or ""
                        logger.info("VLM analysis done with model %s, got %d chars", vlm_model, len(vlm_description))
            except Exception as exc:
                logger.debug("VLM analysis failed: %s", exc)

            extracted_text = vlm_description if vlm_description else f"[Изображение загружено: {file.filename}]"
            return {
                "filename": file.filename,
                "file_type": file_type,
                "size": len(content_bytes),
                "extracted_text": extracted_text,
                "vlm_description": vlm_description,
                "image_data": image_data_url,
                "thread_id": thread_id,
                "file_id": saved_file_id,
                "file_url": saved_file_url,
                "file_key": saved_file_key,
                "temp_file": True,
            }

        elif filename.endswith((".mp3", ".wav", ".ogg", ".m4a", ".flac", ".webm")):
            file_type = "audio"
            try:
                from service.agents.client import get_openai_client, list_available_models
                client = get_openai_client()
                if client:
                    import io

                    try:
                        available = await list_available_models()
                    except Exception:
                        available = []
                    available_lower = {m.lower(): m for m in available}

                    preferred = ["whisper-medium", "whisper-turbo-local", "whisper-large-v3", "whisper-1"]
                    candidates: list[str] = []
                    for name in preferred:
                        actual = available_lower.get(name.lower())
                        if actual and actual not in candidates:
                            candidates.append(actual)
                    for m in available:
                        low = m.lower()
                        if ("whisper" in low or "asr" in low or "stt" in low) and m not in candidates:
                            candidates.append(m)
                    if not candidates:
                        candidates = preferred[:2]

                    last_exc: Exception | None = None
                    extracted_text = None
                    for model_id in candidates:
                        audio_file = io.BytesIO(content_bytes)
                        audio_file.name = file.filename
                        try:
                            transcription = await client.audio.transcriptions.create(
                                model=model_id,
                                file=audio_file,
                            )
                            extracted_text = transcription.text or "[Аудио не распознано]"
                            logger.info("Audio transcribed via %s", model_id)
                            break
                        except Exception as exc:
                            last_exc = exc
                            logger.warning(
                                "Audio transcription failed with %s (%s): %s",
                                model_id, type(exc).__name__, exc,
                            )

                    if extracted_text is None:
                        detail = f" ({last_exc})" if last_exc else ""
                        extracted_text = f"[Аудио файл: {file.filename}, транскрипция недоступна{detail}]"
                else:
                    extracted_text = "[Аудио загружено, но транскрипция недоступна]"
            except Exception as exc:
                logger.warning("Audio transcription failed (%s): %s", type(exc).__name__, exc)
                extracted_text = f"[Аудио файл: {file.filename}, транскрипция недоступна]"

        else:
            file_type = "binary"
            try:
                extracted_text = content_bytes.decode("utf-8", errors="replace")[:5000]
            except Exception:
                extracted_text = f"[Файл {file.filename} загружен, но содержимое не удалось извлечь]"

    except Exception as exc:
        logger.exception("File processing failed: %s", exc)
        raise HTTPException(status_code=500, detail="File processing failed")

    # Truncate
    if len(extracted_text) > 15000:
        extracted_text = extracted_text[:15000] + "\n...[содержимое обрезано]"

    return {
        "filename": file.filename,
        "file_type": file_type,
        "size": len(content_bytes),
        "extracted_text": extracted_text,
        "thread_id": thread_id,
        "file_id": saved_file_id,
        "file_url": saved_file_url,
        "file_key": saved_file_key,
        "temp_file": True,
    }


@chat_router.post("/web-search")
async def web_search_endpoint(q: str = "", num_results: int = 5):
    """Search the web and return results."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query is required")
    from service.agents.tools.web_search import web_search
    results = await web_search(q.strip(), num_results=min(num_results, 10))
    return {"query": q, "results": results, "count": len(results)}


@chat_router.post("/parse-url")
async def parse_url_endpoint(url: str = ""):
    """Parse a URL and extract text content."""
    if not url.strip():
        raise HTTPException(status_code=400, detail="URL is required")
    from service.agents.tools.web_search import parse_url
    result = await parse_url(url.strip())
    return result


@chat_router.post("/generate-pptx")
async def generate_pptx_endpoint(topic: str = ""):
    """Generate a PowerPoint presentation on the given topic."""
    from fastapi.responses import Response
    if not topic.strip():
        raise HTTPException(status_code=400, detail="Topic is required")

    try:
        from service.agents.client import list_available_models
        from service.agents.tools.pptx import generate_pptx
        import re

        models = await list_available_models()
        text_re = re.compile(r"(gpt|qwen|llama|mistral|alpha|instruct|chat)", re.I)
        model = next((m for m in models if text_re.search(m)), models[0] if models else None)

        if not model:
            raise HTTPException(status_code=503, detail="No models available")

        pptx_bytes, structure = await generate_pptx(topic.strip(), model)

        filename = re.sub(r"[^\w\s-]", "", topic.strip())[:40].strip().replace(" ", "_") or "presentation"

        return Response(
            content=pptx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": f'attachment; filename="{filename}.pptx"'},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("PPTX generation failed")
        raise HTTPException(status_code=500, detail=f"PPTX generation failed: {str(exc)}")
