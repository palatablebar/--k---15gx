"""幂等演示数据：`docker compose exec backend python -m scripts.seed_demo`。

模拟客户：医疗 SaaS「云诊」合规数据服务组，向上游 clinic 库的三张表做脱敏与导出。
自然键：users.email / dataset_tables.table_name / dataset_columns(table_id,name) /
masking_policies.name / export_requests(requester,table,dataset_version) /
k_anonymity_checks(table,qi,sensitive,target) / clinic 表主键。
连跑两次只输出 SEED_SKIPPED，行数完全一致（末尾打印 SEED_SUMMARY {json}）。
"""
from __future__ import annotations

import json
import random
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Any

import sqlalchemy as sa
from sqlalchemy import text

from src.config.database import engine, session_scope
from src.config.settings import settings
from src.constants.enums import ColumnRole, ExportStatus, MaskMethod, PIIType, SensitivityLevel
from src.constants.roles import ROLE_ADMIN, ROLE_CLIENT, ROLE_DPO
from src.models.audit_log import AuditLog
from src.models.dataset_column import DatasetColumn
from src.models.dataset_table import DatasetTable
from src.models.export_request import ExportRequest
from src.models.k_anonymity_check import KAnonymityCheck
from src.models.masking_policy import MaskingPolicy
from src.models.pii_finding import PIIFinding
from src.models.user import User
from src.services import export_service, k_anonymity_service, pii_detector, raw_data_service
from src.utils.password import hash_password
from src.utils.pii_rules import ID_CARD_CHECK_CODES, ID_CARD_WEIGHTS, MOBILE_SEGMENTS

DEMO_PASSWORD = "Demo@2026"
DEMO_USERS = [
    ("admin@clinic.local", "陈而立", ROLE_ADMIN, "云诊 · 合规数据服务组"),
    ("dpo@clinic.local", "沈砚秋", ROLE_DPO, "云诊 · 数据保护办公室"),
    ("client@clinic.local", "林亦舟", ROLE_CLIENT, "心研所 · 临床流行病学组"),
]

RANDOM_SEED = 20261110
REFERENCE_DATE = date(2026, 11, 10)

# 年龄/性别/邮编的分布是 k-匿名演示的关键：240 个等价类 × 3~4 行 → 基线 k=3
PATIENT_AGES = list(range(24, 44))
GENDERS = ["女", "男"]
ZIPS = ["610041", "610042", "611041", "611042", "612041", "612042"]
DIAGNOSES = [
    "2型糖尿病",
    "原发性高血压",
    "冠心病",
    "慢性肾病",
    "甲状腺功能减退",
    "高脂血症",
    "慢性胃炎",
    "骨质疏松",
]
SURNAMES = list("赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦许何吕施张孔曹严华金魏陶姜谢邹喻柏水窦章苏潘葛范彭郎鲁韦昌马苗凤花方俞任袁柳鲍史唐")
GIVEN_NAMES = ["建国", "秀兰", "志强", "海燕", "文博", "雅静", "宁远", "若溪", "明哲", "嘉禾", "清和", "亦宁", "望舒", "牧之", "南乔", "书言"]
DEPARTMENTS = ["内分泌科", "心内科", "肾内科", "老年医学科", "全科", "营养科"]
DOCTOR_NAMES = ["顾清和", "陆知远", "苏静姝", "许砚白", "韩明诚", "邵云舒"]

CITIES = ["成都市武侯区", "成都市锦江区", "成都市青羊区", "成都市高新区"]
ROADS = ["人民南路", "科华北路", "天府大道", "一环路南段", "芳草街", "玉林东路"]
TESTS = [("HBA1C", "%"), ("GLU", "mmol/L"), ("CREA", "umol/L"), ("TSH", "mIU/L"), ("LDL", "mmol/L"), ("K", "mmol/L")]

CREATED = 0
SKIPPED = 0


def _log(kind: str, entity: str, key: str) -> None:
    global CREATED, SKIPPED
    if kind == "SEED_CREATED":
        CREATED += 1
    else:
        SKIPPED += 1
    print(f"{kind} entity={entity} key={key}", flush=True)


