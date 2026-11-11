from fastapi import APIRouter

from src.routes import (
    audit,
    auth,
    dataset,
    export,
    health,
    k_anonymity,
    meta,
    policy,
    pii,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(meta.router)
api_router.include_router(dataset.router)
api_router.include_router(pii.router)
api_router.include_router(policy.router)
api_router.include_router(k_anonymity.router)
api_router.include_router(export.router)
api_router.include_router(audit.router)

__all__ = ["api_router"]
