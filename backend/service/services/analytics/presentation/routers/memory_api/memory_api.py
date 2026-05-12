"""Memory API endpoints for viewing and managing long-term user facts."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from service.models.auth_models import AuthProfile
from service.shared.security.auth_checker import check_auth
from service.services.analytics.presentation.routers.memory_api.schemas import (
    AddMemoryFactRequest,
    AddMemoryFactResponse,
    MemoryFactResponse,
    MemoryFactsResponse,
)
from service.services.analytics.application.memory_service import MemoryService

memory_router = APIRouter(prefix="/api/memory")


def get_memory_service() -> MemoryService:
    return MemoryService()


def _ensure_owner_access(path_user_id: str, auth_profile: AuthProfile) -> str:
    normalized = str(path_user_id or "").strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required")

    auth_user_id = str(auth_profile.user_id)
    if normalized != auth_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return normalized


@memory_router.get("/{user_id}", response_model=MemoryFactsResponse)
async def get_user_memory(
    user_id: str,
    auth_profile: Annotated[AuthProfile, Depends(check_auth)],
    service: Annotated[MemoryService, Depends(get_memory_service)],
) -> MemoryFactsResponse:
    effective_user_id = _ensure_owner_access(user_id, auth_profile)
    facts = await service.list_facts(effective_user_id)
    context_text = await service.get_memory_context(effective_user_id)
    return MemoryFactsResponse(
        facts=[MemoryFactResponse(**item) for item in facts],
        context_text=context_text,
    )


@memory_router.get("/{user_id}/search", response_model=MemoryFactsResponse)
async def search_user_memory(
    user_id: str,
    q: Annotated[str, Query(min_length=1)],
    auth_profile: Annotated[AuthProfile, Depends(check_auth)],
    service: Annotated[MemoryService, Depends(get_memory_service)],
) -> MemoryFactsResponse:
    effective_user_id = _ensure_owner_access(user_id, auth_profile)
    facts = await service.list_facts(effective_user_id, query=q)
    return MemoryFactsResponse(facts=[MemoryFactResponse(**item) for item in facts], context_text=None)


@memory_router.post("/{user_id}/facts", response_model=AddMemoryFactResponse, status_code=201)
async def add_memory_fact(
    user_id: str,
    payload: AddMemoryFactRequest,
    auth_profile: Annotated[AuthProfile, Depends(check_auth)],
    service: Annotated[MemoryService, Depends(get_memory_service)],
) -> AddMemoryFactResponse:
    effective_user_id = _ensure_owner_access(user_id, auth_profile)
    if payload.user_id and str(payload.user_id) != effective_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id mismatch")

    created = await service.add_fact(
        effective_user_id,
        fact_type=payload.fact_type,
        fact_key=payload.fact_key,
        fact_value=payload.fact_value,
    )
    if not created:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to add memory fact")

    return AddMemoryFactResponse(fact=MemoryFactResponse(**created))


@memory_router.delete("/{user_id}/facts/{fact_id}", status_code=204)
async def delete_memory_fact(
    user_id: str,
    fact_id: str,
    auth_profile: Annotated[AuthProfile, Depends(check_auth)],
    service: Annotated[MemoryService, Depends(get_memory_service)],
) -> None:
    effective_user_id = _ensure_owner_access(user_id, auth_profile)
    deleted = await service.delete_fact(effective_user_id, fact_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fact not found")
    return None
