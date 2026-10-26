"""Ensure all user_preferences guardrails columns exist idempotently

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-26 16:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    try:
        insp = sa.inspect(bind)
        tables = insp.get_table_names()
    except Exception:
        tables = []
        insp = None

    if "user_preferences" in tables and insp:
        pref_cols = {c["name"] for c in insp.get_columns("user_preferences")}
    else:
        pref_cols = set()

    columns_to_add = [
        ("automation_paused", sa.Column("automation_paused", sa.Boolean(), server_default=sa.false(), nullable=False)),
        ("automation_mode", sa.Column("automation_mode", sa.String(length=50), server_default="draft_only", nullable=False)),
        ("daily_reply_limit", sa.Column("daily_reply_limit", sa.Integer(), server_default=sa.text("20"), nullable=False)),
        ("min_confidence_score", sa.Column("min_confidence_score", sa.Integer(), server_default=sa.text("85"), nullable=False)),
        ("sender_allowlist", sa.Column("sender_allowlist", sa.JSON(), nullable=True)),
        ("sender_blocklist", sa.Column("sender_blocklist", sa.JSON(), nullable=True)),
        ("job_title", sa.Column("job_title", sa.String(length=255), nullable=True)),
        ("company", sa.Column("company", sa.String(length=255), nullable=True)),
        ("timezone", sa.Column("timezone", sa.String(length=100), server_default="UTC", nullable=False)),
        ("custom_instructions", sa.Column("custom_instructions", sa.Text(), nullable=True)),
    ]

    for col_name, col_def in columns_to_add:
        if col_name not in pref_cols:
            op.add_column("user_preferences", col_def)


def downgrade() -> None:
    bind = op.get_bind()
    try:
        insp = sa.inspect(bind)
        tables = insp.get_table_names()
    except Exception:
        tables = []
        insp = None

    if "user_preferences" in tables and insp:
        pref_cols = {c["name"] for c in insp.get_columns("user_preferences")}
        for col in [
            "custom_instructions", "timezone", "company", "job_title",
            "sender_blocklist", "sender_allowlist", "min_confidence_score",
            "daily_reply_limit", "automation_mode", "automation_paused"
        ]:
            if col in pref_cols:
                op.drop_column("user_preferences", col)
