"""算法 2：k-匿名 / ℓ-diversity 等价类计算 + 泛化层级搜索。

口径
----
- 准标识 QI：birth_date（派生年龄）、gender、zip 等列；敏感属性 S：diagnosis。
- 等价类：把每行 QI 按当前泛化层级映射后分组，组大小 = class size。
- k = 所有等价类的最小行数；ℓ = 每个等价类内 S 的不同取值数的最小值。
- 泛化层级：年龄 1/5/10 岁区间；邮编 5/3/2 位。
- 枚举所有层级组合；在 k≥目标 k 且 ℓ≥目标 ℓ 的组合里选信息损失最小者：

    level_loss     = mean((level_index)/(level_count-1))      # 区间宽度代价
    distinct_loss  = 1 - class_count / baseline_class_count    # 区分度损失
    information_loss = 0.5 × level_loss + 0.5 × distinct_loss

  结果确定：层级组合按固定顺序枚举，排序键 (passed desc, information_loss asc, k desc)。
"""
from __future__ import annotations

import itertools
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from src.config.settings import settings
from src.constants import error_codes as codes
from src.constants.enums import ColumnRole
from src.constants.limits import KANON_MAX_CLASSES, KANON_MAX_ROWS
from src.models.dataset_column import DatasetColumn
from src.models.dataset_table import DatasetTable
from src.models.k_anonymity_check import KAnonymityCheck
from src.models.user import User
from src.services import raw_data_service
from src.utils.errors import AppError, not_found
from src.utils.logger import get_logger, log_info, log_warning

logger = get_logger("maskguard.kanon")

AGE_EXACT = {"kind": "age_exact", "label": "精确年龄"}
AGE_5 = {"kind": "age_band", "width": 5, "label": "5 岁区间"}
AGE_10 = {"kind": "age_band", "width": 10, "label": "10 岁区间"}
ZIP_FULL = {"kind": "exact", "label": "完整邮编"}
ZIP_3 = {"kind": "zip_prefix", "keep": 3, "label": "邮编前 3 位"}
ZIP_2 = {"kind": "zip_prefix", "keep": 2, "label": "邮编前 2 位"}

QI_SPECS: dict[str, list[dict[str, Any]]] = {
    "birth_date": [AGE_EXACT, AGE_5, AGE_10],
    "age": [AGE_EXACT, AGE_5, AGE_10],
    "zip": [ZIP_FULL, ZIP_3, ZIP_2],
    "gender": [{"kind": "exact", "label": "原始取值"}],
}


def levels_for(qi_column: str) -> list[dict[str, Any]]:
    return QI_SPECS.get(qi_column, [{"kind": "exact", "label": "原始取值"}])


