"""导出合规门禁：export_requests 落门禁结论，k_anonymity_checks 落数据签名。

Revision ID: 0002_export_gate
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

from src.config.settings import settings

revision = "0002_export_gate"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

META = settings.meta_schema


def upgrade() -> None:
    op.add_column(
        "export_requests",
        sa.Column("gate_status", sa.String(20), server_default="unchecked", nullable=False),
        schema=META,
    )
    op.add_column(
        "export_requests",
        sa.Column("gate_gaps_json", JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
        schema=META,
    )
    op.add_column(
        "export_requests",
        sa.Column("gate_fingerprint", sa.String(64), nullable=True),
        schema=META,
    )
    op.add_column(
        "export_requests",
        sa.Column("gate_snapshot_json", JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        schema=META,
    )
    op.add_column(
        "export_requests",
        sa.Column("gate_checked_at", sa.DateTime(timezone=True), nullable=True),
        schema=META,
    )
    op.add_column(
        "k_anonymity_checks",
        sa.Column("data_signature", sa.String(64), nullable=True),
        schema=META,
    )


def downgrade() -> None:
    op.drop_column("k_anonymity_checks", "data_signature", schema=META)
    op.drop_column("export_requests", "gate_checked_at", schema=META)
    op.drop_column("export_requests", "gate_snapshot_json", schema=META)
    op.drop_column("export_requests", "gate_fingerprint", schema=META)
    op.drop_column("export_requests", "gate_gaps_json", schema=META)
    op.drop_column("export_requests", "gate_status", schema=META)
