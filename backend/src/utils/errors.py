"""统一业务异常。service 抛 AppError，controller 再包一层实体与字段信息。"""
from __future__ import annotations

from typing import Any

from src.constants import error_codes as codes


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str | None = None,
        detail: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message or codes.ERROR_MESSAGES.get(code, code)
        self.detail = detail or ""
        self.extra = extra or {}
        super().__init__(self.message)

    @property
    def http_status(self) -> int:
        return codes.HTTP_STATUS.get(self.code, 500)

    def to_payload(self, trace_id: str | None = None) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "detail": self.detail,
            "trace_id": trace_id,
            **({"extra": self.extra} if self.extra else {}),
        }


def not_found(entity: str, entity_id: object) -> AppError:
    return AppError(codes.NOT_FOUND, f"{entity} 不存在", f"{entity}[id={entity_id}] not found")


def wrap(code: str, entity: str, entity_id: object, detail: str) -> AppError:
    return AppError(code, None, f"{entity}[id={entity_id}] {detail}")
