"""掩码策略接口编排。"""
from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from src.models.user import User
from src.schemas.policy import PolicyCreateRequest, PolicyUpdateRequest
from src.services import audit_service, policy_service


def list_policies(db: Session) -> dict[str, Any]:
    return {"items": policy_service.list_policies(db)}


def detail(db: Session, policy_id: str) -> dict[str, Any]:
    policy = policy_service.get_policy(db, policy_id)
    return {"policy": policy_service.serialize(policy, None)}


def create(db: Session, payload: PolicyCreateRequest, user: User, request: Request) -> dict[str, Any]:
    result = policy_service.create_policy(db, user, payload)
    audit_service.record(
        db,
        action="policy.create",
        actor=user,
        entity_type="masking_policy",
        entity_id=result["id"],
        detail={"name": result["name"], "method": result["method"], "pattern": result["column_pattern"]},
        request=request,
    )
    db.commit()
    return {"policy": result}


def update(
    db: Session, policy_id: str, payload: PolicyUpdateRequest, user: User, request: Request
) -> dict[str, Any]:
    result = policy_service.update_policy(db, policy_id, payload)
    audit_service.record(
        db,
        action="policy.update",
        actor=user,
        entity_type="masking_policy",
        entity_id=policy_id,
        detail={
            "name": result["name"],
            "method": result["method"],
            "params": result["params"],
            "is_active": result["is_active"],
        },
        request=request,
    )
    db.commit()
    return {"policy": result}


def preview(db: Session, policy_id: str, user: User, request: Request) -> dict[str, Any]:
    result = policy_service.preview_policy(db, policy_id)
    audit_service.record(
        db,
        action="policy.preview",
        actor=user,
        entity_type="masking_policy",
        entity_id=policy_id,
        detail={
            "columns": [item["column_name"] for item in result["applied_columns"]],
            "rows": result["total_rows"],
        },
        request=request,
    )
    db.commit()
    return result
