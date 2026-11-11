"""审计日志查询编排。"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.models.audit_log import AuditLog
from src.services import serializers


def list_logs(db: Session, limit: int = 50, action: str | None = None) -> dict[str, Any]:
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    logs = query.order_by(AuditLog.created_at.desc()).limit(min(limit, 200)).all()
    return {"items": [serializers.audit_out(log) for log in logs]}
