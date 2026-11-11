from __future__ import annotations

from pydantic import BaseModel, Field


class ExportCreateRequest(BaseModel):
    table_id: str
    purpose: str = Field(min_length=6, max_length=400)
    requested_rows: int = Field(default=800, ge=1, le=5000)


class ReviewRequest(BaseModel):
    note: str = Field(default="", max_length=400)


class ExportOut(BaseModel):
    id: str
    table_id: str
    table_name: str
    table_display_name: str
    requester_id: str
    requester_email: str
    requester_name: str
    purpose: str
    requested_rows: int
    dataset_version: str
    status: str
    build_status: str
    review_note: str
    reviewed_by_email: str | None
    reviewed_at: str | None
    file_digest: str | None
    masked_rows: int | None
    applied_policies: list[str]
    error_detail: str | None
    created_at: str | None
