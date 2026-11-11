"""认证编排：登录写审计、刷新令牌、当前用户、用户列表。"""
from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from src.models.base import utcnow
from src.models.user import User
from src.schemas.auth import LoginRequest, RefreshRequest, serialize_user
from src.services import audit_service, auth_service
from src.utils.logger import get_logger, log_info

logger = get_logger("maskguard.auth")


def login(request: Request, payload: LoginRequest, db: Session) -> dict[str, Any]:
    user = auth_service.authenticate(db, payload.email, payload.password)
    user.last_login_at = utcnow()
    audit_service.record(
        db,
        action="login",
        actor=user,
        entity_type="user",
        entity_id=str(user.id),
        detail={"role": user.role, "organization": user.organization},
        request=request,
    )
    db.commit()
    db.refresh(user)
    log_info(logger, "auth.login", email=user.email, role=user.role, ok=True)
    return {**auth_service.issue_tokens(user), "user": serialize_user(user)}


def refresh(payload: RefreshRequest, db: Session) -> dict[str, Any]:
    return auth_service.refresh(db, payload.refresh_token)


def me(user: User) -> dict[str, Any]:
    return {"user": serialize_user(user)}


def list_users(db: Session) -> dict[str, Any]:
    users = db.query(User).order_by(User.role, User.email).all()
    return {"items": [serialize_user(item) for item in users]}
