"""日志序列化：把常量模板 + 上下文拼成一行结构化文本。"""
from __future__ import annotations

import json
import logging
import sys
from typing import Any

from src.constants.log_templates import LOG_TEMPLATES

_LOGGERS: dict[str, logging.Logger] = {}


def get_logger(name: str) -> logging.Logger:
    if name in _LOGGERS:
        return _LOGGERS[name]
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    _LOGGERS[name] = logger
    return logger


def render(template_key: str, **kwargs: Any) -> str:
    template = LOG_TEMPLATES.get(template_key)
    if template is None:
        return json.dumps({"template": template_key, **kwargs}, ensure_ascii=False, default=str)
    safe = {k: ("" if v is None else v) for k, v in kwargs.items()}
    try:
        return template.format(**safe)
    except (KeyError, IndexError):
        return f"{template_key} " + json.dumps(safe, ensure_ascii=False, default=str)


def log_info(logger: logging.Logger, template_key: str, **kwargs: Any) -> None:
    logger.info(render(template_key, **kwargs))


def log_warning(logger: logging.Logger, template_key: str, **kwargs: Any) -> None:
    logger.warning(render(template_key, **kwargs))


def log_error(logger: logging.Logger, template_key: str, **kwargs: Any) -> None:
    logger.error(render(template_key, **kwargs))
