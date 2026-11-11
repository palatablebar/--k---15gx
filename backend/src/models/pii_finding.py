from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, utcnow, new_uuid


class PIIFinding(Base, ):
    """一次 PII 扫描的列级证据：命中数、校验位数、置信度拆解、样例证据。"""

    __tablename__ = "pii_findings"
    __table_args__ = (UniqueConstraint("column_id", "algorithm_version", name="uq_pii_finding_column_version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    column_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_columns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pii_type: Mapped[str] = mapped_column(String(24), nullable=False)
    scanned_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    candidate_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    matched_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checksum_checked_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checksum_pass_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hit_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    checksum_pass_rate: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    uniqueness_penalty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    evidence_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    algorithm_version: Mapped[str] = mapped_column(String(32), nullable=False, default="pii-1.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
