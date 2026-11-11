"""ASGI 审计上下文中间件：trace_id、访问日志、耗时。

业务成功后由 service 显式写 audit_logs（那里才拿得到 entity_id），
中间件只负责请求级上下文与访问日志。
"""
from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.utils.logger import get_logger

logger = get_logger("maskguard.access")


class AuditContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("x-trace-id") or uuid.uuid4().hex[:16]
        request.state.trace_id = trace_id
        request.state.client_ip = (
            request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or (request.client.host if request.client else "")
        )
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        response.headers["x-trace-id"] = trace_id
        if request.url.path not in ("/health", "/api/health"):
            logger.info(
                "%s %s -> %s %sms trace=%s",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
                trace_id,
            )
        return response
