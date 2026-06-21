"""Add user_id to stock_groups and stock_group_items for user isolation

Revision ID: add_user_id_stock_groups
Revises:
Create Date: 2024-04-30

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_user_id_stock_groups'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 为 stock_groups 表添加 user_id 列
    op.add_column('stock_groups', sa.Column('user_id', sa.Integer(), nullable=False, server_default='1'))
    # 为 stock_group_items 表添加 user_id 列
    op.add_column('stock_group_items', sa.Column('user_id', sa.Integer(), nullable=False, server_default='1'))

    # 创建索引以提高查询性能
    op.create_index('ix_stock_groups_user_id', 'stock_groups', ['user_id'])
    op.create_index('ix_stock_group_items_user_id', 'stock_group_items', ['user_id'])
    op.create_index('ix_stock_groups_user_id_name', 'stock_groups', ['user_id', 'name'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_stock_groups_user_id_name', table_name='stock_groups')
    op.drop_index('ix_stock_group_items_user_id', table_name='stock_group_items')
    op.drop_index('ix_stock_groups_user_id', table_name='stock_groups')
    op.drop_column('stock_group_items', 'user_id')
    op.drop_column('stock_groups', 'user_id')