def _created(entity: str, key: str) -> None:
    _log("SEED_CREATED", entity, key)


def _skipped(entity: str, key: str) -> None:
    _log("SEED_SKIPPED", entity, key)


# ------------------------------------------------------------------ 原始数据 ----


def build_id_card(birth: date, sequence: int) -> str:
    base = "510104" + birth.strftime("%Y%m%d") + f"{sequence:03d}"
    total = sum(int(base[index]) * ID_CARD_WEIGHTS[index] for index in range(17))
    return base + ID_CARD_CHECK_CODES[total % 11]


def build_patients() -> list[dict[str, Any]]:
    """800 行；前 60 行带可识别的 18 位身份证（58 条校验位正确，2 条故意写错）。"""
    segments = sorted(MOBILE_SEGMENTS)
    rows: list[dict[str, Any]] = []
    combo_index = 0
    serial = 0
    for age in PATIENT_AGES:
        for gender in GENDERS:
            for zip_code in ZIPS:
                count = 4 if combo_index % 3 == 0 else 3
                combo_index += 1
                for _ in range(count):
                    serial += 1
                    birth = REFERENCE_DATE - timedelta(days=age * 365 + 100)
                    if serial <= 60:
                        card = build_id_card(birth, serial)
                        if serial in (59, 60):  # 校验位故意写错，验证算法能识别
                            card = card[:-1] + ("0" if card[-1] != "0" else "1")
                        id_card = card
                    else:
                        id_card = f"5101**********{serial:04d}"
                    if serial <= 680:
                        segment = segments[(serial * 3) % len(segments)]
                        mobile = f"{segment}{serial:08d}"[:11]
                    else:
                        mobile = f"138****{serial % 10000:04d}"
                    rows.append(
                        {
                            "patient_id": f"P{serial:04d}",
                            "name": f"{SURNAMES[(serial * 13) % len(SURNAMES)]}{GIVEN_NAMES[(serial * 7) % len(GIVEN_NAMES)]}",
                            "id_card": id_card,
                            "mobile": mobile,
                            "email": f"patient{serial:04d}@yunzhen-clinic.cn",
                            "home_address": (
                                f"{CITIES[serial % len(CITIES)]}{ROADS[serial % len(ROADS)]}"
                                f"{serial % 200}号{serial % 8 + 1}栋{serial % 6 + 1}单元"
                                f"{serial % 30 + 1}0{serial % 9 + 1}室"
                            ),
                            "birth_date": birth,
                            "gender": gender,
                            "zip": zip_code,
                            "diagnosis": DIAGNOSES[(serial - 1) % len(DIAGNOSES)],
                            "visit_count": (serial * 7) % 13,
                        }
                    )
    return rows


def build_visits() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index in range(1, 2401):
        patient_serial = ((index * 37) % 800) + 1
        rows.append(
            {
                "visit_id": index,
                "patient_id": f"P{patient_serial:04d}",
                "visit_date": date(2026, 1, 1) + timedelta(days=(index * 11) % 300),
                "department": DEPARTMENTS[(index * 5) % len(DEPARTMENTS)],
                "doctor": DOCTOR_NAMES[(index * 3) % len(DOCTOR_NAMES)],
                "cost": round(35.5 + ((index * 17) % 400) * 1.25, 2),
            }
        )
    return rows


def build_labs() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index in range(1, 1201):
        visit_id = ((index * 13) % 2400) + 1
        patient_serial = ((visit_id * 37) % 800) + 1
        test_code, unit = TESTS[index % len(TESTS)]
        rows.append(
            {
                "lab_id": index,
                "visit_id": visit_id,
                "patient_id": f"P{patient_serial:04d}",
                "test_code": test_code,
                "result_value": round(1.5 + ((index * 29) % 180) * 0.37, 2),
                "unit": unit,
            }
        )
    return rows


