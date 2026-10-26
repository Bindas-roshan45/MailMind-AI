"""Add email_signatures, processed_message_logs, and user_preferences guardrails

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-26 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
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

    # 1. Create email_signatures table if not exists
    if "email_signatures" not in tables:
        op.create_table(
            "email_signatures",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("sender_name", sa.String(length=255), nullable=False),
            sa.Column("job_title", sa.String(length=255), nullable=True),
            sa.Column("company", sa.String(length=255), nullable=True),
            sa.Column("sign_off", sa.String(length=100), server_default="Best regards", nullable=False),
            sa.Column("custom_sign_off", sa.String(length=255), nullable=True),
            sa.Column("phone", sa.String(length=50), nullable=True),
            sa.Column("content_html", sa.Text(), nullable=True),
            sa.Column("content_text", sa.Text(), nullable=False),
            sa.Column("is_default_new", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("is_default_reply", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        )
        op.create_index(op.f("ix_email_signatures_id"), "email_signatures", ["id"], unique=False)
        op.create_index(op.f("ix_email_signatures_user_id"), "email_signatures", ["user_id"], unique=False)

    # 2. Create processed_message_logs table if not exists
    if "processed_message_logs" not in tables:
        op.create_table(
            "processed_message_logs",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("message_id", sa.String(length=255), nullable=False),
            sa.Column("thread_id", sa.String(length=255), nullable=True),
            sa.Column("action_taken", sa.String(length=50), nullable=False),
            sa.Column("rule_id", sa.Integer(), sa.ForeignKey("auto_reply_rules.id", ondelete="SET NULL"), nullable=True),
            sa.Column("reason", sa.String(length=500), nullable=True),
            sa.Column("reply_message_id", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index(op.f("ix_processed_message_logs_id"), "processed_message_logs", ["id"], unique=False)
        op.create_index(op.f("ix_processed_message_logs_user_id"), "processed_message_logs", ["user_id"], unique=False)
        op.create_index(op.f("ix_processed_message_logs_message_id"), "processed_message_logs", ["message_id"], unique=False)
        op.create_index(op.f("ix_processed_message_logs_thread_id"), "processed_message_logs", ["thread_id"], unique=False)

    # 3. Add safety and profile columns to user_preferences if not exists
    if insp:
        pref_cols = {c["name"] for c in insp.get_columns("user_preferences")} if "user_preferences" in tables else set()
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

    if "processed_message_logs" in tables:
        op.drop_table("processed_message_logs")

    if "email_signatures" in tables:
        op.drop_table("email_signatures")

    if "user_preferences" in tables:
        pref_cols = {c["name"] for c in insp.get_columns("user_preferences")}
        for col in [
            "custom_instructions", "timezone", "company", "job_title",
            "sender_blocklist", "sender_allowlist", "min_confidence_score",
            "daily_reply_limit", "automation_mode", "automation_paused"
        ]:
            if col in pref_cols:
                op.drop_column("user_preferences", col)

