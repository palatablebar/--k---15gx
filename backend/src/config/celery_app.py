"""backend 侧 Celery 客户端：只负责投递任务，不消费。"""
from __future__ import annotations

from celery import Celery

from src.config.settings import settings

celery_client = Celery(
    "maskguard_client",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_client.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
    broker_connection_retry_on_startup=True,
)


def dispatch(task_name: str, **kwargs) -> str | None:
    """投递任务；broker 不可用时返回 None，由调用方同步兜底。"""
    try:
        result = celery_client.send_task(task_name, kwargs=kwargs)
        return result.id
    except Exception:  # noqa: BLE001 - broker 抖动不能把请求打死
        return None
