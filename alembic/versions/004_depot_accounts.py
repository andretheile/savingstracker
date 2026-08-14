"""Mark which accounts are a securities depot

Revision ID: 004_depot_accounts
Revises: 003_household_accounts
Create Date: 2026-08-12 22:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "004_depot_accounts"
down_revision = "003_household_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column(
            "is_depot",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("accounts", "is_depot")
