from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import ROLE_ADMIN, ROLE_DPO
from src.controllers import auth_controller
from src.middlewares.auth import get_current_user
from src.middlewares.rbac import require_role
from src.models.user import User
from src.schemas.auth import LoginRequest, RefreshRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    return auth_controller.login(request, payload, db)


@router.post("/refresh")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> dict:
    return auth_controller.refresh(payload, db)


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return auth_controller.me(user)


@router.get("/users")
def list_users(
    user: User = Depends(require_role(ROLE_ADMIN, ROLE_DPO)), db: Session = Depends(get_db)
) -> dict:
    return auth_controller.list_users(db)
