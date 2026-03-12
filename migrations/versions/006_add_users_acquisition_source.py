"""Add acquisition_source for users

Revision ID: 006
Revises: 005
Create Date: 2026-03-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("acquisition_source", sa.String(length=32), nullable=False, server_default="other"),
    )


def downgrade() -> None:
    op.drop_column("users", "acquisition_source")
