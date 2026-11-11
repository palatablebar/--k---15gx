from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class EnumsOut(BaseModel):
    pii_types: dict[str, str]
    mask_methods: dict[str, str]
    sensitivity_levels: dict[str, str]
    export_statuses: dict[str, str]
    column_roles: dict[str, str]
    roles: dict[str, str]
    permissions: dict[str, list[str]]
    generalize_kinds: list[str]
    algorithm_versions: dict[str, str]
    params: dict[str, Any]
