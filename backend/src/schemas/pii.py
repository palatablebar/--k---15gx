from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class EvidenceSampleOut(BaseModel):
    value: str
    display_value: str
    kind: str  # match / miss
    span_start: int
    span_end: int
    validation: str  # passed / failed / not_applicable
    note: str = ""


class FindingOut(BaseModel):
    id: str
    column_id: str
    column_name: str
    table_id: str
    table_name: str
    pii_type: str
    scanned_rows: int
    candidate_rows: int
    matched_count: int
    checksum_checked_count: int
    checksum_pass_count: int
    hit_rate: float
    checksum_pass_rate: float
    uniqueness_penalty: float
    confidence: float
    algorithm_version: str
    sample_values: list[Any]
    evidence: list[EvidenceSampleOut]
    created_at: str | None


class ScanResultOut(BaseModel):
    table_id: str
    table_name: str
    columns_scanned: int
    findings: int
    total_matched: int
    checksum_passed: int
    duration_ms: int
    findings_detail: list[FindingOut]
    message: str
