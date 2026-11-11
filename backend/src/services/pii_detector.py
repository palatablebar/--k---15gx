"""算法 1：PII 类型识别。

对每列读取原始值，逐类型匹配 + 格式/校验位验证，选取得分最高的类型：

    hit_rate          = 命中数 / 候选值数（候选值 = 非空且未被 `*`/X 预掩码的值）
    checksum_rate     = 校验通过数 / 参与校验数（无校验位的类型记 1.0）
    uniqueness_penalty= 0.2 × 候选值唯一率
    confidence        = hit_rate × checksum_rate × (1 - uniqueness_penalty)

身份证走 GB 11643-1999 加权校验位；手机号校验号段白名单；姓名查姓氏表；
地址查行政区/街道关键词。命中率低于 2%（且命中数 < 5）视为噪声，不判 PII。
"""
from __future__ import annotations

import math
import time
from typing import Any, Callable

from sqlalchemy.orm import Session

from src.constants.enums import PIIType
from src.constants.limits import PII_EVIDENCE_SAMPLES, PII_SCAN_MAX_ROWS
from src.models.dataset_column import DatasetColumn
from src.models.dataset_table import DatasetTable
from src.models.pii_finding import PIIFinding
from src.services import raw_data_service
from src.utils import pii_rules
from src.utils.logger import get_logger, log_info

logger = get_logger("maskguard.pii")
ALGORITHM_VERSION = "pii-1.0"
NOISE_MIN_HITS = 5
NOISE_MIN_RATE = 0.02

Detector = dict[str, Callable[[str], bool]]

# 顺序有意义：先判强格式（证件/手机号/邮箱），再判弱语义（姓名/地址），
# 避免 18 位数字串被地址关键词误伤。
DETECTORS: list[tuple[str, Detector]] = [
    (PIIType.ID_CARD.value, {
        "match": pii_rules.ID_CARD_RE.match,
        "validate": pii_rules.id_card_checksum,
    }),
    (PIIType.MOBILE.value, {
        "match": pii_rules.MOBILE_RE.match,
        "validate": pii_rules.mobile_ok,
    }),
    (PIIType.EMAIL.value, {
        "match": pii_rules.email_ok,
        "validate": pii_rules.email_ok,
    }),
    (PIIType.NAME.value, {
        "match": pii_rules.name_ok,
        "validate": pii_rules.name_ok,
    }),
    (PIIType.ADDRESS.value, {
        "match": pii_rules.address_ok,
        "validate": pii_rules.address_ok,
    }),
]


def _evaluate_type(values: list[str], detector: Detector) -> dict[str, Any]:
    candidates = [value for value in values if value.strip() != "" and not pii_rules.is_placeholder(value)]
    matched_values: list[str] = []
    checked = 0
    passed = 0
    for value in candidates:
        if detector["match"](value):
            matched_values.append(value)
            checked += 1
            if detector["validate"](value):
                passed += 1

    candidate_rows = len(candidates)
    matched = len(matched_values)
    hit_rate = matched / candidate_rows if candidate_rows else 0.0
    checksum_rate = (passed / checked) if checked else 1.0
    distinct_ratio = (len(set(candidates)) / candidate_rows) if candidate_rows else 0.0
    uniqueness_penalty = round(0.2 * distinct_ratio, 4)
    confidence = hit_rate * checksum_rate * (1.0 - uniqueness_penalty)
    return {
        "pii_type": "",
        "candidate_rows": candidate_rows,
        "matched_count": matched,
        "checksum_checked_count": checked,
        "checksum_pass_count": passed,
        "hit_rate": round(hit_rate, 4),
        "checksum_pass_rate": round(checksum_rate, 4),
        "uniqueness_penalty": uniqueness_penalty,
        "confidence": round(confidence, 4),
        "_matched_values": matched_values,
        "_candidates": candidates,
    }


def detect_column(values: list[str]) -> dict[str, Any]:
    """对单列候选值做识别，返回胜出的类型 + 置信度拆解 + 命中样例。"""
    best: dict[str, Any] | None = None
    per_type: dict[str, dict[str, Any]] = {}
    for pii_type, detector in DETECTORS:
        result = _evaluate_type(values, detector)
        result["pii_type"] = pii_type
        per_type[pii_type] = {k: v for k, v in result.items() if not k.startswith("_")}
        if result["matched_count"] == 0:
            continue
        min_hits = max(NOISE_MIN_HITS, math.ceil(NOISE_MIN_RATE * max(result["candidate_rows"], 1)))
        if result["matched_count"] < min_hits:
            continue
        if best is None or (result["matched_count"], result["confidence"]) > (
            best["matched_count"], best["confidence"]
        ):
            best = result

    if best is None:
        return {
            "pii_type": None,
            "candidate_rows": len([v for v in values if v.strip() and not pii_rules.is_placeholder(v)]),
            "matched_count": 0,
            "checksum_checked_count": 0,
            "checksum_pass_count": 0,
            "hit_rate": 0.0,
            "checksum_pass_rate": 1.0,
            "uniqueness_penalty": 0.0,
            "confidence": 0.0,
            "evidence": [],
            "per_type": per_type,
        }

    matched_values = best["_matched_values"]
    candidates = best["_candidates"]
    evidence = _build_evidence(matched_values, candidates, best["pii_type"])
    return {
        "pii_type": best["pii_type"],
        "candidate_rows": best["candidate_rows"],
        "matched_count": best["matched_count"],
        "checksum_checked_count": best["checksum_checked_count"],
        "checksum_pass_count": best["checksum_pass_count"],
        "hit_rate": best["hit_rate"],
        "checksum_pass_rate": best["checksum_pass_rate"],
        "uniqueness_penalty": best["uniqueness_penalty"],
        "confidence": best["confidence"],
        "evidence": evidence,
        "per_type": per_type,
    }


