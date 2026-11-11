from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import policy_controller
from src.middlewares.rate_limit import rate_limit
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.policy import PolicyCreateRequest, PolicyUpdateRequest

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("")
def list_policies(
    user: User = Depends(require_permission("policies:read")), db: Session = Depends(get_db)
) -> dict:
    return policy_controller.list_policies(db)


@router.get("/{policy_id}")
def detail(
    policy_id: str,
    user: User = Depends(require_permission("policies:read")),
    db: Session = Depends(get_db),
) -> dict:
    return policy_controller.detail(db, policy_id)


@router.post("")
def create(
    payload: PolicyCreateRequest,
    request: Request,
    user: User = Depends(require_permission("policies:write")),
    db: Session = Depends(get_db),
    _: None = rate_limit("policy"),
) -> dict:
    return policy_controller.create(db, payload, user, request)


@router.patch("/{policy_id}")
def update(
    policy_id: str,
    payload: PolicyUpdateRequest,
    request: Request,
    user: User = Depends(require_permission("policies:write")),
    db: Session = Depends(get_db),
) -> dict:
    return policy_controller.update(db, policy_id, payload, user, request)


@router.post("/{policy_id}/preview")
def preview(
    policy_id: str,
    request: Request,
    user: User = Depends(require_permission("policies:preview")),
    db: Session = Depends(get_db),
    _: None = rate_limit("preview"),
) -> dict:
    return policy_controller.preview(db, policy_id, user, request)
