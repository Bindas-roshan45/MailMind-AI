"""add nullable hashed_password on users

Revision ID: a1b2c3d4e5f6
Revises: 6f92c4c42425
Create Date: 2026-10-14 15:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "6f92c4c42425"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add optional password hash without touching existing user rows."""
    op.add_column("users", sa.Column("hashed_password", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "hashed_password")
