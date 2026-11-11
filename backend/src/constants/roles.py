"""角色与权限矩阵：admin（数据源/策略/审批）、dpo（PII 复核/k-匿名/审批）、client（只读+申请）。"""
from __future__ import annotations

ROLE_ADMIN = "admin"
ROLE_DPO = "dpo"
ROLE_CLIENT = "client"

ALL_ROLES = (ROLE_ADMIN, ROLE_DPO, ROLE_CLIENT)

ROLE_LABELS: dict[str, str] = {
    ROLE_ADMIN: "数据平台管理员",
    ROLE_DPO: "数据保护官",
    ROLE_CLIENT: "科研客户",
}

# 权限点 → 允许的角色
PERMISSIONS: dict[str, tuple[str, ...]] = {
    "datasets:read": ALL_ROLES,
    "datasets:scan": (ROLE_ADMIN, ROLE_DPO),
    "pii:read": ALL_ROLES,
    "pii:review": (ROLE_ADMIN, ROLE_DPO),
    "policies:read": ALL_ROLES,
    "policies:write": (ROLE_ADMIN,),
    "policies:preview": (ROLE_ADMIN, ROLE_DPO),
    "kanon:read": ALL_ROLES,
    "kanon:run": (ROLE_ADMIN, ROLE_DPO),
    "exports:read": ALL_ROLES,
    "exports:create": ALL_ROLES,
    "exports:approve": (ROLE_ADMIN, ROLE_DPO),
    "audit:read": (ROLE_ADMIN, ROLE_DPO),
}


def role_can(role: str, permission: str) -> bool:
    return role in PERMISSIONS.get(permission, ())
