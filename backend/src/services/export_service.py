"""导出申请与审批台账 + 脱敏文件生成（worker 执行，backend 同步兜底）。

文件生成口径：按列顺序读原始行 → 每列匹配生效策略 → 逐值掩码 → 写 CSV 到共享卷
→ 计算 sha256 摘要与行数落库。前后端都不缓存在进程内存里。

审批门禁：批准前必须通过 export_gate 的现行环境评估（范围 × 策略 × 校验 × 数据），
被拦截的申请落缺口明细；状态认领用条件 UPDATE 保证并发下同一申请只会放行一次。
"""
from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

from sqlalchemy import update
from sqlalchemy.orm import Session

from src.config.celery_app import dispatch
from src.config.settings import settings
from src.constants import error_codes as codes
from src.constants.enums import ExportStatus, GateStatus
from src.constants.limits import EXPORT_MAX_ROWS
from src.models.dataset_column import DatasetColumn
from src.models.dataset_table import DatasetTable
from src.models.export_request import ExportRequest
from src.models.user import User
from src.services import (
    audit_service,
    export_gate,
    masking_service,
    policy_service,
    raw_data_service,
    serializers,
)
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
    # 现行环境指纹按表缓存：同表申请共享一份，判断各自结论是否已失效
    fingerprints: dict[Any, str] = {}
    items: list[dict[str, Any]] = []
    for request, table, requester in rows:
        if table.id not in fingerprints:
            fingerprints[table.id] = export_gate.current_fingerprint(db, table)
        stale = export_gate.is_stale(request, fingerprints[table.id])
        items.append(
            serializers.export_out(
                request, table, requester, reviewers.get(request.reviewed_by), gate_stale=stale
            )
        )
    return items


def get_request(db: Session, request_id: str) -> ExportRequest:
    request = db.get(ExportRequest, request_id)
    if request is None:
        raise not_found("导出申请", request_id)
    return request


def _serialize(db: Session, export: ExportRequest, reviewer: User | None) -> dict[str, Any]:
    table = db.get(DatasetTable, export.table_id)
    requester = db.get(User, export.requester_id)
    stale = export_gate.is_stale(export, export_gate.current_fingerprint(db, table)) if table else False
    return serializers.export_out(export, table, requester, reviewer, gate_stale=stale)


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


def precheck(db: Session, reviewer: User, request_id: str, request=None) -> dict[str, Any]:
    """合规校验：按现行环境重估门禁并落结论。幂等——重复执行只刷新结论，无副作用。"""
    export = get_request(db, request_id)
    if export.status != ExportStatus.PENDING.value:
        raise AppError(codes.EXPORT_NOT_PENDING, None, f"status={export.status}")
    verdict = export_gate.evaluate(db, export)
    export_gate.apply_verdict(export, verdict)
    table = db.get(DatasetTable, export.table_id)
    audit_service.record(
        db,
        action="export.precheck",
        actor=reviewer,
        entity_type="export_request",
        entity_id=str(export.id),
        detail={
            "table": table.table_name if table else "",
            "passed": verdict["passed"],
            "gaps": [gap["code"] for gap in verdict["gaps"]],
        },
        request=request,
    )
    db.commit()
    log_info(
        logger,
        "export.gate",
        request=str(export.id),
        passed=verdict["passed"],
        gaps=len(verdict["gaps"]),
    )
    return _serialize(db, export, reviewer)


def approve(db: Session, reviewer: User, request_id: str, note: str, request=None) -> dict[str, Any]:
    export = get_request(db, request_id)
    if export.status != ExportStatus.PENDING.value:
        raise AppError(codes.EXPORT_NOT_PENDING, None, f"status={export.status}")
    table = db.get(DatasetTable, export.table_id)

    # 门禁：永远按现行环境重评，不采信任何历史结论
    verdict = export_gate.evaluate(db, export)
    if not verdict["passed"]:
        export_gate.apply_verdict(export, verdict)
        audit_service.record(
            db,
            action="export.blocked",
            actor=reviewer,
            entity_type="export_request",
            entity_id=str(export.id),
            detail={
                "table": table.table_name if table else "",
                "note": note,
                "gaps": [gap["code"] for gap in verdict["gaps"]],
            },
            request=request,
        )
        db.commit()
        log_info(
            logger,
            "export.blocked",
            request=str(export.id),
            gaps=",".join(gap["code"] for gap in verdict["gaps"]),
        )
        raise AppError(
            codes.EXPORT_GATE_BLOCKED,
            None,
            f"request={request_id} gaps={len(verdict['gaps'])}",
            extra={"gaps": verdict["gaps"], "snapshot": verdict["snapshot"]},
        )

    # 原子认领：并发重复批准只有第一个生效，不会再次放行
    claimed = db.execute(
        update(ExportRequest)
        .where(
            ExportRequest.id == export.id,
            ExportRequest.status == ExportStatus.PENDING.value,
        )
        .values(
            status=ExportStatus.APPROVED.value,
            build_status="queued",
            review_note=note,
            reviewed_by=reviewer.id,
            reviewed_at=_now(),
            gate_status=GateStatus.PASSED.value,
            gate_gaps_json=[],
            gate_fingerprint=verdict["fingerprint"],
            gate_snapshot_json=verdict["snapshot"],
            gate_checked_at=_now(),
        )
    )
    if claimed.rowcount != 1:
        db.rollback()
        raise AppError(codes.EXPORT_NOT_PENDING, None, f"status={export.status}")
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
        build_export(db, export.id)
    db.refresh(export)
    return _serialize(db, export, db.get(User, reviewer.id))


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
    return _serialize(db, export, reviewer)


def build_export(db: Session, request_id: str) -> dict[str, Any]:
    """真正生成脱敏 CSV：读原始行、逐列套策略、写共享卷、落摘要。

    幂等：未批准的申请不生成；已生成（done 且文件在）直接返回既有摘要，
    同一申请重复执行不会新增文件、不会改写已放行产物。
    """
    export = get_request(db, request_id)
    if export.status != ExportStatus.APPROVED.value:
        raise AppError(
            codes.EXPORT_NOT_READY,
            "导出申请未获批准，不能生成文件",
            f"request={request_id} status={export.status}",
        )
    if export.build_status == "done" and export.file_path and Path(export.file_path).exists():
        log_info(logger, "export.build.skip", request=request_id, digest=export.file_digest)
        return {
            "request_id": str(export.id),
            "rows": export.masked_rows,
            "digest": export.file_digest,
            "applied_policies": [
                str(item.get("name", "")) for item in (export.applied_policies_json or [])
            ],
            "skipped": True,
        }
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
