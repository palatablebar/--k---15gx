from fastapi import APIRouter

from src.controllers import meta_controller

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/enums")
def enums() -> dict:
    return meta_controller.enums()
