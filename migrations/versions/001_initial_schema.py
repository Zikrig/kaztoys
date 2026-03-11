"""Initial schema: users, listings, responses, matches, subscriptions, search_filters

Revision ID: 001
Revises:
Create Date: 2025-03-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("first_name", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("confirmed_deals", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("referral_from_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["referral_from_id"], ["users.id"], name="users_referral_from_id_fkey"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)
    op.create_index("ix_users_referral_from_id", "users", ["referral_from_id"], unique=False)

    op.create_table(
        "listings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("photo_file_id", sa.String(255), nullable=True),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("age_group", sa.String(50), nullable=False),
        sa.Column("district", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="listings_user_id_fkey"),
    )
    op.create_index("ix_listings_code", "listings", ["code"], unique=True)
    op.create_index("ix_listings_user_id", "listings", ["user_id"], unique=False)
    op.create_index("ix_listings_status", "listings", ["status"], unique=False)
    op.create_index("ix_listings_created_at", "listings", ["created_at"], unique=False)
    op.create_index(
        "ix_listings_search",
        "listings",
        ["status", "category", "age_group", "district", "created_at"],
        unique=False,
    )

    op.create_table(
        "responses",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("listing_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("photo_file_id", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("chosen", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], name="responses_listing_id_fkey"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="responses_user_id_fkey"),
    )
    op.create_index("ix_responses_code", "responses", ["code"], unique=True)
    op.create_index("ix_responses_listing_id", "responses", ["listing_id"], unique=False)
    op.create_index("ix_responses_user_id", "responses", ["user_id"], unique=False)
    op.create_index("ix_responses_chosen", "responses", ["chosen"], unique=False)

    op.create_table(
        "matches",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("listing_id", sa.BigInteger(), nullable=False),
        sa.Column("response_id", sa.BigInteger(), nullable=False),
        sa.Column("listing_owner_id", sa.BigInteger(), nullable=False),
        sa.Column("response_owner_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("listing_owner_confirmed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("response_owner_confirmed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], name="matches_listing_id_fkey"),
        sa.ForeignKeyConstraint(["response_id"], ["responses.id"], name="matches_response_id_fkey"),
        sa.ForeignKeyConstraint(["listing_owner_id"], ["users.id"], name="matches_listing_owner_id_fkey"),
        sa.ForeignKeyConstraint(["response_owner_id"], ["users.id"], name="matches_response_owner_id_fkey"),
    )
    op.create_index("ix_matches_listing_id", "matches", ["listing_id"], unique=False)
    op.create_index("ix_matches_response_id", "matches", ["response_id"], unique=True)
    op.create_index("ix_matches_listing_owner_id", "matches", ["listing_owner_id"], unique=False)
    op.create_index("ix_matches_response_owner_id", "matches", ["response_owner_id"], unique=False)
    op.create_index("ix_matches_status", "matches", ["status"], unique=False)

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="subscriptions_user_id_fkey"),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=False)
    op.create_index("ix_subscriptions_expires_at", "subscriptions", ["expires_at"], unique=False)

    op.create_table(
        "search_filters",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("age_group", sa.String(50), nullable=True),
        sa.Column("district", sa.String(100), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("user_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="search_filters_user_id_fkey"),
    )


def downgrade() -> None:
    op.drop_table("search_filters")
    op.drop_table("subscriptions")
    op.drop_table("matches")
    op.drop_table("responses")
    op.drop_table("listings")
    op.drop_table("users")
