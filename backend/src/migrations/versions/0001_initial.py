"""初始化 meta（平台元数据）与 clinic（上游业务库原始表）。

Revision ID: 0001_initial
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from src.config.settings import settings
from src.models import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

META = settings.meta_schema
CLINIC = settings.raw_schema

RAW_DDL = f"""
CREATE TABLE IF NOT EXISTS {CLINIC}.patients (
    patient_id   text PRIMARY KEY,
    name         text NOT NULL,
    id_card      text NOT NULL,
    mobile       text NOT NULL,
    email        text NOT NULL,
    home_address text NOT NULL,
    birth_date   date NOT NULL,
    gender       text NOT NULL,
    zip          text NOT NULL,
    diagnosis    text NOT NULL,
    visit_count  integer NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS {CLINIC}.visits (
    visit_id    bigint PRIMARY KEY,
    patient_id  text NOT NULL,
    visit_date  date NOT NULL,
    department  text NOT NULL,
    doctor      text NOT NULL,
    cost        numeric(10,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS {CLINIC}.labs (
    lab_id       bigint PRIMARY KEY,
    visit_id     bigint NOT NULL,
    patient_id   text NOT NULL,
    test_code    text NOT NULL,
    result_value numeric(10,2),
    unit         text
);

CREATE INDEX IF NOT EXISTS idx_visits_patient ON {CLINIC}.visits (patient_id);
CREATE INDEX IF NOT EXISTS idx_labs_patient ON {CLINIC}.labs (patient_id);
CREATE INDEX IF NOT EXISTS idx_labs_visit ON {CLINIC}.labs (visit_id);
"""


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {META}")
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {CLINIC}")

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)

    for statement in [part.strip() for part in RAW_DDL.split(";") if part.strip()]:
        op.execute(sa.text(statement))


def downgrade() -> None:
    op.execute(f"DROP SCHEMA IF EXISTS {CLINIC} CASCADE")
    op.execute(f"DROP SCHEMA IF EXISTS {META} CASCADE")
