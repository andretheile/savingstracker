"""Initial schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-09 20:58:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('timezone', sa.String(length=64), nullable=False, server_default='Europe/Berlin'),
        sa.Column('preferences', postgresql.JSONB(as_uuid=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
        sa.UniqueConstraint('telegram_id', name=op.f('uq_users_telegram_id'))
    )
    op.create_index(op.f('ix_users_telegram_id'), 'users', ['telegram_id'], unique=True)

    # 2. Accounts
    op.create_table(
        'accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('iban', sa.String(length=34), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='EUR'),
        sa.Column('initial_balance', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_accounts_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_accounts'))
    )
    op.create_index(op.f('ix_accounts_user_id'), 'accounts', ['user_id'], unique=False)

    # 3. Bank Connections
    op.create_table(
        'bank_connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bank_blz', sa.String(length=16), nullable=False),
        sa.Column('bank_name', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('fints_url', sa.String(length=512), nullable=False, server_default=''),
        sa.Column('login_name', sa.String(length=512), nullable=False),
        sa.Column('adapter_type', sa.String(length=32), nullable=False, server_default='fints'),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_status', sa.String(length=32), nullable=False, server_default='idle'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_bank_connections_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_bank_connections'))
    )
    op.create_index(op.f('ix_bank_connections_user_id'), 'bank_connections', ['user_id'], unique=False)

    # 4. Categories
    op.create_table(
        'categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('icon', sa.String(length=8), nullable=False, server_default='❓'),
        sa.Column('direction', sa.String(length=16), nullable=False, server_default='expense'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['categories.id'], name=op.f('fk_categories_parent_id_categories'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_categories_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_categories'))
    )
    op.create_index(op.f('ix_categories_user_id'), 'categories', ['user_id'], unique=False)

    # 5. Classification Rules
    op.create_table(
        'classification_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('field', sa.String(length=32), nullable=False),
        sa.Column('operator', sa.String(length=16), nullable=False),
        sa.Column('value', sa.String(length=512), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], name=op.f('fk_classification_rules_category_id_categories'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_classification_rules_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_classification_rules'))
    )
    op.create_index(op.f('ix_classification_rules_user_id'), 'classification_rules', ['user_id'], unique=False)

    # 6. Transactions
    op.create_table(
        'transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('bank_connection_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('value_date', sa.Date(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('counterparty', sa.String(length=512), nullable=False, server_default=''),
        sa.Column('reference', sa.String(length=512), nullable=False, server_default=''),
        sa.Column('import_hash', sa.String(length=64), nullable=True),
        sa.Column('is_manually_classified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], name=op.f('fk_transactions_account_id_accounts'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['bank_connection_id'], ['bank_connections.id'], name=op.f('fk_transactions_bank_connection_id_bank_connections'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], name=op.f('fk_transactions_category_id_categories'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_transactions')),
        sa.UniqueConstraint('import_hash', name=op.f('uq_transactions_import_hash'))
    )
    op.create_index('ix_transactions_account_date', 'transactions', ['account_id', 'transaction_date'], unique=False)
    op.create_index('ix_transactions_category', 'transactions', ['category_id'], unique=False)

    # 7. KPI Definitions
    op.create_table(
        'kpi_definitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('formula', sa.Text(), nullable=False),
        sa.Column('unit', sa.String(length=16), nullable=False, server_default='%'),
        sa.Column('period', sa.String(length=16), nullable=False, server_default='monthly'),
        sa.Column('required_variables', postgresql.JSONB(as_uuid=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_kpi_definitions_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_kpi_definitions'))
    )
    op.create_index(op.f('ix_kpi_definitions_user_id'), 'kpi_definitions', ['user_id'], unique=False)

    # 8. KPI Snapshots
    op.create_table(
        'kpi_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kpi_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('value', sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column('variable_values', postgresql.JSONB(as_uuid=True), nullable=True),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['kpi_id'], ['kpi_definitions.id'], name=op.f('fk_kpi_snapshots_kpi_id_kpi_definitions'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_kpi_snapshots_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_kpi_snapshots'))
    )

    # 9. Projection Configs
    op.create_table(
        'projection_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False, server_default='My Savings Goal'),
        sa.Column('annual_return_pct', sa.Numeric(precision=5, scale=2), nullable=False, server_default='7.0'),
        sa.Column('inflation_pct', sa.Numeric(precision=5, scale=2), nullable=False, server_default='2.0'),
        sa.Column('horizon_years', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('monthly_contribution', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('use_actual_savings', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_projection_configs_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_projection_configs'))
    )

    # 10. Projection Snapshots
    op.create_table(
        'projection_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('projection_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('computed_for_month', sa.Date(), nullable=False),
        sa.Column('current_savings_rate', sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column('monthly_contribution', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('projected_value_nominal', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('projected_value_real', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('scenarios', postgresql.JSONB(as_uuid=True), nullable=True),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['projection_id'], ['projection_configs.id'], name=op.f('fk_projection_snapshots_projection_id_projection_configs'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_projection_snapshots_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_projection_snapshots'))
    )

    # 11. Monthly Reports
    op.create_table(
        'monthly_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('report_month', sa.Date(), nullable=False),
        sa.Column('report_data', postgresql.JSONB(as_uuid=True), nullable=False),
        sa.Column('sent_via_telegram', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_monthly_reports_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_monthly_reports'))
    )


def downgrade() -> None:
    op.drop_table('monthly_reports')
    op.drop_table('projection_snapshots')
    op.drop_table('projection_configs')
    op.drop_table('kpi_snapshots')
    op.drop_table('kpi_definitions')
    op.drop_table('transactions')
    op.drop_table('classification_rules')
    op.drop_table('categories')
    op.drop_table('bank_connections')
    op.drop_table('accounts')
    op.drop_table('users')
