"""导出申请与审批台账 + 脱敏文件生成（worker 执行，backend 同步兜底）。

文件生成口径：按列顺序读原始行 → 每列匹配生效策略 → 逐值掩码 → 写 CSV 到共享卷
→ 计算 sha256 摘要与行数落库。前后端都不缓存在进程内存里。
"""
from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from src.config.celery_app import dispatch
from src.config.settings import settings
from src.constants import error_codes as codes
from src.constants.enums import ExportStatus
from src.constants.limits import EXPORT_MAX_ROWS
from src.models.dataset_column import DatasetColumn
from src.models.dataset_table import DatasetTable
from src.models.export_request import ExportRequest
from src.models.user import User
from src.services import audit_service, masking_service, policy_service, raw_data_service, serializers
from src.utils.checksum import sha256_bytes
from src.utils.errors import AppError, not_found
from src.utils.logger import get_logger, log_error, log_info

logger = get_logger("maskguard.export")

EXPORT_TASK = "maskguard.build_export"


def export_dir() -> Path:
    path = Path(settings.artifact_dir) / "exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def list_requests(db: Session) -> list[dict[str, Any]]:
    rows = (
        db.query(ExportRequest, DatasetTable, User)
        .join(DatasetTable, DatasetTable.id == ExportRequest.table_id)
        .join(User, User.id == ExportRequest.requester_id)
        .order_by(ExportRequest.created_at.desc())
        .all()
    )
    reviewer_ids = {row[0].reviewed_by for row in rows if row[0].reviewed_by}
    reviewers = {
        user.id: user for user in db.query(User).filter(User.id.in_(reviewer_ids)).all()
    } if reviewer_ids else {}
    return [
        serializers.export_out(request, table, requester, reviewers.get(request.reviewed_by))
        for request, table, requester in rows
    ]


def get_request(db: Session, request_id: str) -> ExportRequest:
    request = db.get(ExportRequest, request_id)
    if request is None:
        raise not_found("导出申请", request_id)
    return request


def submit(db: Session, user: User, payload: Any, request=None) -> dict[str, Any]:
    table = db.get(DatasetTable, payload.table_id)
    if table is None:
        raise not_found("数据集表", payload.table_id)
    export = ExportRequest(
        requester_id=user.id,
        table_id=table.id,
        purpose=payload.purpose,
        requested_rows=min(payload.requested_rows, EXPORT_MAX_ROWS),
        dataset_version="2026-11",
        status=ExportStatus.PENDING.value,
        build_status="idle",
    )
    db.add(export)
    db.flush()
    audit_service.record(
        db,
        action="export.submit",
        actor=user,
        entity_type="export_request",
        entity_id=str(export.id),
        detail={"table": table.table_name, "purpose": payload.purpose, "rows": export.requested_rows},
        request=request,
    )
    db.commit()
    db.refresh(export)
    return serializers.export_out(export, table, user, None)


def approve(db: Session, reviewer: User, request_id: str, note: str, request=None) -> dict[str, Any]:
    export = get_request(db, request_id)
    if export.status != ExportStatus.PENDING.value:
        raise AppError(codes.EXPORT_NOT_PENDING, None, f"status={export.status}")
    table = db.get(DatasetTable, export.table_id)
    export.status = ExportStatus.APPROVED.value
    export.build_status = "queued"
    export.review_note = note
    export.reviewed_by = reviewer.id
    export.reviewed_at = _now()
    audit_service.record(
        db,
        action="export.approve",
        actor=reviewer,
        entity_type="export_request",
        entity_id=str(export.id),
        detail={"table": table.table_name if table else "", "note": note},
        request=request,
    )
    db.commit()

    task_id = dispatch(EXPORT_TASK, request_id=str(export.id))
    if task_id is None:
        # broker 不可用：同步兜底，保证审批不会留下永远 queued 的台账
        build_export(db, str(export.id))
    requester = db.get(User, export.requester_id)
    reviewer_row = db.get(User, reviewer.id)
    db.refresh(export)
    return serializers.export_out(export, table, requester, reviewer_row)