RAW_INSERTS: list[tuple[str, str, list[dict[str, Any]]]] = [
    (
        "patients",
        f'INSERT INTO {settings.raw_schema}.patients '
        "(patient_id, name, id_card, mobile, email, home_address, birth_date, gender, zip, diagnosis, visit_count) "
        "VALUES (:patient_id, :name, :id_card, :mobile, :email, :home_address, :birth_date, :gender, :zip, :diagnosis, :visit_count) "
        "ON CONFLICT (patient_id) DO NOTHING",
        build_patients(),
    ),
    (
        "visits",
        f'INSERT INTO {settings.raw_schema}.visits '
        "(visit_id, patient_id, visit_date, department, doctor, cost) "
        "VALUES (:visit_id, :patient_id, :visit_date, :department, :doctor, :cost) "
        "ON CONFLICT (visit_id) DO NOTHING",
        build_visits(),
    ),
    (
        "labs",
        f'INSERT INTO {settings.raw_schema}.labs '
        "(lab_id, visit_id, patient_id, test_code, result_value, unit) "
        "VALUES (:lab_id, :visit_id, :patient_id, :test_code, :result_value, :unit) "
        "ON CONFLICT (lab_id) DO NOTHING",
        build_labs(),
    ),
]


def seed_raw_rows() -> None:
    with engine.begin() as conn:
        for table, sql, rows in RAW_INSERTS:
            before = conn.execute(text(f"SELECT count(*) FROM {settings.raw_schema}.{table}")).scalar_one()
            conn.execute(text(sql), rows)
            after = conn.execute(text(f"SELECT count(*) FROM {settings.raw_schema}.{table}")).scalar_one()
            if after > before:
                _created("ClinicRows", f"{table} (+{after - before})")
            else:
                _skipped("ClinicRows", f"{table} ({after})")


# ------------------------------------------------------------------ 账号 ----


def seed_users(db) -> dict[str, User]:
    users: dict[str, User] = {}
    for email, display_name, role, organization in DEMO_USERS:
        user = db.query(User).filter(User.email == email).one_or_none()
        if user is None:
            user = User(
                email=email,
                password_hash=hash_password(DEMO_PASSWORD),
                display_name=display_name,
                role=role,
                organization=organization,
                is_active=True,
            )
            db.add(user)
            db.flush()
            _created("User", email)
        else:
            _skipped("User", email)
        users[role] = user
    db.commit()
    return users


# ------------------------------------------------------------------ 数据集 ----


