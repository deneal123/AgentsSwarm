"""
RBAC — Role-Based Access Control.

Использование в роутерах:
    @router.get("/admin-only")
    async def admin_endpoint(
        _: UserContext = Depends(require_role(UserRole.ADMIN)),
    ): ...

    # Или через готовые shortcuts (уже callable, без лишнего Depends):
    @router.delete("/robots/{id}")
    async def delete_robot(
        _: UserContext = Depends(require_operator),
    ): ...

    # Если нужен доступ к UserContext:
    @router.post("/tasks")
    async def create_task(
        current_user: UserContext = Depends(require_operator),
    ): ...
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, status

from gateway_service.auth.middleware import get_current_user
from gateway_service.auth.schemas import ROLE_HIERARCHY, UserContext, UserRole


def require_role(*roles: UserRole) -> Callable:
    """
    Dependency factory: проверяет, что роль пользователя входит в список.

    Возвращает callable (async функцию), пригодную для Depends(...).

    Пример:
        Depends(require_role(UserRole.ADMIN, UserRole.SUPERVISOR))
    """

    async def _dependency(
        current_user: UserContext = Depends(get_current_user),
    ) -> UserContext:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "PERMISSION_DENIED",
                    "message": f"Required role(s): {', '.join(r.value for r in roles)}",
                    "your_role": current_user.role.value,
                },
            )
        return current_user

    return _dependency


def require_min_role(min_role: UserRole) -> Callable:
    """
    Dependency factory: проверяет, что роль пользователя >= min_role по иерархии.

    Возвращает callable (async функцию), пригодную для Depends(...).

    Пример: require_min_role(UserRole.OPERATOR) пропустит OPERATOR, SUPERVISOR, ADMIN.
    """
    min_level = ROLE_HIERARCHY.get(min_role, 999)

    async def _dependency(
        current_user: UserContext = Depends(get_current_user),
    ) -> UserContext:
        user_level = ROLE_HIERARCHY.get(current_user.role, -1)
        if user_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "PERMISSION_DENIED",
                    "message": f"Minimum required role: {min_role.value}",
                    "your_role": current_user.role.value,
                },
            )
        return current_user

    return _dependency


# ─── Готовые shortcuts (callable — используйте в Depends(...)) ───────────────

# Только администраторы
require_admin: Callable = require_role(UserRole.ADMIN)

# Оператор и выше (OPERATOR, SUPERVISOR, ADMIN)
require_operator: Callable = require_min_role(UserRole.OPERATOR)

# Супервизор и выше (SUPERVISOR, ADMIN)
require_supervisor: Callable = require_min_role(UserRole.SUPERVISOR)

# Любой авторизованный пользователь (не ROBOT)
require_authenticated: Callable = require_min_role(UserRole.VIEWER)
