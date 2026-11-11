"""导出申请与审批接口编排。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from src.models.user import User
from src.schemas.export import ExportCreateRequest, ReviewRequest
from src.services import audit_service, export_service


def list_requests(db: Session) -> dict[str, Any]:
    return {"items": export_service.list_requests(db)}


def create(db: Session, payload: ExportCreateRequest, user: User, request: Request) -> dict[str, Any]:
    return {"request": export_service.submit(db, user, payload, request)}


def approve(db: Session, request_id: str, payload: ReviewRequest, user: User, request: Request) -> dict[str, Any]:
    return {"request": export_service.approve(db, user, request_id, payload.note, request)}


def reject(db: Session, request_id: str, payload: ReviewRequest, user: User, request: Request) -> dict[str, Any]:
    return {"request": export_service.reject(db, user, request_id, payload.note, request)}


def download(db: Session, request_id: str, user: User, request: Request) -> FileResponse:
    path, export = export_service.artifact_path(db, request_id, user)
    audit_service.record(
        db,
        action="export.download",
        actor=user,
        entity_type="export_request",
        entity_id=str(export.id),
        detail={"digest": export.file_digest, "rows": export.masked_rows},
        request=request,
    )
    db.commit()
    return FileResponse(
        path=Path(path),
        media_type="text/csv",
        filename=f"masked-export-{export.id}.csv",
    )
