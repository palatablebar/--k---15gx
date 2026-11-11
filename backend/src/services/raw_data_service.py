"""上游业务库（clinic schema）的只读访问。

原始行不复制进元数据库：算法与导出都直接读 clinic 表，用参数化查询 + 标识符白名单。
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.utils.sql_safety import qualified_table, safe_identifier


def column_values(db: Session, table_name: str, column_name: str, limit: int) -> list[str]:
    sql = text(
        f"SELECT {safe_identifier(column_name)} FROM {qualified_table(settings.raw_schema, table_name)} "
        f"LIMIT :limit"
    )
    rows = db.execute(sql, {"limit": limit}).scalars().all()
    return ["" if value is None else str(value) for value in rows]


def row_count(db: Session, table_name: str) -> int:
    sql = text(f"SELECT count(*) FROM {qualified_table(settings.raw_schema, table_name)}")
    return int(db.execute(sql).scalar_one())


def fetch_rows(
    db: Session,
    table_name: str,
    columns: list[str],
    limit: int,
    order_by: str | None = None,
) -> list[dict[str, Any]]:
    select_list = ", ".join(safe_identifier(column) for column in columns)
    order_clause = f" ORDER BY {safe_identifier(order_by)}" if order_by else ""
    sql = text(
        f"SELECT {select_list} FROM {qualified_table(settings.raw_schema, table_name)}"
        f"{order_clause} LIMIT :limit"
    )
    result = db.execute(sql, {"limit": limit})
    return [dict(row._mapping) for row in result]


def column_stats(db: Session, table_name: str, column_name: str, limit: int) -> dict[str, Any]:
    """空值率 / 唯一性 / 样例：扫描阶段做列画像用。"""
    values = column_values(db, table_name, column_name, limit)
    total = len(values)
    non_empty = [value for value in values if value.strip() != ""]
    distinct = len(set(non_empty))
    return {
        "total": total,
        "null_ratio": round((total - len(non_empty)) / total, 4) if total else 0.0,
        "distinct_ratio": round(distinct / total, 4) if total else 0.0,
        "distinct": distinct,
        "samples": non_empty[:8],
    }
