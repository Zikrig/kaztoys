"""Add reports, hidden authors, and blacklist fields

Revision ID: 004
Revises: 003
Create Date: 2026-03-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("users", sa.Column("blocked_reason", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("blocked_by_admin_id", sa.BigInteger(), nullable=True))
    op.add_column("users", sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_is_blocked", "users", ["is_blocked"], unique=False)

    op.create_table(
        "reports",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("reporter_user_id", sa.BigInteger(), nullable=False),
        sa.Column("target_user_id", sa.BigInteger(), nullable=False),
        sa.Column("listing_id", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("admin_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], name="reports_listing_id_fkey"),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"], name="reports_reporter_user_id_fkey"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], name="reports_target_user_id_fkey"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_reporter_user_id", "reports", ["reporter_user_id"], unique=False)
    op.create_index("ix_reports_target_user_id", "reports", ["target_user_id"], unique=False)
    op.create_index("ix_reports_listing_id", "reports", ["listing_id"], unique=False)
    op.create_index("ix_reports_reason", "reports", ["reason"], unique=False)
    op.create_index("ix_reports_status", "reports", ["status"], unique=False)

    op.create_table(
        "hidden_authors",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("hidden_user_id", sa.BigInteger(), nullable=False),
        sa.Column("report_id", sa.BigInteger(), nullable=True),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["hidden_user_id"], ["users.id"], name="hidden_authors_hidden_user_id_fkey"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], name="hidden_authors_report_id_fkey"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="hidden_authors_user_id_fkey"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "hidden_user_id", "reason", name="uq_hidden_authors_user_hidden_reason"),
    )
    op.create_index("ix_hidden_authors_user_id", "hidden_authors", ["user_id"], unique=False)
    op.create_index("ix_hidden_authors_hidden_user_id", "hidden_authors", ["hidden_user_id"], unique=False)
    op.create_index("ix_hidden_authors_report_id", "hidden_authors", ["report_id"], unique=False)
    op.create_index("ix_hidden_authors_reason", "hidden_authors", ["reason"], unique=False)


def downgrade() -> None:
    op.drop_table("hidden_authors")
    op.drop_table("reports")
    op.drop_index("ix_users_is_blocked", table_name="users")
    op.drop_column("users", "blocked_at")
    op.drop_column("users", "blocked_by_admin_id")
    op.drop_column("users", "blocked_reason")
    op.drop_column("users", "is_blocked")