def reject(db: Session, reviewer: User, request_id: str, note: str, request=None) -> dict[str, Any]:
    export = get_request(db, request_id)
    if export.status != ExportStatus.PENDING.value:
        raise AppError(codes.EXPORT_NOT_PENDING, None, f"status={export.status}")
    table = db.get(DatasetTable, export.table_id)
    export.status = ExportStatus.REJECTED.value
    export.review_note = note
    export.reviewed_by = reviewer.id
    export.reviewed_at = _now()
    audit_service.record(
        db,
        action="export.reject",
        actor=reviewer,
        entity_type="export_request",
        entity_id=str(export.id),
        detail={"table": table.table_name if table else "", "note": note},
        request=request,
    )
    db.commit()
    db.refresh(export)
    return serializers.export_out(export, table, db.get(User, export.requester_id), reviewer)


def build_export(db: Session, request_id: str) -> dict[str, Any]:
    """真正生成脱敏 CSV：读原始行、逐列套策略、写共享卷、落摘要。"""
    export = get_request(db, request_id)
    table = db.get(DatasetTable, export.table_id)
    if table is None:
        raise not_found("数据集表", export.table_id)
    export.build_status = "running"
    db.commit()
    try:
        columns = (
            db.query(DatasetColumn)
            .filter(DatasetColumn.table_id == table.id)
            .order_by(DatasetColumn.ordinal)
            .all()
        )
        policies = {column.id: policy_service.policy_for_column(db, column) for column in columns}
        limit = min(export.requested_rows or EXPORT_MAX_ROWS, EXPORT_MAX_ROWS)
        rows = raw_data_service.fetch_rows(
            db,
            table.table_name,
            [column.name for column in columns],
            limit,
            order_by=columns[0].name if columns else None,
        )

        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow([column.name for column in columns])
        for row in rows:
            writer.writerow(
                [
                    masking_service.mask_value_with_policy(
                        column.name, str(row.get(column.name, "") or ""), policies.get(column.id)
                    )
                    for column in columns
                ]
            )
        payload = buffer.getvalue().encode("utf-8")
        digest = sha256_bytes(payload)
        target = export_dir() / f"export-{export.id}.csv"
        target.write_bytes(payload)

        export.build_status = "done"
        export.file_path = str(target)
        export.file_digest = digest
        export.masked_rows = len(rows)
        export.error_detail = None
        export.applied_policies_json = [
            {
                "name": policy.name,
                "method": policy.method,
                "column": column.name,
                "policy_id": str(policy.id),
            }
            for column in columns
            if (policy := policies.get(column.id)) is not None
        ]
        db.commit()
        log_info(
            logger,
            "export.build",
            request=str(export.id),
            rows=export.masked_rows,
            digest=digest,
        )
        return {
            "request_id": str(export.id),
            "rows": export.masked_rows,
            "digest": digest,
            "applied_policies": [item["name"] for item in export.applied_policies_json],
        }
    except Exception as exc:  # noqa: BLE001 - 失败必须落库
        export.build_status = "failed"
        export.error_detail = str(exc)[:400]
        db.commit()
        log_error(logger, "export.failed", request=request_id, reason=exc)
        raise


def artifact_path(db: Session, request_id: str, user: User) -> tuple[Path, ExportRequest]:
    export = get_request(db, request_id)
    if export.status != ExportStatus.APPROVED.value:
        raise AppError(codes.EXPORT_NOT_READY, None, f"status={export.status}")
    if export.build_status != "done" or not export.file_path:
        raise AppError(codes.EXPORT_NOT_READY, None, f"build_status={export.build_status}")
    allowed = user.role in ("admin", "dpo") or str(export.requester_id) == str(user.id)
    if not allowed:
        raise AppError(codes.EXPORT_DOWNLOAD_DENIED, None, f"user={user.email}")
    path = Path(export.file_path)
    if not path.exists():
        raise AppError(codes.EXPORT_NOT_READY, "导出文件已丢失，请重新审批生成", str(path))
    return path, export


def _now():
    from src.models.base import utcnow

    return utcnow()
