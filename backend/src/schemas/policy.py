from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class PolicyCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    table_id: str | None = None
    column_pattern: str = Field(default="*", min_length=1, max_length=120)
    pii_type: Literal["mobile", "id_card", "email", "name", "address"] | None = None
    method: Literal["mask", "hash", "generalize", "suppress"]
    params: dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    is_active: bool = True


class PolicyUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    method: Literal["mask", "hash", "generalize", "suppress"] | None = None
    params: dict[str, Any] | None = None
    description: str | None = None
    is_active: bool | None = None


class PolicyOut(BaseModel):
    id: str
    name: str
    table_id: str | None
    table_name: str | None
    column_pattern: str
    pii_type: str | None
    method: str
    params: dict[str, Any]
    description: str
    is_active: bool
    created_by: str | None
    created_at: str | None
    updated_at: str | None


class PreviewSampleOut(BaseModel):
    before: str
    after: str
    removable_span: list[int] = Field(default_factory=list)


class PreviewColumnOut(BaseModel):
    column_id: str
    column_name: str
    data_type: str
    pii_type: str | None
    method: str
    total_rows: int
    changed_rows: int
    distinct_before: int
    distinct_after: int
    samples: list[PreviewSampleOut]


class PreviewOut(BaseModel):
    policy_id: str
    policy_name: str
    method: str
    params: dict[str, Any]
    total_rows: int
    applied_columns: list[PreviewColumnOut]
    warnings: list[str] = Field(default_factory=list)
