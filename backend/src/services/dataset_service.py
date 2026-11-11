"""数据集与列画像服务：列表、详情、重新扫描（扫描逻辑委托 pii_detector）。"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.models.dataset_column import DatasetColumn
from src.models.dataset_table import DatasetTable
from src.models.pii_finding import PIIFinding
from src.models.user import User
from src.services import audit_service, pii_detector, serializers
from src.utils.errors import AppError, not_found
from src.utils.logger import get_logger, log_info

logger = get_logger("maskguard.dataset")


SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def list_tables(db: Session) -> list[dict[str, Any]]:
    """敏感级别从高到低排（字符串排序会把 medium 排到 critical 前面，必须显式 rank）。"""
    tables = db.query(DatasetTable).all()
    tables.sort(key=lambda table: (SEVERITY_RANK.get(table.sensitivity_level, 9), table.table_name))
    counts = dict(
        db.query(DatasetColumn.table_id, func.count(DatasetColumn.id))
        .filter(DatasetColumn.pii_type.isnot(None))
        .group_by(DatasetColumn.table_id)
        .all()
    )
    return [serializers.table_out(table, int(counts.get(table.id, 0))) for table in tables]


def get_table(db: Session, table_id: str) -> DatasetTable:
    table = db.get(DatasetTable, table_id)
    if table is None:
        raise not_found("数据集表", table_id)
    return table


def list_columns(db: Session, table_id: str) -> list[DatasetColumn]:
    return (
        db.query(DatasetColumn)
        .filter(DatasetColumn.table_id == table_id)
        .order_by(DatasetColumn.ordinal)
        .all()
    )


def get_column(db: Session, column_id: str) -> tuple[DatasetColumn, DatasetTable]:
    column = db.get(DatasetColumn, column_id)
    if column is None:
        raise not_found("数据集列", column_id)
    table = db.get(DatasetTable, column.table_id)
    return column, table


def pii_summary(db: Session, table_id: str) -> dict[str, Any]:
    rows = (
        db.query(PIIFinding, DatasetColumn)
        .join(DatasetColumn, DatasetColumn.id == PIIFinding.column_id)
        .filter(DatasetColumn.table_id == table_id)
        .all()
    )
    by_type: dict[str, int] = {}
    for finding, _column in rows:
        by_type[finding.pii_type] = by_type.get(finding.pii_type, 0) + finding.matched_count
    return {
        "finding_count": len(rows),
        "total_matched": sum(finding.matched_count for finding, _ in rows),
        "checksum_checked": sum(finding.checksum_checked_count for finding, _ in rows),
        "checksum_passed": sum(finding.checksum_pass_count for finding, _ in rows),
        "by_type": by_type,
    }


def table_detail(db: Session, table_id: str) -> dict[str, Any]:
    table = get_table(db, table_id)
    columns = list_columns(db, table_id)
    return {
        "table": serializers.table_out(
            table, len([column for column in columns if column.pii_type])
        ),
        "columns": [serializers.column_out(column) for column in columns],
        "pii_summary": pii_summary(db, table_id),
    }


def list_findings(db: Session, table_id: str | None = None) -> list[dict[str, Any]]:
    query = (
        db.query(PIIFinding, DatasetColumn, DatasetTable)
        .join(DatasetColumn, DatasetColumn.id == PIIFinding.column_id)
        .join(DatasetTable, DatasetTable.id == DatasetColumn.table_id)
    )
    if table_id:
        query = query.filter(DatasetColumn.table_id == table_id)
    rows = query.order_by(DatasetTable.table_name, DatasetColumn.ordinal).all()
    return [serializers.finding_out(finding, column, table) for finding, column, table in rows]


def get_finding_for_column(db: Session, column_id: str) -> dict[str, Any] | None:
    row = (
        db.query(PIIFinding, DatasetColumn, DatasetTable)
        .join(DatasetColumn, DatasetColumn.id == PIIFinding.column_id)
        .join(DatasetTable, DatasetTable.id == DatasetColumn.table_id)
        .filter(PIIFinding.column_id == column_id)
        .order_by(PIIFinding.created_at.desc())
        .first()
    )
    if row is None:
        return None
    finding, column, table = row
    return serializers.finding_out(finding, column, table)


def scan_table(db: Session, table_id: str, user: User, request=None) -> dict[str, Any]:
    table = get_table(db, table_id)
    if not table.table_name:
        raise AppError(codes.VALIDATION_ERROR, "数据集缺少物理表名", table_id)
    result = pii_detector.scan_table(db, table)
    audit_service.record(
        db,
        action="dataset.scan",
        actor=user,
        entity_type="dataset_table",
        entity_id=str(table.id),
        detail={
            "table": table.table_name,
            "columns_scanned": result["columns_scanned"],
            "findings": result["findings"],
            "total_matched": result["total_matched"],
            "checksum_passed": result["checksum_passed"],
        },
        request=request,
    )
    db.commit()
    findings = list_findings(db, table_id)
    log_info(
        logger,
        "pii.scan.done",
        table=table.table_name,
        columns=result["columns_scanned"],
        findings=result["findings"],
    )
    return {
        "table_id": str(table.id),
        "table_name": table.table_name,
        "columns_scanned": result["columns_scanned"],
        "findings": result["findings"],
        "total_matched": result["total_matched"],
        "checksum_passed": result["checksum_passed"],
        "duration_ms": result["duration_ms"],
        "findings_detail": findings,
        "message": f"已扫描 {result['columns_scanned']} 列，命中 {result['findings']} 个 PII 列",
    }
