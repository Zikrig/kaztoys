"""Add persistent offset for search filters

Revision ID: 005
Revises: 004
Create Date: 2026-03-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("search_filters", sa.Column("offset", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("search_filters", "offset")
