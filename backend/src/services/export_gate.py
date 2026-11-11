"""导出合规门禁：批准前必须基于「当前导出范围 × 现行策略 × 最新校验 × 当前数据」得出达标结论。

评估口径
--------
1. 直接标识覆盖：导出范围内的直接标识列 / PII 列必须各有一条生效的脱敏策略。
2. k-匿名达标：导出范围含 ≥2 个准标识列且含敏感属性列时，必须存在已完成的最新校验，
   且结论达标（k≥目标、ℓ≥目标）。
3. 范围一致：导出范围的准标识列必须被最新校验的 QI 组合覆盖（校验是超集即可，等价类
   只会更细，k/ℓ 单调安全）。
4. 层级一致：现行策略对每个 QI 列的泛化强度不得低于校验推荐层级，否则「达标」只对
   推荐口径成立、对实际导出文件不成立。
5. 结论时效：校验完成之后策略有新增/修改/停用，或上游数据有变化（数据签名不一致），
   旧结论一律失效，必须重新校验。

指纹
----
指纹 = sha256(范围列 + 每列生效策略(含参数与更新时间) + 最新校验(含数据签名) + 当前数据签名)。
任何规则或数据变化都会改变指纹：台账里旧结论据此标记「已失效」，批准时永远按现行环境重评。
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from src.constants.enums import ColumnRole, GateStatus, MaskMethod, PIIType
from src.models.dataset_column import DatasetColumn
from src.models.dataset_table import DatasetTable
from src.models.export_request import ExportRequest
from src.models.k_anonymity_check import KAnonymityCheck
from src.models.masking_policy import MaskingPolicy
from src.schemas.common import iso
from src.services import k_anonymity_service, policy_service

# 缺口代码（随 gate_gaps_json 落库，前端按 code 也可自行归类展示）
POLICY_MISSING_DIRECT_ID = "POLICY_MISSING_DIRECT_ID"
KANON_MISSING = "KANON_MISSING"
KANON_CHECK_FAILED = "KANON_CHECK_FAILED"
KANON_NOT_PASSED = "KANON_NOT_PASSED"
KANON_QI_UNCOVERED = "KANON_QI_UNCOVERED"
KANON_LEVEL_GAP = "KANON_LEVEL_GAP"
KANON_SIGNATURE_MISSING = "KANON_SIGNATURE_MISSING"
POLICY_CHANGED_AFTER_CHECK = "POLICY_CHANGED_AFTER_CHECK"
DATA_CHANGED_AFTER_CHECK = "DATA_CHANGED_AFTER_CHECK"

PII_LABELS = {
    PIIType.MOBILE.value: "手机号",
    PIIType.ID_CARD.value: "身份证号",
    PIIType.EMAIL.value: "邮箱",
    PIIType.NAME.value: "姓名",
    PIIType.ADDRESS.value: "地址",
}

# 强于一切泛化层级的方法（直接销毁准标识可链接性）
_STRONG_METHODS = {MaskMethod.SUPPRESS.value, MaskMethod.HASH.value}


def _gap(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **extra}


def _scope_columns(db: Session, table: DatasetTable) -> list[DatasetColumn]:
    return (
        db.query(DatasetColumn)
        .filter(DatasetColumn.table_id == table.id)
        .order_by(DatasetColumn.ordinal)
        .all()
    )


def _effective_policies(
    db: Session, columns: list[DatasetColumn]
) -> dict[str, MaskingPolicy | None]:
    """与导出文件生成完全相同的策略选取口径（policy_for_column）。"""
    return {column.name: policy_service.policy_for_column(db, column) for column in columns}


def _latest_check(db: Session, table: DatasetTable) -> KAnonymityCheck | None:
    return (
        db.query(KAnonymityCheck)
        .filter(KAnonymityCheck.table_id == table.id)
        .order_by(KAnonymityCheck.created_at.desc())
        .first()
    )


def _check_columns(check: KAnonymityCheck) -> list[str]:
    """校验执行时参与计算与签名的列集合（顺序与 execute_check 保持一致）。"""
    qi = [str(item) for item in (check.quasi_identifiers_json or [])]
    return list(dict.fromkeys(qi + [check.sensitive_column]))


def _provided_level(policy: MaskingPolicy | None, column_name: str) -> int:
    """现行策略对该 QI 列实际提供的泛化层级（1-based，对应 levels_for 的层级表）。

    无策略 / 仅掩码 → 1（近似原始精度）；抑制 / 哈希 → 足够强，记为最高层级之上。
    """
    if policy is None:
        return 1
    if policy.method in _STRONG_METHODS:
        return 99
    if policy.method != MaskMethod.GENERALIZE.value:
        return 1
    params = dict(policy.params_json or {})
    kind = str(params.get("kind", ""))
    specs = k_anonymity_service.levels_for(column_name)
    if kind == "age_band":
        width = int(params.get("width", 1))
        for index, spec in enumerate(specs):
            if spec.get("kind") == "age_band" and int(spec.get("width", 0)) == width:
                return index + 1
        return 1  # width=1 等同精确年龄
    if kind == "zip_prefix":
        keep = int(params.get("keep", 5))
        for index, spec in enumerate(specs):
            if spec.get("kind") == "zip_prefix" and int(spec.get("keep", 0)) == keep:
                return index + 1
        if keep <= 2:
            return len(specs)  # 比层级表最粗一档还粗
        return 1  # keep=4/5 接近完整邮编
    return 1  # date_year / keep_prefix 等不在 QI 层级表内，保守按原始精度


def _level_label(column_name: str, level: int) -> str:
    specs = k_anonymity_service.levels_for(column_name)
    if 1 <= level <= len(specs):
        return str(specs[level - 1].get("label", "原始取值"))
    return "原始取值"


def _changed_policies(db: Session, table: DatasetTable, check: KAnonymityCheck) -> list[str]:
    """校验完成之后变更过（含新增与停用）且可能影响本表的策略名。"""
    if check.finished_at is None:
        return []
    rows = (
        db.query(MaskingPolicy)
        .filter(
            MaskingPolicy.updated_at > check.finished_at,
            (MaskingPolicy.table_id == table.id) | (MaskingPolicy.table_id.is_(None)),
        )
        .order_by(MaskingPolicy.updated_at)
        .all()
    )
    return [policy.name for policy in rows]


def _fingerprint(payload: dict[str, Any]) -> str:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _environment(db: Session, table: DatasetTable) -> dict[str, Any]:
    """门禁依赖的现行环境：范围列、每列生效策略、最新校验、当前数据签名。"""
    columns = _scope_columns(db, table)
    policies = _effective_policies(db, columns)
    check = _latest_check(db, table)
    if check is not None:
        signature_columns = _check_columns(check)
    else:
        signature_columns = [
            column.name
            for column in columns
            if column.column_role in (ColumnRole.QUASI_ID.value, ColumnRole.SENSITIVE.value)
        ]
    data_signature = (
        k_anonymity_service.fetch_signature(db, table.table_name, signature_columns)
        if signature_columns
        else ""
    )
    return {
        "columns": columns,
        "policies": policies,
        "check": check,
        "data_signature": data_signature,
    }


def current_fingerprint(db: Session, table: DatasetTable, env: dict[str, Any] | None = None) -> str:
    """现行环境指纹：与 evaluate 落库的指纹同算法，用于判定旧结论是否失效。"""
    env = env or _environment(db, table)
    check = env["check"]
    return _fingerprint(
        {
            "table": str(table.id),
            "columns": [column.name for column in env["columns"]],
            "policies": {
                name: (
                    {
                        "id": str(policy.id),
                        "method": policy.method,
                        "params": dict(policy.params_json or {}),
                        "updated_at": iso(policy.updated_at),
                    }
                    if policy is not None
                    else None
                )
                for name, policy in env["policies"].items()
            },
            "check": (
                {
                    "id": str(check.id),
                    "status": check.status,
                    "passed": check.passed,
                    "final_k": check.final_k,
                    "final_l": check.final_l,
                    "finished_at": iso(check.finished_at),
                    "data_signature": check.data_signature,
                }
                if check is not None
                else None
            ),
            "data_signature": env["data_signature"],
        }
    )


def evaluate(db: Session, export: ExportRequest) -> dict[str, Any]:
    """对一条导出申请按现行环境评估门禁，返回 {passed, gaps, fingerprint, snapshot}。"""
    table = db.get(DatasetTable, export.table_id)
    if table is None:
        return {
            "passed": False,
            "gaps": [_gap("TABLE_MISSING", "导出申请关联的数据集表已不存在")],
            "fingerprint": "",
            "snapshot": {"evaluated_at": iso(_now()), "table": ""},
        }

    env = _environment(db, table)
    columns: list[DatasetColumn] = env["columns"]
    policies: dict[str, MaskingPolicy | None] = env["policies"]
    check: KAnonymityCheck | None = env["check"]
    gaps: list[dict[str, Any]] = []

    # 1. 直接标识 / PII 列必须全部配有生效策略
    uncovered: list[str] = []
    for column in columns:
        if column.column_role == ColumnRole.DIRECT_ID.value or column.pii_type:
            if policies.get(column.name) is None:
                label = PII_LABELS.get(column.pii_type or "", "直接标识符")
                gaps.append(
                    _gap(
                        POLICY_MISSING_DIRECT_ID,
                        f"直接标识列 {column.name}（{label}）未配置生效的脱敏策略",
                        column=column.name,
                    )
                )
                uncovered.append(column.name)

    # 2. k-匿名：范围含 ≥2 准标识且有敏感属性列时强制
    qi_columns = [column.name for column in columns if column.column_role == ColumnRole.QUASI_ID.value]
    sensitive_columns = [
        column.name for column in columns if column.column_role == ColumnRole.SENSITIVE.value
    ]
    kanon_required = len(qi_columns) >= 2 and len(sensitive_columns) >= 1

    if kanon_required:
        if check is None:
            gaps.append(
                _gap(
                    KANON_MISSING,
                    f"导出范围含准标识列（{'、'.join(qi_columns)}）与敏感属性列"
                    f"（{'、'.join(sensitive_columns)}），但从未做过 k-匿名校验",
                )
            )
        else:
            if check.status != "succeeded":
                gaps.append(
                    _gap(
                        KANON_CHECK_FAILED,
                        f"最新一次 k-匿名校验未成功完成（状态：{check.status}），请重新执行校验",
                        check_id=str(check.id),
                    )
                )
            elif check.passed is not True:
                gaps.append(
                    _gap(
                        KANON_NOT_PASSED,
                        f"最新一次 k-匿名校验不达标：最优仅 k={check.final_k}、ℓ={check.final_l}，"
                        f"低于目标 k≥{check.target_k}、ℓ≥{check.target_l}",
                        check_id=str(check.id),
                    )
                )
            else:
                # 3. 范围一致：导出范围的准标识列必须被校验 QI 覆盖
                checked_qi = {str(item) for item in (check.quasi_identifiers_json or [])}
                missing_qi = [name for name in qi_columns if name not in checked_qi]
                if missing_qi:
                    gaps.append(
                        _gap(
                            KANON_QI_UNCOVERED,
                            f"准标识列 {'、'.join(missing_qi)} 未被最新校验的准标识组合覆盖，"
                            "请按当前导出范围重新校验",
                            columns=missing_qi,
                        )
                    )
                # 4. 层级一致：现行策略泛化强度不得低于校验推荐层级
                recommended = dict(check.recommended_level_json or {})
                required_levels = {str(k): int(v) for k, v in dict(recommended.get("levels") or {}).items()}
                for name, required in sorted(required_levels.items()):
                    if required <= 1:
                        continue
                    provided = _provided_level(policies.get(name), name)
                    if provided < required:
                        gaps.append(
                            _gap(
                                KANON_LEVEL_GAP,
                                f"准标识列 {name} 需要「{_level_label(name, required)}」及以上的泛化策略，"
                                f"现行策略仅达到「{_level_label(name, provided)}」",
                                column=name,
                                required_level=required,
                                provided_level=provided,
                            )
                        )
            # 5a. 策略时效：校验完成后策略有变更 → 旧结论失效
            changed = _changed_policies(db, table, check)
            if changed:
                gaps.append(
                    _gap(
                        POLICY_CHANGED_AFTER_CHECK,
                        f"校验完成后策略 {'、'.join(changed)} 有新增/修改/停用，"
                        "旧校验结论已失效，请重新执行 k-匿名校验",
                        policies=changed,
                    )
                )
            # 5b. 数据时效：校验完成后上游数据有变化 → 旧结论失效
            if check.status == "succeeded":
                if not check.data_signature:
                    gaps.append(
                        _gap(
                            KANON_SIGNATURE_MISSING,
                            "最新校验缺少数据签名（旧版校验记录），无法确认数据未变化，请重新执行校验",
                            check_id=str(check.id),
                        )
                    )
                elif env["data_signature"] != check.data_signature:
                    gaps.append(
                        _gap(
                            DATA_CHANGED_AFTER_CHECK,
                            "校验完成后上游数据已发生变化，旧校验结论已失效，请重新执行 k-匿名校验",
                            check_id=str(check.id),
                        )
                    )

    fingerprint = current_fingerprint(db, table, env)
    snapshot = {
        "evaluated_at": iso(_now()),
        "table": table.table_name,
        "columns_total": len(columns),
        "direct_id_columns": [
            column.name
            for column in columns
            if column.column_role == ColumnRole.DIRECT_ID.value or column.pii_type
        ],
        "uncovered_columns": uncovered,
        "kanon_required": kanon_required,
        "quasi_id_columns": qi_columns,
        "sensitive_columns": sensitive_columns,
        "check": (
            {
                "id": str(check.id),
                "status": check.status,
                "passed": check.passed,
                "final_k": check.final_k,
                "final_l": check.final_l,
                "target_k": check.target_k,
                "target_l": check.target_l,
                "finished_at": iso(check.finished_at),
            }
            if check is not None
            else None
        ),
        "active_policy_count": sum(1 for policy in policies.values() if policy is not None),
        "data_signature": (env["data_signature"] or "")[:12],
    }
    return {"passed": not gaps, "gaps": gaps, "fingerprint": fingerprint, "snapshot": snapshot}


def apply_verdict(export: ExportRequest, verdict: dict[str, Any]) -> None:
    """把评估结论落到台账记录上（由调用方提交事务）。"""
    export.gate_status = GateStatus.PASSED.value if verdict["passed"] else GateStatus.BLOCKED.value
    export.gate_gaps_json = verdict["gaps"]
    export.gate_fingerprint = verdict["fingerprint"]
    export.gate_snapshot_json = verdict["snapshot"]
    export.gate_checked_at = _now()


def is_stale(export: ExportRequest, live_fingerprint: str) -> bool:
    """台账展示用：已得出的结论与现行环境指纹不符 → 结论已失效。"""
    if export.gate_status == GateStatus.UNCHECKED.value or not export.gate_fingerprint:
        return False
    return export.gate_fingerprint != live_fingerprint


def _now():
    from src.models.base import utcnow

    return utcnow()
