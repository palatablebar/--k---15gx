"""掩码策略：参数校验、适用范围解析、冲突检测、预览编排。"""
from __future__ import annotations

import fnmatch
from typing import Any

from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.enums import GeneralizeKind, MaskMethod
from src.models.dataset_column import DatasetColumn
from src.models.dataset_table import DatasetTable
from src.models.masking_policy import MaskingPolicy
from src.models.user import User
from src.services import masking_service
from src.utils.errors import AppError, not_found
from src.utils.logger import get_logger, log_info

logger = get_logger("maskguard.policy")

VALID_METHODS = {method.value for method in MaskMethod}
VALID_KINDS = {kind.value for kind in GeneralizeKind}


def validate_params(method: str, params: dict[str, Any]) -> dict[str, Any]:
    """把用户参数收敛成规范形式；不合法直接 422。"""
    if method not in VALID_METHODS:
        raise AppError(codes.VALIDATION_ERROR, "掩码方法不合法", f"method={method}")
    clean: dict[str, Any] = {}
    if method == MaskMethod.MASK.value:
        keep_prefix = int(params.get("keep_prefix", 4))
        keep_suffix = int(params.get("keep_suffix", 4))
        if not (0 <= keep_prefix <= 20 and 0 <= keep_suffix <= 20):
            raise AppError(codes.VALIDATION_ERROR, "保留位数需在 0-20 之间", str(params))
        if keep_prefix + keep_suffix == 0:
            raise AppError(codes.VALIDATION_ERROR, "至少保留 1 位原始字符", str(params))
        clean = {
            "keep_prefix": keep_prefix,
            "keep_suffix": keep_suffix,
            "mask_char": str(params.get("mask_char", "*"))[:1] or "*",
        }
    elif method == MaskMethod.HASH.value:
        digest_len = int(params.get("digest_len", 16))
        if not 4 <= digest_len <= 64:
            raise AppError(codes.VALIDATION_ERROR, "哈希截取长度需在 4-64 之间", str(params))
        clean = {"digest_len": digest_len, "prefix": str(params.get("prefix", ""))[:8]}
    elif method == MaskMethod.SUPPRESS.value:
        clean = {"replacement": str(params.get("replacement", "[已抑制]"))[:32] or "[已抑制]"}
    else:  # generalize
        kind = str(params.get("kind", GeneralizeKind.AGE_BAND.value))
        if kind not in VALID_KINDS:
            raise AppError(codes.VALIDATION_ERROR, "泛化类型不合法", f"kind={kind}")
        clean = {"kind": kind}
        if kind == GeneralizeKind.AGE_BAND.value:
            width = int(params.get("width", 5))
            if width not in (1, 5, 10):
                raise AppError(codes.VALIDATION_ERROR, "年龄区间宽度只支持 1/5/10", str(params))
            clean["width"] = width
        elif kind == GeneralizeKind.ZIP_PREFIX.value:
            keep = int(params.get("keep", 3))
            if not 1 <= keep <= 5:
                raise AppError(codes.VALIDATION_ERROR, "邮编保留位数需在 1-5 之间", str(params))
            clean["keep"] = keep
        elif kind == GeneralizeKind.KEEP_PREFIX.value:
            keep = int(params.get("keep", 6))
            if not 1 <= keep <= 20:
                raise AppError(codes.VALIDATION_ERROR, "保留前缀长度需在 1-20 之间", str(params))
            clean["keep"] = keep
    return clean


def resolve_target_columns(db: Session, policy: MaskingPolicy) -> list[tuple[DatasetColumn, DatasetTable]]:
    """按 表 + 列通配 + PII 类型 解析策略命中的列。"""
    query = db.query(DatasetColumn, DatasetTable).join(
        DatasetTable, DatasetTable.id == DatasetColumn.table_id
    )
    if policy.table_id is not None:
        query = query.filter(DatasetColumn.table_id == policy.table_id)
    if policy.pii_type:
        query = query.filter(DatasetColumn.pii_type == policy.pii_type)
    pairs = query.order_by(DatasetTable.table_name, DatasetColumn.ordinal).all()
    matches = [
        (column, table)
        for column, table in pairs
        if fnmatch.fnmatch(column.name, policy.column_pattern or "*")
    ]
    return matches


def serialize(policy: MaskingPolicy, table_name: str | None) -> dict[str, Any]:
    from src.schemas.common import iso

    return {
        "id": str(policy.id),
        "name": policy.name,
        "table_id": str(policy.table_id) if policy.table_id else None,
        "table_name": table_name,
        "column_pattern": policy.column_pattern,
        "pii_type": policy.pii_type,
        "method": policy.method,
        "params": dict(policy.params_json or {}),
        "description": policy.description,
        "is_active": policy.is_active,
        "created_by": str(policy.created_by) if policy.created_by else None,
        "created_at": iso(policy.created_at),
        "updated_at": iso(policy.updated_at),
    }


