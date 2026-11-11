from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, new_uuid


class DatasetColumn(Base, TimestampMixin):
    """列画像：类型、样例、空值/唯一性统计、PII 类型与置信度、列角色。"""

    __tablename__ = "dataset_columns"
    __table_args__ = (UniqueConstraint("table_id", "name", name="uq_dataset_column_table_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_tables.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(63), nullable=False)
    data_type: Mapped[str] = mapped_column(String(32), nullable=False, default="text")
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    column_role: Mapped[str] = mapped_column(String(24), nullable=False, default="non_sensitive")
    sensitivity_level: Mapped[str] = mapped_column(String(20), nullable=False, default="low")
    null_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    distinct_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pii_type: Mapped[str | None] = mapped_column(String(24), nullable=True)
    pii_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sample_values_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    current_policy_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    is_scanned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
