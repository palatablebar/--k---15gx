"""心跳任务：写 Redis 键，供 worker 容器 healthcheck 判断存活。"""
from __future__ import annotations

import time

from worker_src.config.celery_app import celery_app


@celery_app.task(name="maskguard.heartbeat")
def heartbeat() -> dict:
    from src.utils.redis_client import get_redis

    try:
        get_redis().set("maskguard:worker:heartbeat", time.time(), ex=180)
        return {"status": "ok", "ts": time.time()}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "detail": str(exc)}
