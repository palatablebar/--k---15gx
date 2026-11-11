from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AuditOut(BaseModel):
    id: str
    actor_email: str
    actor_role: str
    action: str
    entity_type: str
    entity_id: str
    detail: dict[str, Any]
    ip: str
    trace_id: str
    created_at: str | None
