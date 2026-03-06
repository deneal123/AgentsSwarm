"""Корневой роутер API v1 — объединяет все суб-роутеры."""

from __future__ import annotations

from fastapi import APIRouter

from gateway_service.api.v1.chat import router as chat_router
from gateway_service.api.v1.robots import router as robots_router
from gateway_service.api.v1.tasks import router as tasks_router
from gateway_service.api.v1.telemetry import router as telemetry_router
from gateway_service.api.v1.users import router as users_router
from gateway_service.api.v1.zones import router as zones_router

api_v1_router = APIRouter()

# Аутентификация — prefix="/auth" задан непосредственно в users.py
api_v1_router.include_router(users_router)

# REST API ресурсы
api_v1_router.include_router(robots_router,    prefix="/robots",    tags=["robots"])
api_v1_router.include_router(tasks_router,     prefix="/tasks",     tags=["tasks"])
api_v1_router.include_router(zones_router,     prefix="/zones",     tags=["zones"])
api_v1_router.include_router(chat_router,      prefix="/chat",      tags=["chat"])
api_v1_router.include_router(telemetry_router, prefix="/telemetry", tags=["telemetry"])
