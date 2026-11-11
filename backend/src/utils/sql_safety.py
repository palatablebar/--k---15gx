"""原始表名/列名白名单校验：这些名字来自数据库元数据，仍然不信任何外部输入。"""
from __future__ import annotations

import re

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")


def safe_identifier(name: str) -> str:
    if not isinstance(name, str) or not _IDENT.match(name):
        raise ValueError(f"unsafe identifier: {name!r}")
    return name


def qualified_table(schema: str, table: str) -> str:
    return f"{safe_identifier(schema)}.{safe_identifier(table)}"
