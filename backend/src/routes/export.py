from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import export_controller
from src.middlewares.rate_limit import rate_limit
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.export import ExportCreateRequest, ReviewRequest

router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("")
def list_requests(
    user: User = Depends(require_permission("exports:read")), db: Session = Depends(get_db)
) -> dict:
    return export_controller.list_requests(db)


@router.post("")
def create(
    payload: ExportCreateRequest,
    request: Request,
    user: User = Depends(require_permission("exports:create")),
    db: Session = Depends(get_db),
    _: None = rate_limit("export"),
) -> dict:
    return export_controller.create(db, payload, user, request)


@router.post("/{request_id}/precheck")
def precheck(
    request_id: str,
    request: Request,
    user: User = Depends(require_permission("exports:approve")),
    db: Session = Depends(get_db),
) -> dict:
    return export_controller.precheck(db, request_id, user, request)


@router.post("/{request_id}/approve")
def approve(
    request_id: str,
    payload: ReviewRequest,
    request: Request,
    user: User = Depends(require_permission("exports:approve")),
    db: Session = Depends(get_db),
) -> dict:
    return export_controller.approve(db, request_id, payload, user, request)


@router.post("/{request_id}/reject")
def reject(
    request_id: str,
    payload: ReviewRequest,
    request: Request,
    user: User = Depends(require_permission("exports:approve")),
    db: Session = Depends(get_db),
) -> dict:
    return export_controller.reject(db, request_id, payload, user, request)


@router.get("/{request_id}/download")
def download(
    request_id: str,
    request: Request,
    user: User = Depends(require_permission("exports:read")),
    db: Session = Depends(get_db),
) -> FileResponse:
    return export_controller.download(db, request_id, user, request)
