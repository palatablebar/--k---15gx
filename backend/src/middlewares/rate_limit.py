"""Redis 滑动窗口限流（按用户 + 路由）。Redis 不可用时 fail-open，只记日志。"""
from __future__ import annotations

import time

from fastapi import Depends, Request

from src.constants import error_codes as codes
from src.constants.limits import RATE_LIMIT_DEFAULT_PER_MINUTE, RATE_LIMIT_EXPORT_PER_MINUTE
from src.config.settings import settings
from src.middlewares.auth import get_current_user
from src.models.user import User
from src.utils.errors import AppError
from src.utils.logger import get_logger
from src.utils.redis_client import get_redis

logger = get_logger("maskguard.ratelimit")


def _check(key: str, limit: int, window_seconds: int = 60) -> None:
    try:
        now = time.time()
        client = get_redis()
        pipeline = client.pipeline()
        pipeline.zremrangebyscore(key, 0, now - window_seconds)
        pipeline.zadd(key, {f"{now}": now})
        pipeline.zcard(key)
        pipeline.expire(key, window_seconds)
        results = pipeline.execute()
        count = int(results[2])
    except Exception as exc:  # noqa: BLE001 - 限流不能把业务打死
        logger.warning("rate limit skipped: %s", exc)
        return
    if count > limit:
        raise AppError(
            codes.RATE_LIMITED,
            "请求过于频繁，请稍后重试",
            f"key={key} count={count} limit={limit}",
            extra={"retry_after": window_seconds},
        )


def rate_limit(bucket: str = "default") -> object:
    def dependency(request: Request, user: User = Depends(get_current_user)) -> None:
        if bucket == "export":
            limit = RATE_LIMIT_EXPORT_PER_MINUTE
        else:
            limit = int(settings.rate_limit_per_minute or RATE_LIMIT_DEFAULT_PER_MINUTE)
        _check(f"ratelimit:{bucket}:{user.id}:{request.url.path}", limit)

    return Depends(dependency)
