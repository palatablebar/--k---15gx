"""认证中间件：Bearer → request.state.user；健康检查与登录白名单。"""
from __future__ import annotations

from typing import Any

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants import error_codes as codes
from src.models.user import User
from src.utils.errors import AppError
from src.utils.jwt import decode_token

PUBLIC_PATHS = ("/health", "/api/health", "/auth/login", "/api/auth/login", "/docs", "/openapi.json")


def _extract_bearer(request: Request) -> str | None:
    header = request.headers.get("authorization") or ""
    if not header.lower().startswith("bearer "):
        return None
    return header.split(" ", 1)[1].strip()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = _extract_bearer(request)
    if not token:
        raise AppError(codes.AUTH_REQUIRED, "请先登录", "missing Authorization header")
    payload = decode_token(token)
    user = db.get(User, payload.get("sub"))
    if user is None or not user.is_active:
        raise AppError(codes.AUTH_INVALID, "登录状态无效，请重新登录", "user missing/inactive")
    request.state.user = user
    return user


def optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    try:
        return get_current_user(request, db)
    except AppError:
        return None


def current_user_payload(user: User) -> dict[str, Any]:
    from src.schemas.auth import serialize_user

    return serialize_user(user)