TABLE_DEFINITIONS: list[dict[str, Any]] = [
    {
        "table_name": "patients",
        "display_name": "患者主索引",
        "description": "挂号系统导出的患者主索引，含身份与联系信息，是脱敏审批的第一敏感源。",
        "business_domain": "患者主数据",
        "sensitivity_level": SensitivityLevel.CRITICAL.value,
        "owner_note": "身份证/手机号/地址为直接标识符；诊断属敏感属性，仅供去标识后科研使用。",
        "columns": [
            ("patient_id", "text", ColumnRole.NON_SENSITIVE.value, SensitivityLevel.LOW.value),
            ("name", "text", ColumnRole.DIRECT_ID.value, SensitivityLevel.CRITICAL.value),
            ("id_card", "text", ColumnRole.DIRECT_ID.value, SensitivityLevel.CRITICAL.value),
            ("mobile", "text", ColumnRole.DIRECT_ID.value, SensitivityLevel.HIGH.value),
            ("email", "text", ColumnRole.DIRECT_ID.value, SensitivityLevel.HIGH.value),
            ("home_address", "text", ColumnRole.DIRECT_ID.value, SensitivityLevel.HIGH.value),
            ("birth_date", "date", ColumnRole.QUASI_ID.value, SensitivityLevel.MEDIUM.value),
            ("gender", "text", ColumnRole.QUASI_ID.value, SensitivityLevel.LOW.value),
            ("zip", "text", ColumnRole.QUASI_ID.value, SensitivityLevel.MEDIUM.value),
            ("diagnosis", "text", ColumnRole.SENSITIVE.value, SensitivityLevel.CRITICAL.value),
            ("visit_count", "integer", ColumnRole.NON_SENSITIVE.value, SensitivityLevel.LOW.value),
        ],
    },
    {
        "table_name": "visits",
        "display_name": "就诊记录",
        "description": "2026 年门诊就诊流水，含科室、医生与费用，用于服务量分析。",
        "business_domain": "就诊服务",
        "sensitivity_level": SensitivityLevel.MEDIUM.value,
        "owner_note": "医生姓名为执业人员个人信息，导出前需抑制。",
        "columns": [
            ("visit_id", "bigint", ColumnRole.NON_SENSITIVE.value, SensitivityLevel.LOW.value),
            ("patient_id", "text", ColumnRole.QUASI_ID.value, SensitivityLevel.MEDIUM.value),
            ("visit_date", "date", ColumnRole.QUASI_ID.value, SensitivityLevel.MEDIUM.value),
            ("department", "text", ColumnRole.NON_SENSITIVE.value, SensitivityLevel.LOW.value),
            ("doctor", "text", ColumnRole.DIRECT_ID.value, SensitivityLevel.HIGH.value),
            ("cost", "numeric", ColumnRole.NON_SENSITIVE.value, SensitivityLevel.LOW.value),
        ],
    },
    {
        "table_name": "labs",
        "display_name": "检验结果",
        "description": "检验科结果明细，指标值本身不敏感，但结合就诊时间会放大重识别风险。",
        "business_domain": "检验检查",
        "sensitivity_level": SensitivityLevel.LOW.value,
        "owner_note": "指标值可开放；关联键 patient_id 需按准标识处理。",
        "columns": [
            ("lab_id", "bigint", ColumnRole.NON_SENSITIVE.value, SensitivityLevel.LOW.value),
            ("visit_id", "bigint", ColumnRole.NON_SENSITIVE.value, SensitivityLevel.LOW.value),
            ("patient_id", "text", ColumnRole.QUASI_ID.value, SensitivityLevel.MEDIUM.value),
            ("test_code", "text", ColumnRole.NON_SENSITIVE.value, SensitivityLevel.LOW.value),
            ("result_value", "numeric", ColumnRole.NON_SENSITIVE.value, SensitivityLevel.LOW.value),
            ("unit", "text", ColumnRole.NON_SENSITIVE.value, SensitivityLevel.LOW.value),
        ],
    },
]


def seed_tables(db) -> dict[str, DatasetTable]:
    tables: dict[str, DatasetTable] = {}
    for definition in TABLE_DEFINITIONS:
        table = db.query(DatasetTable).filter(DatasetTable.table_name == definition["table_name"]).one_or_none()
        if table is None:
            table = DatasetTable(
                schema_name=settings.raw_schema,
                table_name=definition["table_name"],
                display_name=definition["display_name"],
                description=definition["description"],
                business_domain=definition["business_domain"],
                row_count=raw_data_service.row_count(db, definition["table_name"]),
                column_count=len(definition["columns"]),
                sensitivity_level=definition["sensitivity_level"],
                owner_note=definition["owner_note"],
            )
            db.add(table)
            db.flush()
            _created("DatasetTable", definition["table_name"])
        else:
            _skipped("DatasetTable", definition["table_name"])
        tables[definition["table_name"]] = table

        for ordinal, (name, data_type, role, sensitivity) in enumerate(definition["columns"]):
            column = (
                db.query(DatasetColumn)
                .filter(DatasetColumn.table_id == table.id, DatasetColumn.name == name)
                .one_or_none()
            )
            if column is not None:
                _skipped("DatasetColumn", f"{definition['table_name']}.{name}")
                continue
            stats = raw_data_service.column_stats(db, definition["table_name"], name, 800)
            db.add(
                DatasetColumn(
                    table_id=table.id,
                    name=name,
                    data_type=data_type,
                    ordinal=ordinal,
                    column_role=role,
                    sensitivity_level=sensitivity,
                    null_ratio=stats["null_ratio"],
                    distinct_ratio=stats["distinct_ratio"],
                    sample_values_json=stats["samples"],
                )
            )
            _created("DatasetColumn", f"{definition['table_name']}.{name}")
    db.commit()
    return tables


