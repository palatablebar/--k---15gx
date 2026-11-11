"""sha256 工具：导出文件摘要、脱敏哈希、种子数据校验。"""
from __future__ import annotations

import hashlib


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def salted_hash(value: str, salt: str, length: int = 16) -> str:
    """哈希掩码：sha256(salt + value)，取前 length 个 hex 字符。"""
    return hashlib.sha256(f"{salt}:{value}".encode("utf-8")).hexdigest()[:length]
