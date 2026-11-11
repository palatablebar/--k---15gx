"""模型 → 出口 JSON 的唯一转换点，controller 只负责编排。"""
from __future__ import annotations

from typing import Any

from src.schemas.common import iso


def column_out(column: Any) -> dict[str, Any]:
    return {
        "id": str(column.id),
        "table_id": str(column.table_id),
        "name": column.name,
        "data_type": column.data_type,
        "ordinal": column.ordinal,
        "column_role": column.column_role,
        "sensitivity_level": column.sensitivity_level,
        "null_ratio": round(float(column.null_ratio), 4),
        "distinct_ratio": round(float(column.distinct_ratio), 4),
        "pii_type": column.pii_type,
        "pii_confidence": round(float(column.pii_confidence), 4),
        "sample_values": list(column.sample_values_json or []),
        "current_policy_id": str(column.current_policy_id) if column.current_policy_id else None,
        "is_scanned": column.is_scanned,
        "scanned_at": iso(column.scanned_at),
    }


def table_out(table: Any, pii_column_count: int = 0) -> dict[str, Any]:
    return {
        "id": str(table.id),
        "schema_name": table.schema_name,
        "table_name": table.table_name,
        "display_name": table.display_name,
        "description": table.description,
        "business_domain": table.business_domain,
        "row_count": table.row_count,
        "column_count": table.column_count,
        "sensitivity_level": table.sensitivity_level,
        "owner_note": table.owner_note,
        "last_profiled_at": iso(table.last_profiled_at),
        "pii_column_count": pii_column_count,
    }


def finding_out(finding: Any, column: Any, table: Any) -> dict[str, Any]:
    return {
        "id": str(finding.id),
        "column_id": str(finding.column_id),
        "column_name": column.name if column else "",
        "table_id": str(table.id) if table else "",
        "table_name": table.table_name if table else "",
        "pii_type": finding.pii_type,
        "scanned_rows": finding.scanned_rows,
        "candidate_rows": finding.candidate_rows,
        "matched_count": finding.matched_count,
        "checksum_checked_count": finding.checksum_checked_count,
        "checksum_pass_count": finding.checksum_pass_count,
        "hit_rate": round(float(finding.hit_rate), 4),
        "checksum_pass_rate": round(float(finding.checksum_pass_rate), 4),
        "uniqueness_penalty": round(float(finding.uniqueness_penalty), 4),
        "confidence": round(float(finding.confidence), 4),
        "algorithm_version": finding.algorithm_version,
        "sample_values": list(column.sample_values_json or []) if column else [],
        "evidence": [
            {
                "value": item.get("value", ""),
                "display_value": item.get("value", ""),
                "kind": item.get("kind", "match"),
                "span_start": int(item.get("span_start", 0)),
                "span_end": int(item.get("span_end", 0)),
                "validation": item.get("validation", "not_applicable"),
                "note": item.get("note", ""),
            }
            for item in (finding.evidence_json or [])
        ],
        "created_at": iso(finding.created_at),
    }


def check_out(check: Any, table_name: str, created_by_email: str | None) -> dict[str, Any]:
    return {
        "id": str(check.id),
        "table_id": str(check.table_id),
        "table_name": table_name,
        "quasi_identifiers": list(check.quasi_identifiers_json or []),
        "sensitive_column": check.sensitive_column,
        "target_k": check.target_k,
        "target_l": check.target_l,
        "status": check.status,
        "base_k": check.base_k,
        "base_l": check.base_l,
        "final_k": check.final_k,
        "final_l": check.final_l,
        "passed": check.passed,
        "recommended_level": dict(check.recommended_level_json or {}),
        "candidates": list(check.candidates_json or []),
        "equivalence_classes": list(check.equivalence_classes_json or []),
        "class_size_histogram": dict(check.class_size_histogram_json or {}),
        "information_loss": round(float(check.information_loss), 4) if check.information_loss is not None else None,
        "conclusion": check.conclusion,
        "error_detail": check.error_detail,
        "task_id": check.task_id,
        "created_by_email": created_by_email,
        "created_at": iso(check.created_at),
        "finished_at": iso(check.finished_at),
    }


def export_out(request: Any, table: Any, requester: Any, reviewer: Any) -> dict[str, Any]:
    return {
        "id": str(request.id),
        "table_id": str(request.table_id),
        "table_name": table.table_name if table else "",
        "table_display_name": table.display_name if table else "",
        "requester_id": str(request.requester_id),
        "requester_email": requester.email if requester else "",
        "requester_name": requester.display_name if requester else "",
        "purpose": request.purpose,
        "requested_rows": request.requested_rows,
        "dataset_version": request.dataset_version,
        "status": request.status,
        "build_status": request.build_status,
        "review_note": request.review_note,
        "reviewed_by_email": reviewer.email if reviewer else None,
        "reviewed_at": iso(request.reviewed_at),
        "file_digest": request.file_digest,
        "masked_rows": request.masked_rows,
        "applied_policies": [
            str(item.get("name", "")) for item in (request.applied_policies_json or [])
        ],
        "error_detail": request.error_detail,
        "created_at": iso(request.created_at),
    }


def audit_out(log: Any) -> dict[str, Any]:
    return {
        "id": str(log.id),
        "actor_email": log.actor_email,
        "actor_role": log.actor_role,
        "action": log.action,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "detail": dict(log.detail_json or {}),
        "ip": log.ip,
        "trace_id": log.trace_id,
        "created_at": iso(log.created_at),
    }
