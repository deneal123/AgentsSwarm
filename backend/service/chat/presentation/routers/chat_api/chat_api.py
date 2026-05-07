import logging
import mimetypes
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from fastapi.responses import RedirectResponse, Response
from service.chat.application.chat_application_service import ChatApplicationService
from service.chat.presentation.http.upload_api import upload_router

from service.chat.presentation.routers.chat_api.schemas import (
    MessageRequest,
    MessageResponse,
    ModelsResponse,
    ThreadCreate,
    ThreadResponse,
)

logger = logging.getLogger(__name__)


chat_router = APIRouter(prefix="/api/chats")
chat_router.include_router(upload_router)

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


@chat_router.post("/web-search")
async def web_search_endpoint(q: str = "", num_results: int = 5):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query is required")
    from service.agents.tools.web_search import web_search
    results = await web_search(q.strip(), num_results=min(num_results, 10))
    return {"query": q, "results": results, "count": len(results)}


@chat_router.post("/parse-url")
async def parse_url_endpoint(url: str = ""):
    if not url.strip():
        raise HTTPException(status_code=400, detail="URL is required")
    from service.agents.tools.web_search import parse_url
    result = await parse_url(url.strip())
    return result


@chat_router.post("/generate-pptx")
async def generate_pptx_endpoint(topic: str = ""):
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

        pptx_bytes, _ = await generate_pptx(topic.strip(), model)

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
