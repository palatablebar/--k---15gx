from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import kanon_controller
from src.middlewares.rate_limit import rate_limit
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.kanon import CheckCreateRequest

router = APIRouter(prefix="/k-anonymity", tags=["k-anonymity"])


@router.get("/checks")
def list_checks(
    user: User = Depends(require_permission("kanon:read")), db: Session = Depends(get_db)
) -> dict:
    return kanon_controller.list_checks(db)


@router.get("/checks/{check_id}")
def detail(
    check_id: str,
    user: User = Depends(require_permission("kanon:read")),
    db: Session = Depends(get_db),
) -> dict:
    return kanon_controller.detail(db, check_id)


@router.post("/checks")
def create(
    payload: CheckCreateRequest,
    request: Request,
    user: User = Depends(require_permission("kanon:run")),
    db: Session = Depends(get_db),
    _: None = rate_limit("kanon"),
) -> dict:
    return kanon_controller.create(db, payload, user, request)
