from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    """重新扫描列画像的入参：只允许指定是否需要重算样例（默认全量）。"""

    refresh_samples: bool = Field(default=True)


class ColumnOut(BaseModel):
    id: str
    table_id: str
    name: str
    data_type: str
    ordinal: int
    column_role: str
    sensitivity_level: str
    null_ratio: float
    distinct_ratio: float
    pii_type: str | None
    pii_confidence: float
    sample_values: list[Any]
    current_policy_id: str | None
    is_scanned: bool
    scanned_at: str | None


class TableOut(BaseModel):
    id: str
    schema_name: str
    table_name: str
    display_name: str
    description: str
    business_domain: str
    row_count: int
    column_count: int
    sensitivity_level: str
    owner_note: str
    last_profiled_at: str | None
    pii_column_count: int = 0


class PiiSummaryOut(BaseModel):
    finding_count: int
    total_matched: int
    checksum_checked: int
    checksum_passed: int
    by_type: dict[str, int]


class TableDetailOut(BaseModel):
    table: TableOut
    columns: list[ColumnOut]
    pii_summary: PiiSummaryOut
