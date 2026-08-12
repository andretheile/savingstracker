"""Add exclude_from_totals on transactions

Revision ID: 002_exclude_from_totals
Revises: 001_initial_schema
Create Date: 2026-08-12 20:40:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "002_exclude_from_totals"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column(
            "exclude_from_totals",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("transactions", "exclude_from_totals")