def list_policies(db: Session) -> list[dict[str, Any]]:
    rows = (
        db.query(MaskingPolicy, DatasetTable)
        .outerjoin(DatasetTable, DatasetTable.id == MaskingPolicy.table_id)
        .order_by(MaskingPolicy.created_at)
        .all()
    )
    return [serialize(policy, table.table_name if table else None) for policy, table in rows]


def get_policy(db: Session, policy_id: str) -> MaskingPolicy:
    policy = db.get(MaskingPolicy, policy_id)
    if policy is None:
        raise not_found("掩码策略", policy_id)
    return policy


def _table_name_of(db: Session, policy: MaskingPolicy) -> str | None:
    if policy.table_id is None:
        return None
    table = db.get(DatasetTable, policy.table_id)
    return table.table_name if table else None


def create_policy(db: Session, user: User, payload: Any) -> dict[str, Any]:
    if db.query(MaskingPolicy).filter(MaskingPolicy.name == payload.name).count():
        raise AppError(codes.POLICY_CONFLICT, "策略名称已存在", payload.name)
    table_name: str | None = None
    if payload.table_id:
        table = db.get(DatasetTable, payload.table_id)
        if table is None:
            raise not_found("数据集表", payload.table_id)
        table_name = table.table_name
    conflict = (
        db.query(MaskingPolicy)
        .filter(
            MaskingPolicy.is_active.is_(True),
            MaskingPolicy.table_id == (payload.table_id or None),
            MaskingPolicy.column_pattern == payload.column_pattern,
        )
        .count()
    )
    if conflict:
        raise AppError(codes.POLICY_CONFLICT, "同一列范围已有生效策略，请先停用旧策略", payload.column_pattern)
    policy = MaskingPolicy(
        name=payload.name,
        table_id=payload.table_id,
        column_pattern=payload.column_pattern,
        pii_type=payload.pii_type,
        method=payload.method,
        params_json=validate_params(payload.method, payload.params or {}),
        description=payload.description,
        is_active=payload.is_active,
        created_by=user.id,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return serialize(policy, table_name)


def update_policy(db: Session, policy_id: str, payload: Any) -> dict[str, Any]:
    policy = get_policy(db, policy_id)
    if payload.name is not None:
        duplicated = (
            db.query(MaskingPolicy)
            .filter(MaskingPolicy.name == payload.name, MaskingPolicy.id != policy.id)
            .count()
        )
        if duplicated:
            raise AppError(codes.POLICY_CONFLICT, "策略名称已存在", payload.name)
        policy.name = payload.name
    if payload.method is not None:
        policy.method = payload.method
        policy.params_json = validate_params(payload.method, payload.params or policy.params_json or {})
    elif payload.params is not None:
        policy.params_json = validate_params(policy.method, payload.params)
    if payload.description is not None:
        policy.description = payload.description
    if payload.is_active is not None:
        policy.is_active = payload.is_active
    db.commit()
    db.refresh(policy)
    return serialize(policy, _table_name_of(db, policy))


def preview_policy(db: Session, policy_id: str) -> dict[str, Any]:
    policy = get_policy(db, policy_id)
    if not policy.is_active:
        raise AppError(codes.POLICY_INACTIVE, None, f"policy_id={policy_id}")
    pairs = resolve_target_columns(db, policy)
    if not pairs:
        raise AppError(codes.POLICY_NO_TARGET, None, f"policy_id={policy_id}")
    by_table: dict[str, list[DatasetColumn]] = {}
    for column, table in pairs:
        by_table.setdefault(table.table_name, []).append(column)
    applied: list[dict[str, Any]] = []
    warnings: list[str] = []
    total_values = 0
    for table_name, columns in by_table.items():
        result = masking_service.preview(db, policy, columns, table_name)
        applied.extend(result["applied_columns"])
        warnings.extend(result["warnings"])
        total_values += result["total_rows"]
    log_info(
        logger,
        "policy.preview",
        policy=policy.name,
        columns=len(applied),
        rows=total_values,
    )
    return {
        "policy_id": str(policy.id),
        "policy_name": policy.name,
        "method": policy.method,
        "params": dict(policy.params_json or {}),
        "total_rows": total_values,
        "applied_columns": applied,
        "warnings": warnings,
    }


def policy_for_column(db: Session, column: DatasetColumn) -> MaskingPolicy | None:
    """导出时给每列挑策略：表级优先，其次 PII 类型级，再次通配。"""
    candidates = (
        db.query(MaskingPolicy)
        .filter(MaskingPolicy.is_active.is_(True))
        .all()
    )
    matched: list[MaskingPolicy] = []
    for policy in candidates:
        if policy.table_id is not None and policy.table_id != column.table_id:
            continue
        if policy.pii_type and column.pii_type and policy.pii_type != column.pii_type:
            continue
        if policy.pii_type and not column.pii_type:
            continue
        if not fnmatch.fnmatch(column.name, policy.column_pattern or "*"):
            continue
        matched.append(policy)
    if not matched:
        return None
    matched.sort(key=lambda item: (item.table_id is not None, item.pii_type is not None), reverse=True)
    return matched[0]
