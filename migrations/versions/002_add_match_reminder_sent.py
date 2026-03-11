"""Add reminder_sent to matches for 24h confirmation reminder

Revision ID: 002
Revises: 001
Create Date: 2025-03-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("reminder_sent", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("matches", "reminder_sent")
