"""审计日志：所有写操作都落一条，审批与脱敏动作可追溯。"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session
from starlette.requests import Request

from src.models.audit_log import AuditLog
from src.models.user import User
from src.utils.logger import get_logger

logger = get_logger("maskguard.audit")


def record(
    db: Session,
    *,
    action: str,
    actor: User | None = None,
    entity_type: str = "",
    entity_id: str = "",
    detail: dict[str, Any] | None = None,
    request: Request | None = None,
) -> AuditLog:
    log = AuditLog(
        actor_id=actor.id if actor else None,
        actor_email=actor.email if actor else "",
        actor_role=actor.role if actor else "",
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id)[:64],
        detail_json=detail or {},
        ip=_client_ip(request),
        trace_id=getattr(request.state, "trace_id", "") if request else "",
    )
    db.add(log)
    return log


def _client_ip(request: Request | None) -> str:
    if request is None:
        return ""
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded:
        return forwarded[:64]
    return request.client.host[:64] if request.client else ""


def serialize_many(logs: list[AuditLog]) -> list[dict[str, Any]]:
    from src.services.serializers import audit_out

    return [audit_out(log) for log in logs]
