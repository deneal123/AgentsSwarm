import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, UploadFile, status

from service.composition.state import get_file_saver_service
from service.models.auth_models import AuthProfile
from service.models.key_value import ServiceType
from service.shared.security.auth_checker import check_auth
from service.services.files.presentation.routers.files_api.schemas import (
    FetchModesResponse,
    FetchUserFilesResponse,
    UploadResponse,
    FileMetadata,
    PresignRequest,
    PresignResponse,
    FileDetailResponse,
    CallbackRequest,
)
from service.services.files.application.file_saver_service import FileSaverService
from service.settings import config

logger = logging.getLogger(__name__)
files_router = APIRouter(prefix="/api/service")


@files_router.get(
    "/files/v1/modes",
    summary="(Beta) Get available service modes",
    response_model=FetchModesResponse,
)
async def fetch_available_modes(
    profile: Annotated[AuthProfile, Depends(check_auth)],
) -> FetchModesResponse:
    return FetchModesResponse(modes=[mode for mode in ServiceType])


@files_router.get(
    path="/files/v1/fetch/{mode}",
    summary="Fetch user photos metadata",
    response_model=FetchUserFilesResponse,
)
async def fetch_handler(
    profile: Annotated[AuthProfile, Depends(check_auth)],
    mode: Annotated[ServiceType, Path(...)],
    service: Annotated[FileSaverService, Depends(get_file_saver_service)],
) -> FetchUserFilesResponse:
    return await service.fetch_all_user_files(profile.user_id, mode)


@files_router.post(
    "/files/v1/upload/{mode}",
    summary="Upload user photo",
    description=f"Only: {config.file.settings.allowed_extensions} format allowed.",
    response_model=UploadResponse,
)
async def upload_handler(
    profile: Annotated[AuthProfile, Depends(check_auth)],
    mode: Annotated[ServiceType, Path(...)],
    file: UploadFile,
    service: Annotated[FileSaverService, Depends(get_file_saver_service)],
) -> UploadResponse:
    if file_name := file.filename:
        lower_name = file_name.lower()
        if not any(lower_name.endswith(ext.lower()) for ext in config.file.settings.allowed_extensions):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file extension. Only: {config.file.settings.allowed_extensions} allowed.",
            )
        content = await file.read()
        if len(content) > config.file.settings.max_file_size_byte:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Max size: {config.file.settings.max_file_size_byte} bytes.",
            )
        return await service.save(
            user_id=profile.user_id,
            mode=mode,
            file_name=file_name,
            file_content=content,
        )
    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty filename")


@files_router.delete("/files/v1/delete/{file_id}")
async def delete_handler(
    profile: Annotated[AuthProfile, Depends(check_auth)],
    file_id: Annotated[UUID, Path(..., title="File ID")],
    service: Annotated[FileSaverService, Depends(get_file_saver_service)],
) -> None:
    await service.delete(user_id=profile.user_id, file_id=file_id)


@files_router.post(
    "/files/v1/presign/{mode}",
    summary="Create presigned upload URL",
    response_model=PresignResponse,
)
async def presign_upload(
    profile: Annotated[AuthProfile, Depends(check_auth)],
    mode: Annotated[ServiceType, Path(...)],
    payload: PresignRequest,
    service: Annotated[FileSaverService, Depends(get_file_saver_service)],
) -> PresignResponse:
    res = await service.presign_upload(
        user_id=profile.user_id,
        mode=mode,
        file_name=payload.filename,
        expiry_sec=payload.expiry_sec,
    )
    return PresignResponse(
        file_id=res["file_id"],
        file_key=res["file_key"],
        upload_url=res["upload_url"],
        expires_in=payload.expiry_sec,
    )


@files_router.post(
    "/files/v1/{file_id}/callback",
    summary="Callback invoked after client finishes upload",
    response_model=FileMetadata,
)
async def upload_callback(
    file_id: Annotated[UUID, Path(..., title="File ID")],
    payload: CallbackRequest,
    profile: Annotated[AuthProfile, Depends(check_auth)],
    service: Annotated[FileSaverService, Depends(get_file_saver_service)],
) -> FileMetadata:
    res = await service.finalize_upload(
        user_id=profile.user_id,
        mode=payload.mode,
        file_id=file_id,
        file_key=payload.file_key,
    )
    return FileMetadata(file_id=res["file_id"], file_url=res["file_url"])


@files_router.get(
    "/files/v1/{file_id}",
    summary="Get file metadata and download URL",
    response_model=FileDetailResponse,
)
async def get_file(
    file_id: Annotated[UUID, Path(..., title="File ID")],
    profile: Annotated[AuthProfile, Depends(check_auth)],
    service: Annotated[FileSaverService, Depends(get_file_saver_service)],
) -> FileDetailResponse:
    meta = await service.fetch_file_metadata(profile.user_id, file_id)
    download = await service.get_presigned_url_by_key(
        file_key=meta.file_id.hex if hasattr(meta, "file_id") else None
    )
    return FileDetailResponse(file_id=meta.file_id, file_url=meta.file_url, download_url=download)