# ------------------------------------------------------------------ 策略 ----


POLICY_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "身份证号 · 首尾保留掩码",
        "table": "patients",
        "column_pattern": "id_card",
        "pii_type": PIIType.ID_CARD.value,
        "method": MaskMethod.MASK.value,
        "params": {"keep_prefix": 4, "keep_suffix": 4, "mask_char": "*"},
        "description": "保留行政区前 4 位与后 4 位，保留可核对性，中间 10 位不可见。",
    },
    {
        "name": "手机号 · 号段保留掩码",
        "table": "patients",
        "column_pattern": "mobile",
        "pii_type": PIIType.MOBILE.value,
        "method": MaskMethod.MASK.value,
        "params": {"keep_prefix": 3, "keep_suffix": 4, "mask_char": "*"},
        "description": "保留运营商号段与尾号，便于回访核对，不暴露完整号码。",
    },
    {
        "name": "邮箱 · 加盐哈希假名",
        "table": "patients",
        "column_pattern": "email",
        "pii_type": PIIType.EMAIL.value,
        "method": MaskMethod.HASH.value,
        "params": {"digest_len": 16, "prefix": "E:"},
        "description": "sha256 + 项目盐，跨数据集可连接、不可逆推邮箱。",
    },
    {
        "name": "姓名 · 整值抑制",
        "table": "patients",
        "column_pattern": "name",
        "pii_type": PIIType.NAME.value,
        "method": MaskMethod.SUPPRESS.value,
        "params": {"replacement": "[姓名已抑制]"},
        "description": "科研分析不需要姓名，直接整值抑制，规避姓氏表推断风险。",
    },
    {
        "name": "地址 · 泛化到行政区",
        "table": "patients",
        "column_pattern": "home_address",
        "pii_type": PIIType.ADDRESS.value,
        "method": MaskMethod.GENERALIZE.value,
        "params": {"kind": "keep_prefix", "keep": 6},
        "description": "只保留到区县级前缀（成都市武侯区…），门牌与楼栋全部丢弃。",
    },
]


def seed_policies(db, admin: User, tables: dict[str, DatasetTable]) -> None:
    for definition in POLICY_DEFINITIONS:
        existing = db.query(MaskingPolicy).filter(MaskingPolicy.name == definition["name"]).one_or_none()
        if existing is not None:
            _skipped("MaskingPolicy", definition["name"])
            continue
        db.add(
            MaskingPolicy(
                name=definition["name"],
                table_id=tables[definition["table"]].id,
                column_pattern=definition["column_pattern"],
                pii_type=definition["pii_type"],
                method=definition["method"],
                params_json=definition["params"],
                description=definition["description"],
                is_active=True,
                created_by=admin.id,
            )
        )
        _created("MaskingPolicy", definition["name"])
    db.commit()


# ------------------------------------------------------------------ 扫描 ----


def seed_scans(db, tables: dict[str, DatasetTable]) -> None:
    for table in tables.values():
        if table.last_profiled_at is not None:
            _skipped("PIIScan", table.table_name)
            continue
        pii_detector.scan_table(db, table)
        _created("PIIScan", table.table_name)


# ------------------------------------------------------------------ k-匿名 ----


