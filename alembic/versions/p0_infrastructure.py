"""Add P0 infrastructure tables: audit_events, user_role_assignments, compliance_rules, compliance_violations

Revision ID: p0_infrastructure
Revises: add_user_id_stock_groups
Create Date: 2026-06-13

P0 Survival: RBAC persistence, audit trail, compliance pre-check
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'p0_infrastructure'
down_revision = 'add_user_id_stock_groups'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. audit_events table
    op.create_table(
        'audit_events',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('snapshot_id', sa.String(64), unique=True, nullable=False, index=True),
        sa.Column('order_id', sa.String(64), nullable=False, index=True),
        sa.Column('user_id', sa.Integer(), nullable=False, index=True),
        sa.Column('symbol', sa.String(32), nullable=False, index=True),
        sa.Column('action', sa.String(16), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('price', sa.Double(), nullable=False),
        sa.Column('ai_evidence_json', sa.Text(), server_default='{}'),
        sa.Column('factor_values_json', sa.Text(), server_default='{}'),
        sa.Column('risk_assessment_json', sa.Text(), server_default='{}'),
        sa.Column('compliance_result_json', sa.Text(), server_default='{}'),
        sa.Column('timestamp', sa.String(64), server_default='', index=True),
        sa.Column('previous_hash', sa.String(64), server_default='genesis'),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('chain_hash', sa.String(64), nullable=False),
    )

    # 2. user_role_assignments table
    op.create_table(
        'user_role_assignments',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), nullable=False, unique=True, index=True),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('scope', sa.String(32), server_default='global'),
        sa.Column('assigned_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('assigned_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], ),
    )

    # 3. compliance_rules table
    op.create_table(
        'compliance_rules',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('rule_code', sa.String(64), unique=True, nullable=False, index=True),
        sa.Column('rule_type', sa.String(32), nullable=False),
        sa.Column('target', sa.String(128), server_default='*'),
        sa.Column('limit_value', sa.Double(), server_default='0'),
        sa.Column('enabled', sa.SmallInteger(), server_default='1'),
        sa.Column('description', sa.String(256), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # 4. compliance_violations table
    op.create_table(
        'compliance_violations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('rule_id', sa.Integer(), nullable=False, index=True),
        sa.Column('order_id', sa.String(64), nullable=False, index=True),
        sa.Column('user_id', sa.Integer(), nullable=False, index=True),
        sa.Column('symbol', sa.String(32), nullable=False, index=True),
        sa.Column('violation_detail', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), index=True),
        sa.ForeignKeyConstraint(['rule_id'], ['compliance_rules.id'], ),
    )

    # 5. Add permissions_json column to roles table
    op.add_column('roles', sa.Column('permissions_json', sa.Text(), server_default='{}'))


def downgrade() -> None:
    op.drop_column('roles', 'permissions_json')
    op.drop_table('compliance_violations')
    op.drop_table('compliance_rules')
    op.drop_table('user_role_assignments')
    op.drop_table('audit_events')
