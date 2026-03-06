"""
Unit-тесты: RBAC (auth/permissions.py) и UserRole hierarchy.

Покрывает:
  - has_role_or_higher: все комбинации ролей
  - require_role: пропускает нужные роли, блокирует остальные
  - require_min_role: иерархическая проверка
  - UserContext properties: is_admin, is_operator_or_higher
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from gateway_service.auth.permissions import (
    require_admin,
    require_authenticated,
    require_min_role,
    require_operator,
    require_role,
    require_supervisor,
)
from gateway_service.auth.schemas import (
    ROLE_HIERARCHY,
    UserContext,
    UserRole,
    has_role_or_higher,
)


# ─── has_role_or_higher ───────────────────────────────────────────────────────


@pytest.mark.parametrize("user_role,required,expected", [
    (UserRole.ADMIN,      UserRole.ADMIN,      True),
    (UserRole.ADMIN,      UserRole.VIEWER,     True),
    (UserRole.SUPERVISOR, UserRole.OPERATOR,   True),
    (UserRole.OPERATOR,   UserRole.OPERATOR,   True),
    (UserRole.VIEWER,     UserRole.OPERATOR,   False),
    (UserRole.VIEWER,     UserRole.ADMIN,      False),
    (UserRole.ROBOT,      UserRole.OPERATOR,   False),
    (UserRole.OPERATOR,   UserRole.SUPERVISOR, False),
])
def test_has_role_or_higher(user_role: UserRole, required: UserRole, expected: bool) -> None:
    assert has_role_or_higher(user_role, required) == expected


def test_role_hierarchy_all_roles_present() -> None:
    for role in UserRole:
        assert role in ROLE_HIERARCHY, f"Role {role} missing from ROLE_HIERARCHY"


def test_role_hierarchy_admin_highest() -> None:
    admin_level = ROLE_HIERARCHY[UserRole.ADMIN]
    for role, level in ROLE_HIERARCHY.items():
        if role != UserRole.ADMIN:
            assert admin_level > level


def test_role_hierarchy_viewer_lowest_human() -> None:
    viewer_level = ROLE_HIERARCHY[UserRole.VIEWER]
    for role in [UserRole.OPERATOR, UserRole.SUPERVISOR, UserRole.ADMIN]:
        assert ROLE_HIERARCHY[role] > viewer_level


# ─── UserContext properties ───────────────────────────────────────────────────


def _make_user(role: UserRole) -> UserContext:
    return UserContext(
        user_id="test-id",
        username="testuser",
        email="test@test.com",
        role=role,
    )


def test_user_context_is_admin_true() -> None:
    user = _make_user(UserRole.ADMIN)
    assert user.is_admin is True


def test_user_context_is_admin_false() -> None:
    user = _make_user(UserRole.OPERATOR)
    assert user.is_admin is False


@pytest.mark.parametrize("role,expected", [
    (UserRole.OPERATOR,   True),
    (UserRole.SUPERVISOR, True),
    (UserRole.ADMIN,      True),
    (UserRole.VIEWER,     False),
    (UserRole.ROBOT,      False),
])
def test_user_context_is_operator_or_higher(role: UserRole, expected: bool) -> None:
    user = _make_user(role)
    assert user.is_operator_or_higher == expected


# ─── require_role dependency (вызываем функции напрямую) ──────────────────────
# require_role / require_min_role возвращают callable async функции.
# Shortcuts (require_admin, require_operator и т.д.) уже являются этими функциями.


@pytest.mark.asyncio
async def test_require_role_allows_matching() -> None:
    dep_fn = require_role(UserRole.ADMIN, UserRole.SUPERVISOR)
    user = _make_user(UserRole.ADMIN)
    result = await dep_fn(current_user=user)
    assert result.role == UserRole.ADMIN


@pytest.mark.asyncio
async def test_require_role_blocks_wrong_role() -> None:
    dep_fn = require_role(UserRole.ADMIN)
    user = _make_user(UserRole.OPERATOR)

    with pytest.raises(HTTPException) as exc_info:
        await dep_fn(current_user=user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_min_role_allows_higher() -> None:
    dep_fn = require_min_role(UserRole.OPERATOR)
    user = _make_user(UserRole.ADMIN)
    result = await dep_fn(current_user=user)
    assert result.role == UserRole.ADMIN


@pytest.mark.asyncio
async def test_require_min_role_blocks_lower() -> None:
    dep_fn = require_min_role(UserRole.OPERATOR)
    user = _make_user(UserRole.VIEWER)

    with pytest.raises(HTTPException) as exc_info:
        await dep_fn(current_user=user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_admin_blocks_supervisor() -> None:
    user = _make_user(UserRole.SUPERVISOR)
    with pytest.raises(HTTPException):
        await require_admin(current_user=user)


@pytest.mark.asyncio
async def test_require_operator_allows_supervisor() -> None:
    user = _make_user(UserRole.SUPERVISOR)
    result = await require_operator(current_user=user)
    assert result is user


@pytest.mark.asyncio
async def test_require_authenticated_allows_viewer() -> None:
    user = _make_user(UserRole.VIEWER)
    result = await require_authenticated(current_user=user)
    assert result is user
