from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    # 演示域名 clinic.local 属于保留域，EmailStr 会按 RFC 特殊用途域名拒收；
    # 这里用宽松正则即可（真实系统可换成企业 SSO / 域名白名单）。
    email: str = Field(
        min_length=5,
        max_length=200,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    password: str = Field(min_length=1, max_length=200)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


def serialize_user(user: Any) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "organization": user.organization,
        "is_active": user.is_active,
        "last_login_at": user.last_login_at.isoformat() if isinstance(user.last_login_at, datetime) else None,
        "created_at": user.created_at.isoformat() if isinstance(user.created_at, datetime) else None,
    }
