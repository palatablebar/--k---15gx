from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import dataset_controller
from src.middlewares.auth import get_current_user
from src.middlewares.rate_limit import rate_limit
from src.middlewares.rbac import require_permission
from src.models.user import User

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("")
def list_tables(
    user: User = Depends(require_permission("datasets:read")), db: Session = Depends(get_db)
) -> dict:
    return dataset_controller.list_tables(db)


@router.get("/{table_id}")
def table_detail(
    table_id: str,
    user: User = Depends(require_permission("datasets:read")),
    db: Session = Depends(get_db),
) -> dict:
    return dataset_controller.table_detail(db, table_id)


@router.get("/{table_id}/columns")
def list_columns(
    table_id: str,
    user: User = Depends(require_permission("datasets:read")),
    db: Session = Depends(get_db),
) -> dict:
    return dataset_controller.list_columns(db, table_id)


@router.post("/{table_id}/scan")
def scan(
    table_id: str,
    request: Request,
    user: User = Depends(require_permission("datasets:scan")),
    db: Session = Depends(get_db),
    _: None = rate_limit("scan"),
) -> dict:
    return dataset_controller.scan(db, table_id, user, request)
