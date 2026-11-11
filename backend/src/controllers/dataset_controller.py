"""数据集与列画像接口编排。"""
from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from src.models.user import User
from src.services import dataset_service, serializers


def list_tables(db: Session) -> dict[str, Any]:
    return {"items": dataset_service.list_tables(db)}


def table_detail(db: Session, table_id: str) -> dict[str, Any]:
    return dataset_service.table_detail(db, table_id)


def list_columns(db: Session, table_id: str) -> dict[str, Any]:
    dataset_service.get_table(db, table_id)
    columns = dataset_service.list_columns(db, table_id)
    return {"items": [serializers.column_out(column) for column in columns]}


def scan(db: Session, table_id: str, user: User, request: Request) -> dict[str, Any]:
    return dataset_service.scan_table(db, table_id, user, request)
