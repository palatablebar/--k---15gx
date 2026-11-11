"""RBAC：require_role(*roles) / require_permission(action)。"""
from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends

from src.constants import error_codes as codes
from src.constants.roles import role_can
from src.middlewares.auth import get_current_user
from src.models.user import User
from src.utils.errors import AppError


def require_role(*roles: str) -> Callable[..., User]:
    allowed = tuple(roles)

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise AppError(
                codes.FORBIDDEN,
                f"当前角色（{user.role}）无权执行该操作",
                f"role={user.role} required={allowed}",
            )
        return user

    return dependency


def require_permission(action: str) -> Callable[..., User]:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if not role_can(user.role, action):
            raise AppError(
                codes.FORBIDDEN,
                f"当前角色（{user.role}）无 {action} 权限",
                f"role={user.role} action={action}",
            )
        return user

    return dependency
