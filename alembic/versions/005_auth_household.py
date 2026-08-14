"""Auth identities, household invites, and per-household bot/LLM secrets

Revision ID: 005_auth_household
Revises: 003_household_accounts
Create Date: 2026-08-13 20:40:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "005_auth_household"
down_revision = "004_depot_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("telegram_bot_token_encrypted", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("telegram_bot_username", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("telegram_bot_name", sa.String(length=255), nullable=True))
    op.add_column(
        "users",
        sa.Column("telegram_allowed_user_ids", sa.String(length=512), nullable=False, server_default=""),
    )
    op.add_column(
        "users",
        sa.Column("telegram_allowed_chat_ids", sa.String(length=512), nullable=False, server_default=""),
    )
    op.add_column("users", sa.Column("openrouter_api_key_encrypted", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("openrouter_model", sa.String(length=128), nullable=True))

    op.create_table(
        "auth_identities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("google_sub", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("picture", sa.String(length=1024), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_auth_identities_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_auth_identities"),
        sa.UniqueConstraint("email", name="uq_auth_identities_email"),
        sa.UniqueConstraint("google_sub", name="uq_auth_identities_google_sub"),
    )
    op.create_index("ix_auth_identities_user_id", "auth_identities", ["user_id"])
    op.create_index("ix_auth_identities_email", "auth_identities", ["email"])

    op.create_table(
        "household_invites",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("invited_by_email", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_household_invites_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_household_invites"),
        sa.UniqueConstraint("email", name="uq_household_invites_email"),
    )
    op.create_index("ix_household_invites_user_id", "household_invites", ["user_id"])
    op.create_index("ix_household_invites_email", "household_invites", ["email"])


def downgrade() -> None:
    op.drop_index("ix_household_invites_email", table_name="household_invites")
    op.drop_index("ix_household_invites_user_id", table_name="household_invites")
    op.drop_table("household_invites")
    op.drop_index("ix_auth_identities_email", table_name="auth_identities")
    op.drop_index("ix_auth_identities_user_id", table_name="auth_identities")
    op.drop_table("auth_identities")
    op.drop_column("users", "openrouter_model")
    op.drop_column("users", "openrouter_api_key_encrypted")
    op.drop_column("users", "telegram_allowed_chat_ids")
    op.drop_column("users", "telegram_allowed_user_ids")
    op.drop_column("users", "telegram_bot_name")
    op.drop_column("users", "telegram_bot_username")
    op.drop_column("users", "telegram_bot_token_encrypted")
