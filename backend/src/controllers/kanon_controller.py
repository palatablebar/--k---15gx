"""k-匿名校验编排：创建 → 投递 worker（失败同步兜底）→ 查询结果。"""
from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from src.config.celery_app import dispatch
from src.models.dataset_table import DatasetTable
from src.models.k_anonymity_check import KAnonymityCheck
from src.models.user import User
from src.schemas.kanon import CheckCreateRequest
from src.services import audit_service, k_anonymity_service, serializers
from src.utils.logger import get_logger, log_info

logger = get_logger("maskguard.kanon")
KANON_TASK = "maskguard.run_k_anonymity"


def _serialize(db: Session, check: KAnonymityCheck) -> dict[str, Any]:
    table = db.get(DatasetTable, check.table_id)
    creator = db.get(User, check.created_by) if check.created_by else None
    return serializers.check_out(check, table.table_name if table else "", creator.email if creator else None)


def list_checks(db: Session) -> dict[str, Any]:
    checks = db.query(KAnonymityCheck).order_by(KAnonymityCheck.created_at.desc()).all()
    return {"items": [_serialize(db, check) for check in checks]}


def detail(db: Session, check_id: str) -> dict[str, Any]:
    check = k_anonymity_service_and_get(db, check_id)
    return {"check": _serialize(db, check)}


def k_anonymity_service_and_get(db: Session, check_id: str) -> KAnonymityCheck:
    from src.utils.errors import not_found

    check = db.get(KAnonymityCheck, check_id)
    if check is None:
        raise not_found("k-匿名校验", check_id)
    return check


def create(db: Session, payload: CheckCreateRequest, user: User, request: Request) -> dict[str, Any]:
    check = k_anonymity_service.create_check(db, user, payload)
    task_id = dispatch(KANON_TASK, check_id=str(check.id))
    check.task_id = task_id
    db.commit()
    audit_service.record(
        db,
        action="kanon.check",
        actor=user,
        entity_type="k_anonymity_check",
        entity_id=str(check.id),
        detail={
            "table": payload.table_id,
            "qi": payload.quasi_identifiers,
            "sensitive": payload.sensitive_column,
            "target_k": payload.target_k,
            "target_l": payload.target_l,
            "mode": "worker" if task_id else "sync",
        },
        request=request,
    )
    db.commit()
    if task_id is None:
        # broker 不可用：同步兜底，保证结果立即可查
        check.status = "running"
        db.commit()
        k_anonymity_service.execute_check(db, check)
    log_info(
        logger,
        "kanon.start",
        table=payload.table_id,
        qi=",".join(payload.quasi_identifiers),
        k=payload.target_k,
    )
    db.refresh(check)
    return {"check": _serialize(db, check)}
