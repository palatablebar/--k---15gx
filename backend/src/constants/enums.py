"""领域枚举（后端唯一真相；前端 constants/enums.ts 是它的镜像）。

所有枚举同时被 model（字符串列）、schema（Literal 校验）、service（算法分支）、
route（查询参数）与前端筛选器引用，改一处必须同步改前端镜像。
"""
from __future__ import annotations

from enum import Enum


class PIIType(str, Enum):
    MOBILE = "mobile"
    ID_CARD = "id_card"
    EMAIL = "email"
    NAME = "name"
    ADDRESS = "address"


class MaskMethod(str, Enum):
    MASK = "mask"
    HASH = "hash"
    GENERALIZE = "generalize"
    SUPPRESS = "suppress"


class GeneralizeKind(str, Enum):
    AGE_BAND = "age_band"       # 年龄 → 5/10 岁区间
    ZIP_PREFIX = "zip_prefix"   # 邮编 5 → 3 → 2 位
    DATE_YEAR = "date_year"     # 日期 → 年份
    KEEP_PREFIX = "keep_prefix" # 地址保留省市区前缀


class SensitivityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ColumnRole(str, Enum):
    DIRECT_ID = "direct_id"       # 直接标识符（姓名/证件/手机号）
    QUASI_ID = "quasi_id"         # 准标识符（年龄/性别/邮编）
    SENSITIVE = "sensitive"       # 敏感属性（诊断）
    NON_SENSITIVE = "non_sensitive"


class ExportStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class GateStatus(str, Enum):
    """导出合规门禁结论：未校验 / 达标 / 被拦截（达标与否都可因规则或数据变化而失效）。"""

    UNCHECKED = "unchecked"
    PASSED = "passed"
    BLOCKED = "blocked"


class BuildStatus(str, Enum):
    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class CheckStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AuditAction(str, Enum):
    LOGIN = "login"
    DATASET_SCAN = "dataset.scan"
    POLICY_CREATE = "policy.create"
    POLICY_UPDATE = "policy.update"
    POLICY_PREVIEW = "policy.preview"
    KANON_CHECK = "kanon.check"
    EXPORT_SUBMIT = "export.submit"
    EXPORT_PRECHECK = "export.precheck"
    EXPORT_APPROVE = "export.approve"
    EXPORT_BLOCKED = "export.blocked"
    EXPORT_REJECT = "export.reject"
    EXPORT_DOWNLOAD = "export.download"


PII_TYPE_LABELS: dict[str, str] = {
    PIIType.MOBILE.value: "手机号",
    PIIType.ID_CARD.value: "身份证号",
    PIIType.EMAIL.value: "邮箱",
    PIIType.NAME.value: "姓名",
    PIIType.ADDRESS.value: "地址",
}

MASK_METHOD_LABELS: dict[str, str] = {
    MaskMethod.MASK.value: "掩码",
    MaskMethod.HASH.value: "哈希",
    MaskMethod.GENERALIZE.value: "泛化",
    MaskMethod.SUPPRESS.value: "抑制",
}

SENSITIVITY_LABELS: dict[str, str] = {
    SensitivityLevel.LOW.value: "低",
    SensitivityLevel.MEDIUM.value: "中",
    SensitivityLevel.HIGH.value: "高",
    SensitivityLevel.CRITICAL.value: "极高",
}

EXPORT_STATUS_LABELS: dict[str, str] = {
    ExportStatus.PENDING.value: "待审批",
    ExportStatus.APPROVED.value: "已批准",
    ExportStatus.REJECTED.value: "已驳回",
}

GATE_STATUS_LABELS: dict[str, str] = {
    GateStatus.UNCHECKED.value: "未校验",
    GateStatus.PASSED.value: "门禁达标",
    GateStatus.BLOCKED.value: "门禁拦截",
}
