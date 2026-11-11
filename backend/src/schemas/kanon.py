from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CheckCreateRequest(BaseModel):
    table_id: str
    quasi_identifiers: list[str] = Field(min_length=2, max_length=4)
    sensitive_column: str
    target_k: int = Field(default=5, ge=2, le=50)
    target_l: int = Field(default=2, ge=1, le=10)


class CheckOut(BaseModel):
    id: str
    table_id: str
    table_name: str
    quasi_identifiers: list[str]
    sensitive_column: str
    target_k: int
    target_l: int
    status: str
    base_k: int | None
    base_l: int | None
    final_k: int | None
    final_l: int | None
    passed: bool | None
    recommended_level: dict[str, Any]
    candidates: list[Any]
    equivalence_classes: list[Any]
    class_size_histogram: dict[str, Any]
    information_loss: float | None
    conclusion: str
    error_detail: str | None
    task_id: str | None
    created_by_email: str | None
    created_at: str | None
    finished_at: str | None
