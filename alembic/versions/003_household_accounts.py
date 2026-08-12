"""Mark which accounts count toward household cashflow

Revision ID: 003_household_accounts
Revises: 002_exclude_from_totals
Create Date: 2026-08-12 20:50:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "003_household_accounts"
down_revision = "002_exclude_from_totals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column(
            "include_in_household",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("accounts", "include_in_household")