def _parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def derive_age(value: Any) -> int | None:
    born = _parse_date(value)
    if born is None:
        return None
    reference = date.fromisoformat(settings.age_reference_date)
    return max(0, (reference - born).days // 365)


def _generalize(qi_column: str, value: Any, level_spec: dict[str, Any]) -> str:
    kind = level_spec["kind"]
    if kind == "age_exact":
        age = derive_age(value)
        if age is not None:
            return str(age)
        try:
            return str(int(value))
        except (TypeError, ValueError):
            return "未知"
    if kind == "age_band":
        age = derive_age(value)
        if age is None:
            try:
                age = int(value)
            except (TypeError, ValueError):
                return "未知"
        width = int(level_spec["width"])
        low = (age // width) * width
        return f"{low}-{low + width - 1}岁"
    if kind == "zip_prefix":
        digits = "".join(ch for ch in str(value or "") if ch.isdigit())
        keep = int(level_spec["keep"])
        return digits[:keep] if len(digits) >= keep else (digits or "未知")
    return str(value) if value is not None else "未知"


def _classes(
    rows: list[dict[str, Any]],
    qi_columns: list[str],
    sensitive_column: str,
    levels: dict[str, int],
) -> dict[str, Any]:
    buckets: dict[tuple[str, ...], dict[str, Any]] = {}
    for row in rows:
        key = tuple(
            _generalize(column, row.get(column), levels_for(column)[levels[column]])
            for column in qi_columns
        )
        bucket = buckets.setdefault(key, {"size": 0, "sensitive": set(), "qi": {}})
        bucket["size"] += 1
        bucket["sensitive"].add(str(row.get(sensitive_column, "")))
        if not bucket["qi"]:
            bucket["qi"] = {column: key[index] for index, column in enumerate(qi_columns)}
    class_list = [
        {
            "qi": bucket["qi"],
            "size": bucket["size"],
            "sensitive_values": sorted(bucket["sensitive"]),
        }
        for bucket in buckets.values()
    ]
    class_list.sort(key=lambda item: (item["size"], sorted(item["qi"].items())))
    sizes = [item["size"] for item in class_list]
    sensitive_counts = [len(item["sensitive_values"]) for item in class_list]
    histogram: dict[str, int] = {}
    for size in sizes:
        histogram[str(size)] = histogram.get(str(size), 0) + 1
    return {
        "class_count": len(class_list),
        "k": min(sizes) if sizes else 0,
        "l": min(sensitive_counts) if sensitive_counts else 0,
        "classes": class_list,
        "histogram": dict(sorted(histogram.items(), key=lambda item: int(item[0]))),
    }


def _level_penalty(qi_columns: list[str], levels: dict[str, int]) -> float:
    penalties: list[float] = []
    for column in qi_columns:
        specs = levels_for(column)
        if len(specs) <= 1:
            penalties.append(0.0)
            continue
        penalties.append(levels[column] / (len(specs) - 1))
    return sum(penalties) / len(penalties) if penalties else 0.0


def compute(
    rows: list[dict[str, Any]],
    qi_columns: list[str],
    sensitive_column: str,
    target_k: int,
    target_l: int,
) -> dict[str, Any]:
    base_levels = {column: 0 for column in qi_columns}
    base = _classes(rows, qi_columns, sensitive_column, base_levels)
    base_class_count = max(base["class_count"], 1)

    candidates: list[dict[str, Any]] = []
    options = [range(len(levels_for(column))) for column in qi_columns]
    for combination in itertools.product(*options):
        levels = {column: combination[index] for index, column in enumerate(qi_columns)}
        stats = _classes(rows, qi_columns, sensitive_column, levels)
        level_loss = _level_penalty(qi_columns, levels)
        distinct_loss = 1.0 - stats["class_count"] / base_class_count
        information_loss = round(0.5 * level_loss + 0.5 * distinct_loss, 4)
        satisfies_k = stats["k"] >= target_k
        satisfies_l = stats["l"] >= target_l
        candidates.append(
            {
                "levels": {column: levels[column] + 1 for column in qi_columns},
                "level_labels": {
                    column: levels_for(column)[levels[column]]["label"] for column in qi_columns
                },
                "k": stats["k"],
                "l": stats["l"],
                "class_count": stats["class_count"],
                "information_loss": information_loss,
                "level_loss": round(level_loss, 4),
                "distinct_loss": round(distinct_loss, 4),
                "passed": bool(satisfies_k and satisfies_l),
            }
        )

    satisfying = [candidate for candidate in candidates if candidate["passed"]]
    if satisfying:
        recommended = min(
            satisfying,
            key=lambda item: (item["information_loss"], -item["class_count"], item["k"]),
        )
        passed = True
    else:
        recommended = max(candidates, key=lambda item: (item["k"], item["l"], -item["information_loss"]))
        passed = False

    candidates.sort(key=lambda item: (not item["passed"], item["information_loss"], -item["k"]))

    if passed:
        conclusion = (
            f"基线层级（精确年龄 / 完整邮编）k={base['k']}、ℓ={base['l']}，低于目标 k≥{target_k}、ℓ≥{target_l}；"
            f"推荐使用「{'、'.join(recommended['level_labels'].values())}」泛化，"
            f"得到 k={recommended['k']}、ℓ={recommended['l']}，信息损失 {recommended['information_loss']}，达标。"
        )
    else:
        conclusion = (
            f"基线 k={base['k']}、ℓ={base['l']}，未达标；"
            f"穷举 {len(candidates)} 种泛化组合后最高仅 k={recommended['k']}、ℓ={recommended['l']}，"
            f"仍不满足目标 k≥{target_k}、ℓ≥{target_l}，需要补充记录行或抑制部分行。"
        )

    return {
        "row_count": len(rows),
        "base": {
            "levels": {column: 1 for column in qi_columns},
            "level_labels": {column: levels_for(column)[0]["label"] for column in qi_columns},
            "k": base["k"],
            "l": base["l"],
            "class_count": base["class_count"],
            "information_loss": 0.0,
        },
        "recommended": recommended,
        "candidates": candidates,
        "passed": passed,
        "conclusion": conclusion,
        "equivalence_classes": base["classes"][:KANON_MAX_CLASSES],
        "class_size_histogram": base["histogram"],
        "base_class_total": base["class_count"],
    }


def validate_selection(db: Session, table: DatasetTable, qi_columns: list[str], sensitive_column: str) -> None:
    columns = {
        column.name: column
        for column in db.query(DatasetColumn).filter(DatasetColumn.table_id == table.id).all()
    }
    if len(set(qi_columns)) != len(qi_columns) or len(qi_columns) < 2 or len(qi_columns) > 4:
        raise AppError(codes.KANON_INVALID_QI, None, f"qi={qi_columns}")
    for name in qi_columns:
        column = columns.get(name)
        if column is None:
            raise AppError(codes.KANON_INVALID_QI, f"准标识列 {name} 不存在", str(name))
        if column.column_role == ColumnRole.DIRECT_ID.value:
            raise AppError(
                codes.KANON_INVALID_QI,
                f"{name} 是直接标识符，不能作为准标识列（应先脱敏或移除）",
                f"column={name} role={column.column_role}",
            )
    sensitive = columns.get(sensitive_column)
    if sensitive is None:
        raise AppError(codes.KANON_SENSITIVE_MISSING, f"敏感属性列 {sensitive_column} 不存在", "")
    if sensitive.column_role != ColumnRole.SENSITIVE.value:
        raise AppError(
            codes.KANON_SENSITIVE_MISSING,
            f"{sensitive_column} 不是敏感属性列",
            f"column={sensitive_column} role={sensitive.column_role}",
        )
    if sensitive_column in qi_columns:
        raise AppError(codes.KANON_INVALID_QI, "敏感属性列不能同时作为准标识列", sensitive_column)


def execute_check(db: Session, check: KAnonymityCheck) -> KAnonymityCheck:
    """执行一条校验记录（backend 同步兜底 / worker 异步各调用一次）。"""
    table = db.get(DatasetTable, check.table_id)
    if table is None:
        raise AppError(codes.NOT_FOUND, "数据集不存在", str(check.table_id))
    qi_columns = [str(item) for item in (check.quasi_identifiers_json or [])]
    try:
        fetch_columns = list(dict.fromkeys(qi_columns + [check.sensitive_column]))
        rows = raw_data_service.fetch_rows(db, table.table_name, fetch_columns, KANON_MAX_ROWS)
        result = compute(rows, qi_columns, check.sensitive_column, check.target_k, check.target_l)
        check.status = "succeeded"
        check.base_k = result["base"]["k"]
        check.base_l = result["base"]["l"]
        check.final_k = result["recommended"]["k"]
        check.final_l = result["recommended"]["l"]
        check.passed = result["passed"]
        check.recommended_level_json = {
            "levels": result["recommended"]["levels"],
            "level_labels": result["recommended"]["level_labels"],
            "information_loss": result["recommended"]["information_loss"],
            "class_count": result["recommended"]["class_count"],
        }
        check.candidates_json = result["candidates"]
        check.equivalence_classes_json = result["equivalence_classes"]
        check.class_size_histogram_json = result["class_size_histogram"]
        check.information_loss = result["recommended"]["information_loss"]
        check.conclusion = result["conclusion"]
        check.error_detail = None
        check.finished_at = _now()
        db.commit()
        log_info(
            logger,
            "kanon.done",
            check=str(check.id),
            base_k=check.base_k,
            rec_k=check.final_k,
            passed=check.passed,
        )
    except Exception as exc:  # noqa: BLE001 - 失败要落库，前端能看到原因
        check.status = "failed"
        check.error_detail = str(exc)
        check.finished_at = _now()
        db.commit()
        log_warning(logger, "kanon.failed", check=str(check.id), reason=exc)
    return check


def create_check(db: Session, user: User, payload: Any) -> KAnonymityCheck:
    table = db.get(DatasetTable, payload.table_id)
    if table is None:
        raise not_found("数据集表", payload.table_id)
    validate_selection(db, table, payload.quasi_identifiers, payload.sensitive_column)
    check = KAnonymityCheck(
        table_id=table.id,
        quasi_identifiers_json=payload.quasi_identifiers,
        sensitive_column=payload.sensitive_column,
        target_k=payload.target_k,
        target_l=payload.target_l,
        status="queued",
        created_by=user.id,
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    return check


def _now():
    from src.models.base import utcnow

    return utcnow()
