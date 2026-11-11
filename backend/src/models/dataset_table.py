from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, new_uuid


class DatasetTable(Base, TimestampMixin):
    """上游业务库表的数据集登记（元数据，不复制原始行）。"""

    __tablename__ = "dataset_tables"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    schema_name: Mapped[str] = mapped_column(String(63), nullable=False, default="clinic")
    table_name: Mapped[str] = mapped_column(String(63), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    business_domain: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    column_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sensitivity_level: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    owner_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    last_profiled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
