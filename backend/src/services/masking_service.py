"""算法 1 的下半段：4 种掩码方法与策略预览。

mask       保留前后 N 位，中间替换为掩码字符
hash       sha256(salt + value) 取前 N 个 hex，可加前缀，保持可连接但不可逆
generalize 按泛化层级降精度（年龄→区间、邮编→前缀、日期→年、地址→行政区前缀）
suppress   整值替换为占位符（信息损失最大，不可还原）
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from src.config.settings import settings
from src.constants.enums import GeneralizeKind, MaskMethod
from src.constants.limits import PREVIEW_MAX_ROWS, PREVIEW_SAMPLES
from src.models.dataset_column import DatasetColumn
from src.models.masking_policy import MaskingPolicy
from src.services import raw_data_service
from src.utils.checksum import salted_hash


def _as_date(value: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _age(value: str) -> int | None:
    born = _as_date(value)
    if born is None:
        return None
    reference = date.fromisoformat(settings.age_reference_date)
    return (reference - born).days // 365


def apply_method(method: str, value: str, params: dict[str, Any]) -> str:
    """对单个值应用掩码方法；空值原样返回（NULL 不生成假值）。"""
    if value is None or value == "":
        return value

    if method == MaskMethod.MASK.value:
        keep_prefix = int(params.get("keep_prefix", 0))
        keep_suffix = int(params.get("keep_suffix", 0))
        mask_char = str(params.get("mask_char", "*"))
        length = len(value)
        if keep_prefix + keep_suffix >= length:
            return value
        middle = mask_char * (length - keep_prefix - keep_suffix)
        return f"{value[:keep_prefix]}{middle}{value[length - keep_suffix:]}"

    if method == MaskMethod.HASH.value:
        digest_len = int(params.get("digest_len", 16))
        prefix = str(params.get("prefix", ""))
        return f"{prefix}{salted_hash(value, settings.hash_salt, digest_len)}"

    if method == MaskMethod.SUPPRESS.value:
        return str(params.get("replacement", "[已抑制]"))

    if method == MaskMethod.GENERALIZE.value:
        kind = params.get("kind", GeneralizeKind.AGE_BAND.value)
        if kind == GeneralizeKind.AGE_BAND.value:
            width = int(params.get("width", 5))
            age = _age(value)
            if age is None:
                try:
                    age = int(value)
                except (TypeError, ValueError):
                    return value
            low = (age // width) * width
            return f"{low}-{low + width - 1}岁"
        if kind == GeneralizeKind.DATE_YEAR.value:
            parsed = _as_date(value)
            return str(parsed.year) if parsed else value
        if kind == GeneralizeKind.ZIP_PREFIX.value:
            keep = int(params.get("keep", 3))
            digits = "".join(ch for ch in value if ch.isdigit())
            if len(digits) < keep:
                return value
            return digits[:keep] + "*" * (len(digits) - keep)
        if kind == GeneralizeKind.KEEP_PREFIX.value:
            keep = int(params.get("keep", 6))
            if len(value) <= keep:
                return value
            return value[:keep] + "…"
        return value

    return value


def mask_value_with_policy(column_name: str, value: str, policy: MaskingPolicy | None) -> str:
    if policy is None:
        return value
    return apply_method(policy.method, value, dict(policy.params_json or {}))


def describe(method: str, params: dict[str, Any]) -> str:
    if method == MaskMethod.MASK.value:
        return f"保留前 {params.get('keep_prefix', 0)} 位 / 后 {params.get('keep_suffix', 0)} 位"
    if method == MaskMethod.HASH.value:
        return f"sha256 + 盐，截取 {params.get('digest_len', 16)} 位，可连接不可逆"
    if method == MaskMethod.SUPPRESS.value:
        return f"整值替换为 {params.get('replacement', '[已抑制]')}"
    kind = params.get("kind", GeneralizeKind.AGE_BAND.value)
    if kind == GeneralizeKind.AGE_BAND.value:
        return f"年龄按 {params.get('width', 5)} 岁区间泛化"
    if kind == GeneralizeKind.DATE_YEAR.value:
        return "日期精度降到年"
    if kind == GeneralizeKind.ZIP_PREFIX.value:
        return f"邮编保留前 {params.get('keep', 3)} 位"
    if kind == GeneralizeKind.KEEP_PREFIX.value:
        return f"文本保留前 {params.get('keep', 6)} 个字符"
    return method


def preview(db: Session, policy: MaskingPolicy, columns: list[DatasetColumn], table_name: str) -> dict[str, Any]:
    """策略预览：真实读取原始列 → 逐值应用 → 返回前后对比与统计。"""
    applied_columns: list[dict[str, Any]] = []
    warnings: list[str] = []
    total_values = 0
    for column in columns:
        values = raw_data_service.column_values(db, table_name, column.name, PREVIEW_MAX_ROWS)
        total_values += len(values)
        masked = [apply_method(policy.method, value, dict(policy.params_json or {})) for value in values]
        changed = sum(1 for before, after in zip(values, masked) if before != after)
        sample_pairs = [
            {"before": before, "after": after, "removable_span": _removable_span(before, after)}
            for before, after in zip(values, masked)
            if before.strip() != ""
        ][:PREVIEW_SAMPLES]
        applied_columns.append(
            {
                "column_id": str(column.id),
                "column_name": column.name,
                "data_type": column.data_type,
                "pii_type": column.pii_type,
                "method": policy.method,
                "total_rows": len(values),
                "changed_rows": changed,
                "distinct_before": len(set(values)),
                "distinct_after": len(set(masked)),
                "samples": sample_pairs,
            }
        )
        if changed == 0:
            warnings.append(f"列 {column.name} 应用后无变化，请检查参数是否匹配该列数据形态")
    return {
        "policy_id": str(policy.id),
        "policy_name": policy.name,
        "method": policy.method,
        "params": dict(policy.params_json or {}),
        "total_rows": total_values,
        "applied_columns": applied_columns,
        "warnings": warnings,
    }


def _removable_span(before: str, after: str) -> list[int]:
    """标出被涂改的字符区间（用于前端红线删除线渲染）。"""
    if before == after:
        return []
    prefix = 0
    while prefix < min(len(before), len(after)) and before[prefix] == after[prefix]:
        prefix += 1
    suffix = 0
    while (
        suffix < min(len(before), len(after)) - prefix
        and before[len(before) - 1 - suffix] == after[len(after) - 1 - suffix]
    ):
        suffix += 1
    return [prefix, len(before) - suffix]
