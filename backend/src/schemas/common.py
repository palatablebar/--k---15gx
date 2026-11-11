"""公共序列化小工具：时间统一 ISO8601，None 保持 None。"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any


def iso(value: datetime | date | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return value.isoformat()


def as_float(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def serialize_columns_brief(columns: list[Any]) -> list[dict[str, Any]]:
    return [{"name": column.name, "data_type": column.data_type} for column in columns]
