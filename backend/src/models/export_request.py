from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, new_uuid


class ExportRequest(Base, TimestampMixin):
    """导出申请与审批台账：谁申请、用途、状态、脱敏文件摘要。"""

    __tablename__ = "export_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_tables.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    purpose: Mapped[str] = mapped_column(String(400), nullable=False)
    requested_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dataset_version: Mapped[str] = mapped_column(String(40), nullable=False, default="2026-11")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    build_status: Mapped[str] = mapped_column(String(20), nullable=False, default="idle")
    review_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(400), nullable=True)
    file_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    masked_rows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    applied_policies_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
