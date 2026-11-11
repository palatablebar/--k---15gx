"""PII 证据查询编排。"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.services import dataset_service, serializers
from src.utils.errors import AppError


def list_findings(db: Session, table_id: str | None) -> dict[str, Any]:
    return {"items": dataset_service.list_findings(db, table_id)}


def column_evidence(db: Session, column_id: str) -> dict[str, Any]:
    column, table = dataset_service.get_column(db, column_id)
    finding = dataset_service.get_finding_for_column(db, column_id)
    if finding is None:
        raise AppError(codes.DATASET_NOT_SCANNED, "该列尚无 PII 扫描证据，请先扫描数据集", column_id)
    return {
        "column": serializers.column_out(column),
        "table": serializers.table_out(table),
        "finding": finding,
    }
