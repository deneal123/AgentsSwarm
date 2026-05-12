import logging
import mimetypes
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from fastapi.responses import RedirectResponse, Response

from service.services.chat.application.chat_application_service import ChatApplicationService
from service.composition.state import get_chat_application_service
from service.services.chat.presentation.http.upload_api import upload_router

from service.services.chat.presentation.routers.chat_api.schemas import (
    MessageRequest,
    MessageResponse,
    ModelsResponse,
    ThreadCreate,
    ThreadResponse,
)

logger = logging.getLogger(__name__)


chat_router = APIRouter(prefix="/api/chats")
chat_router.include_router(upload_router)


@chat_router.get("/files/download")
async def download_generated_file(
    file_key: Annotated[str, Query(..., description="Storage file key or legacy local path")],
    filename: Annotated[str | None, Query(description="Optional download filename")] = None,
    service: ChatApplicationService = Depends(get_chat_application_service),
):
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
    found = await service.delete_thread(thread_id)
    if found is False:
        raise HTTPException(status_code=404, detail="Thread not found")
    return None


@chat_router.post("/web-search")
async def web_search_endpoint(
    q: str = "",
    num_results: int = 5,
    service: ChatApplicationService = Depends(get_chat_application_service),
):
    return await service.run_web_search(query=q, num_results=num_results)


@chat_router.post("/parse-url")
async def parse_url_endpoint(
    url: str = "",
    service: ChatApplicationService = Depends(get_chat_application_service),
):
    try:
        return await service.parse_url_content(url=url)
    except HTTPException as exc:
        if exc.status_code == 400:
            raise
        logger.warning("URL parse request failed")
        raise HTTPException(status_code=502, detail="Unable to fetch or parse URL content")
    except Exception:
        logger.exception("Unexpected parse-url failure")
        raise HTTPException(status_code=502, detail="Unable to fetch or parse URL content")


@chat_router.post("/generate-pptx")
async def generate_pptx_endpoint(
    topic: str = "",
    service: ChatApplicationService = Depends(get_chat_application_service),
):
    try:
        generated = await service.generate_topic_pptx(topic=topic)
        return Response(
            content=generated["payload"],
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": f'attachment; filename="{generated["filename"]}"'},
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("PPTX generation failed")
        raise HTTPException(status_code=500, detail="PPTX generation failed")
