from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import pii_controller
from src.middlewares.rbac import require_permission
from src.models.user import User

router = APIRouter(prefix="/pii", tags=["pii"])


@router.get("/findings")
def list_findings(
    table_id: str | None = Query(default=None),
    user: User = Depends(require_permission("pii:read")),
    db: Session = Depends(get_db),
) -> dict:
    return pii_controller.list_findings(db, table_id)


@router.get("/columns/{column_id}")
def column_evidence(
    column_id: str,
    user: User = Depends(require_permission("pii:read")),
    db: Session = Depends(get_db),
) -> dict:
    return pii_controller.column_evidence(db, column_id)
