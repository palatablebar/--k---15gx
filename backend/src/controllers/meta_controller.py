"""健康检查与枚举字典。"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.config.settings import settings
from src.constants.enums import (
    EXPORT_STATUS_LABELS,
    MASK_METHOD_LABELS,
    PII_TYPE_LABELS,
    SENSITIVITY_LABELS,
    ColumnRole,
    GeneralizeKind,
    PIIType,
    MaskMethod,
    SensitivityLevel,
)
from src.constants.roles import PERMISSIONS, ROLE_LABELS
from src.config.database import ping_db
from src.services.pii_detector import ALGORITHM_VERSION
from src.utils.redis_client import redis_ping, worker_heartbeat

COLUMN_ROLE_LABELS = {
    ColumnRole.DIRECT_ID.value: "直接标识符",
    ColumnRole.QUASI_ID.value: "准标识符",
    ColumnRole.SENSITIVE.value: "敏感属性",
    ColumnRole.NON_SENSITIVE.value: "非敏感",
}


def health(db: Session) -> dict[str, Any]:
    heartbeat = worker_heartbeat()
    import time

    worker_age = round(time.time() - heartbeat, 1) if heartbeat else None
    return {
        "status": "ok",
        "service": "maskguard-backend",
        "version": "1.0.0",
        "db": ping_db(),
        "redis": redis_ping(),
        "worker": {
            "heartbeat_age_seconds": worker_age,
            "alive": worker_age is not None and worker_age < 90,
        },
        "algorithm_versions": {
            "pii": ALGORITHM_VERSION,
            "k_anonymity": "kanon-1.0",
        },
    }


def enums() -> dict[str, Any]:
    return {
        "pii_types": PII_TYPE_LABELS,
        "mask_methods": MASK_METHOD_LABELS,
        "sensitivity_levels": SENSITIVITY_LABELS,
        "export_statuses": EXPORT_STATUS_LABELS,
        "column_roles": COLUMN_ROLE_LABELS,
        "roles": ROLE_LABELS,
        "permissions": {key: list(value) for key, value in PERMISSIONS.items()},
        "generalize_kinds": [kind.value for kind in GeneralizeKind],
        "algorithm_versions": {"pii": ALGORITHM_VERSION, "k_anonymity": "kanon-1.0"},
        "params": {
            "age_reference_date": settings.age_reference_date,
            "default_target_k": settings.default_target_k,
            "default_target_l": settings.default_target_l,
            "pii_types_count": len(PIIType),
            "mask_methods_count": len(MaskMethod),
            "sensitivity_levels_count": len(SensitivityLevel),
        },
    }