def seed_k_anonymity(db, dpo: User, tables: dict[str, DatasetTable]) -> None:
    table = tables["patients"]
    qi = ["birth_date", "gender", "zip"]
    existing = [
        check
        for check in db.query(KAnonymityCheck).filter(KAnonymityCheck.table_id == table.id).all()
        if [str(item) for item in check.quasi_identifiers_json] == qi
        and check.sensitive_column == "diagnosis"
        and check.target_k == 5
        and check.target_l == 2
    ]
    if existing:
        _skipped("KAnonymityCheck", "birth_date+gender+zip")
        return
    check = KAnonymityCheck(
        table_id=table.id,
        quasi_identifiers_json=qi,
        sensitive_column="diagnosis",
        target_k=5,
        target_l=2,
        status="running",
        created_by=dpo.id,
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    k_anonymity_service.execute_check(db, check)
    _created("KAnonymityCheck", "birth_date+gender+zip")
    print(
        f"SEED_KANON base_k={check.base_k} base_l={check.base_l} "
        f"final_k={check.final_k} final_l={check.final_l} passed={check.passed}",
        flush=True,
    )


# ------------------------------------------------------------------ 导出 ----


EXPORT_DEFINITIONS: list[dict[str, Any]] = [
    {
        "table": "patients",
        "dataset_version": "2026-10",
        "purpose": "2026Q4 糖尿病合并高血压队列研究，仅需去标识后的行级随访数据（已附伦理批件 YZ-2026-118）。",
        "requested_rows": 800,
        "status": ExportStatus.APPROVED.value,
        "reviewer": ROLE_DPO,
        "note": "用途与伦理批件齐全，按 5 条策略脱敏后放行。",
        "build": True,
        "created_at": datetime(2026, 11, 8, 10, 30, tzinfo=timezone.utc),
    },
    {
        "table": "patients",
        "dataset_version": "2026-11",
        "purpose": "心研所 11 月新增房颤患者用药依从性分析，需要去标识行级数据，不申请任何直接标识列。",
        "requested_rows": 800,
        "status": ExportStatus.PENDING.value,
        "reviewer": None,
        "note": "",
        "build": False,
        "created_at": datetime(2026, 11, 10, 9, 20, tzinfo=timezone.utc),
    },
    {
        "table": "visits",
        "dataset_version": "2026-09",
        "purpose": "就诊量月度报表复核，需要科室维度的量价汇总（原始明细）。",
        "requested_rows": 2400,
        "status": ExportStatus.REJECTED.value,
        "reviewer": ROLE_DPO,
        "note": "用途描述缺少伦理批件编号，且申请了含医生姓名的原始明细，请补充材料后重新提交。",
        "build": False,
        "created_at": datetime(2026, 11, 5, 15, 5, tzinfo=timezone.utc),
    },
]


def seed_exports(db, users: dict[str, User], tables: dict[str, DatasetTable]) -> None:
    for definition in EXPORT_DEFINITIONS:
        table = tables[definition["table"]]
        existing = (
            db.query(ExportRequest)
            .filter(
                ExportRequest.requester_id == users[ROLE_CLIENT].id,
                ExportRequest.table_id == table.id,
                ExportRequest.dataset_version == definition["dataset_version"],
                ExportRequest.purpose == definition["purpose"],
            )
            .one_or_none()
        )
        if existing is not None:
            _skipped("ExportRequest", f"{definition['table']}@{definition['dataset_version']}")
            if definition["build"] and existing.build_status != "done":
                existing.status = ExportStatus.APPROVED.value
                db.commit()
                export_service.build_export(db, str(existing.id))
            continue
        request = ExportRequest(
            requester_id=users[ROLE_CLIENT].id,
            table_id=table.id,
            purpose=definition["purpose"],
            requested_rows=definition["requested_rows"],
            dataset_version=definition["dataset_version"],
            status=definition["status"],
            build_status="idle",
            review_note=definition["note"],
            created_at=definition["created_at"],
        )
        if definition["reviewer"]:
            reviewer = users[definition["reviewer"]]
            request.reviewed_by = reviewer.id
            request.reviewed_at = definition["created_at"] + timedelta(hours=3)
        db.add(request)
        db.commit()
        db.refresh(request)
        _created("ExportRequest", f"{definition['table']}@{definition['dataset_version']}")
        if definition["build"]:
            export_service.build_export(db, str(request.id))


# ------------------------------------------------------------------ 审计 ----


AUDIT_DEFINITIONS: list[dict[str, Any]] = [
    ("dataset.scan", ROLE_DPO, "dataset_table", "patients", {"seeded": True, "findings": 5}),
    ("dataset.scan", ROLE_DPO, "dataset_table", "visits", {"seeded": True, "findings": 1}),
    ("dataset.scan", ROLE_DPO, "dataset_table", "labs", {"seeded": True, "findings": 0}),
    ("policy.create", ROLE_ADMIN, "masking_policy", "身份证号 · 首尾保留掩码", {"seeded": True}),
    ("policy.preview", ROLE_DPO, "masking_policy", "身份证号 · 首尾保留掩码", {"seeded": True}),
    ("export.submit", ROLE_CLIENT, "export_request", "2026-10", {"seeded": True}),
    ("export.approve", ROLE_DPO, "export_request", "2026-10", {"seeded": True}),
    ("export.reject", ROLE_DPO, "export_request", "2026-09", {"seeded": True}),
    ("kanon.check", ROLE_DPO, "k_anonymity_check", "birth_date+gender+zip", {"seeded": True}),
]


def seed_audit(db, users: dict[str, User]) -> None:
    base_time = datetime(2026, 11, 9, 8, 0, tzinfo=timezone.utc)
    for index, (action, role, entity_type, entity_id, detail) in enumerate(AUDIT_DEFINITIONS):
        exists = (
            db.query(AuditLog)
            .filter(
                AuditLog.action == action,
                AuditLog.entity_type == entity_type,
                AuditLog.entity_id == entity_id,
            )
            .count()
        )
        if exists:
            _skipped("AuditLog", f"{action}:{entity_id}")
            continue
        user = users[role]
        db.add(
            AuditLog(
                actor_id=user.id,
                actor_email=user.email,
                actor_role=user.role,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                detail_json=detail,
                ip="10.20.4.18",
                trace_id=f"seed-{index:02d}",
                created_at=base_time + timedelta(minutes=index * 7),
            )
        )
        _created("AuditLog", f"{action}:{entity_id}")
    db.commit()


# ------------------------------------------------------------------ 汇总 ----


SUMMARY_TABLES = [
    ("user", User),
    ("dataset_table", DatasetTable),
    ("dataset_column", DatasetColumn),
    ("pii_finding", PIIFinding),
    ("masking_policy", MaskingPolicy),
    ("export_request", ExportRequest),
    ("k_anonymity_check", KAnonymityCheck),
    ("audit_log", AuditLog),
]


def summary() -> dict[str, int]:
    result: dict[str, int] = {}
    with engine.connect() as conn:
        for key, model in SUMMARY_TABLES:
            result[key] = int(conn.execute(sa.select(sa.func.count()).select_from(model.__table__)).scalar_one())
        for table in ("patients", "visits", "labs"):
            result[f"clinic_{table}"] = int(
                conn.execute(text(f"SELECT count(*) FROM {settings.raw_schema}.{table}")).scalar_one()
            )
    return dict(sorted(result.items()))


def seed_all() -> dict[str, Any]:
    global CREATED, SKIPPED
    CREATED = 0
    SKIPPED = 0
    random.seed(RANDOM_SEED)

    seed_raw_rows()
    with session_scope() as db:
        users = seed_users(db)
        tables = seed_tables(db)
        seed_policies(db, users[ROLE_ADMIN], tables)
        seed_scans(db, tables)
        seed_k_anonymity(db, users[ROLE_DPO], tables)
        seed_exports(db, users, tables)
        seed_audit(db, users)

    counts = summary()
    print(f"SEED_SUMMARY {json.dumps(counts, ensure_ascii=False, separators=(',', ':'))}", flush=True)
    print(f"SEED_DONE created={CREATED} skipped={SKIPPED}", flush=True)
    return {"created": CREATED, "skipped": SKIPPED, "counts": counts}


def main() -> int:
    try:
        result = seed_all()
    except Exception as exc:  # noqa: BLE001
        print(f"SEED_FAILED reason={exc}", file=sys.stderr, flush=True)
        import traceback

        traceback.print_exc()
        return 1
    if result["created"] == 0 and result["skipped"] == 0:
        print("SEED_FAILED reason=nothing happened", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
