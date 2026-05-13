from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from service.composition.state import get_chat_application_service
from service.models.auth_models import AuthProfile
from service.services.chat.application.use_cases.upload_file_use_case import UploadFileUseCase
from service.services.chat.infrastructure.media.openai_media_analysis_adapter import (
    OpenAIMediaAnalysisAdapter,
)
from service.services.chat.presentation.routers.chat_api.schemas import UploadFileResponse
from service.shared.security.auth_checker import check_auth

upload_router = APIRouter()


def get_upload_use_case(file_service) -> UploadFileUseCase:
    return UploadFileUseCase(
        media_analysis_port=OpenAIMediaAnalysisAdapter(),
        file_service=file_service,
    )


@upload_router.post("/upload", response_model=UploadFileResponse)
async def upload_file_to_chat(
    profile: Annotated[AuthProfile, Depends(check_auth)],
    file: UploadFile = File(...),  # noqa: B008
    thread_id: str = Form(""),
    chat_application_service=Depends(get_chat_application_service),  # noqa: B008
) -> UploadFileResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    try:
        result = await get_upload_use_case(chat_application_service.file_service).execute(
            filename=file.filename,
            content_type=file.content_type,
            content_bytes=await file.read(),
            thread_id=thread_id,
            user_id=str(profile.user_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OverflowError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="File processing failed") from exc
    return UploadFileResponse(**result)
