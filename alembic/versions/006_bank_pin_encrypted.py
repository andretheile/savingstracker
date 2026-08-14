"""Store encrypted bank PIN for chat and /sync refreshes

Revision ID: 006_bank_pin_encrypted
Revises: 005_auth_household
Create Date: 2026-08-14 21:30:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "006_bank_pin_encrypted"
down_revision = "005_auth_household"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bank_connections", sa.Column("pin_encrypted", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("bank_connections", "pin_encrypted")
