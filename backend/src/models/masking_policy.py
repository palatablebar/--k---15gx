from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, new_uuid


class MaskingPolicy(Base, TimestampMixin):
    """列级掩码策略：方法（mask/hash/generalize/suppress）+ 参数 + 适用范围。"""

    __tablename__ = "masking_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    table_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_tables.id", ondelete="SET NULL"), nullable=True, index=True
    )
    column_pattern: Mapped[str] = mapped_column(String(120), nullable=False, default="*")
    pii_type: Mapped[str | None] = mapped_column(String(24), nullable=True)
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    params_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
