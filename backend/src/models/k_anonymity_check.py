from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, new_uuid


class KAnonymityCheck(Base, TimestampMixin):
    """k-匿名 / ℓ-diversity 校验记录：准标识组合、泛化层级、等价类分布、结论。"""

    __tablename__ = "k_anonymity_checks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_tables.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quasi_identifiers_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    sensitive_column: Mapped[str] = mapped_column(String(63), nullable=False)
    target_k: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    target_l: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", index=True)
    base_k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    base_l: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_l: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passed: Mapped[bool | None] = mapped_column(nullable=True)
    recommended_level_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    candidates_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    equivalence_classes_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    class_size_histogram_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    information_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    conclusion: Mapped[str] = mapped_column(String(400), nullable=False, default="")
    # 执行时参与计算的 QI+敏感列数据签名：数据一旦变化，本次结论即失效
    data_signature: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
