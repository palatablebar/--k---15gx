"""FastAPI 应用装配：中间件、异常收敛、路由挂载、启动钩子。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import settings
from src.middlewares.audit_logger import AuditContextMiddleware
from src.middlewares.error_handler import register_exception_handlers
from src.routes import api_router

logger = logging.getLogger("maskguard.app")


def _run_seed_once() -> None:
    """SEED_DEMO=true 时启动阶段执行一次幂等 seed；失败只记 WARNING，不阻塞健康检查。"""
    if not settings.seed_demo:
        return
    try:
        from scripts.seed_demo import seed_all

        result = seed_all()
        logger.warning("[SEED_DEMO] seed finished %s", result)
    except Exception as exc:  # noqa: BLE001 - 启动阶段绝不允许阻塞
        logger.warning("[SEED_DEMO] seed failed (ignored): %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _run_seed_once()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="maskguard · 数据脱敏与 k-匿名合规工作台",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AuditContextMiddleware)

    register_exception_handlers(app)

    # 同一份路由挂两次：/api/* 给直连与健康检查；根路径给 Nginx 剥前缀后的反代
    app.include_router(api_router, prefix="/api")
    app.include_router(api_router, include_in_schema=False)
    return app