def _build_evidence(matched: list[str], candidates: list[str], pii_type: str) -> list[dict[str, Any]]:
    """证据样例：命中值 + 校验结果 + 命中位置；再混 2 条未命中样例做对照。"""
    detector = dict(DETECTORS)[pii_type]
    evidence: list[dict[str, Any]] = []
    for value in matched[: PII_EVIDENCE_SAMPLES - 2]:
        ok = bool(detector["validate"](value))
        evidence.append(
            {
                "value": value,
                "kind": "match",
                "span_start": 0,
                "span_end": len(value),
                "validation": "passed" if ok else "failed",
                "note": _validation_note(pii_type, ok),
            }
        )
    misses = [value for value in candidates if value not in set(matched)]
    for value in misses[:2]:
        evidence.append(
            {
                "value": value,
                "kind": "miss",
                "span_start": 0,
                "span_end": 0,
                "validation": "not_applicable",
                "note": "未命中该类型规则",
            }
        )
    return evidence


def _validation_note(pii_type: str, ok: bool) -> str:
    if pii_type == PIIType.ID_CARD.value:
        return "GB11643 校验位通过" if ok else "校验位不通过"
    if pii_type == PIIType.MOBILE.value:
        return "号段合法" if ok else "号段不在白名单"
    if pii_type == PIIType.NAME.value:
        return "姓氏表命中" if ok else "姓氏表未命中"
    if pii_type == PIIType.ADDRESS.value:
        return "地址关键词命中" if ok else "地址关键词未命中"
    return "格式合法" if ok else "格式不合法"


def scan_table(db: Session, table: DatasetTable, *, commit: bool = True) -> dict[str, Any]:
    """扫描一张表的全部列：更新列画像 + upsert PII 证据 + 返回汇总。"""
    started = time.perf_counter()
    columns = (
        db.query(DatasetColumn)
        .filter(DatasetColumn.table_id == table.id)
        .order_by(DatasetColumn.ordinal)
        .all()
    )
    findings: list[PIIFinding] = []
    total_matched = 0
    checksum_passed = 0
    for column in columns:
        values = raw_data_service.column_values(db, table.table_name, column.name, PII_SCAN_MAX_ROWS)
        result = detect_column(values)
        stats = {
            "total": len(values),
            "non_empty": [value for value in values if value.strip() != ""],
        }
        column.pii_type = result["pii_type"]
        column.pii_confidence = round(result["confidence"], 4)
        column.is_scanned = True
        column.scanned_at = _now()
        column.distinct_ratio = round(
            len(set(stats["non_empty"])) / len(stats["non_empty"]), 4
        ) if stats["non_empty"] else 0.0
        column.null_ratio = round((len(values) - len(stats["non_empty"])) / len(values), 4) if values else 0.0

        if result["pii_type"] is None:
            continue

        finding = (
            db.query(PIIFinding)
            .filter(
                PIIFinding.column_id == column.id,
                PIIFinding.algorithm_version == ALGORITHM_VERSION,
            )
            .one_or_none()
        )
        if finding is None:
            finding = PIIFinding(column_id=column.id, algorithm_version=ALGORITHM_VERSION)
            db.add(finding)
        finding.pii_type = result["pii_type"]
        finding.scanned_rows = len(values)
        finding.candidate_rows = result["candidate_rows"]
        finding.matched_count = result["matched_count"]
        finding.checksum_checked_count = result["checksum_checked_count"]
        finding.checksum_pass_count = result["checksum_pass_count"]
        finding.hit_rate = result["hit_rate"]
        finding.checksum_pass_rate = result["checksum_pass_rate"]
        finding.uniqueness_penalty = result["uniqueness_penalty"]
        finding.confidence = result["confidence"]
        finding.evidence_json = result["evidence"]
        db.flush()
        findings.append(finding)
        total_matched += result["matched_count"]
        checksum_passed += result["checksum_pass_count"]
        log_info(
            logger,
            "pii.scan",
            table=table.table_name,
            column=column.name,
            pii_type=result["pii_type"],
            hit=result["matched_count"],
            confidence=result["confidence"],
        )

    table.last_profiled_at = _now()
    db.flush()
    if commit:
        db.commit()
    log_info(
        logger,
        "pii.scan.done",
        table=table.table_name,
        columns=len(columns),
        findings=len(findings),
    )
    return {
        "table_id": str(table.id),
        "table_name": table.table_name,
        "columns_scanned": len(columns),
        "findings": len(findings),
        "total_matched": total_matched,
        "checksum_passed": checksum_passed,
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "findings_detail": findings,
    }


def _now():
    from src.models.base import utcnow

    return utcnow()
