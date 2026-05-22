"""add iteration 3 performance indexes

Revision ID: a1b2c3d4e5f6
Revises: ee2ac8e4af0d
Create Date: 2026-05-22 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'ee2ac8e4af0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # customers indexes
    op.create_index('ix_customers_status', 'customers', ['status'])
    op.create_index('ix_customers_assigned_sale', 'customers', ['assigned_sale_id'])
    op.create_index('ix_customers_source', 'customers', ['source_id'])

    # orders indexes
    op.create_index('ix_orders_status', 'orders', ['status'])
    op.create_index('ix_orders_sale_id', 'orders', ['sale_id'])
    op.create_index('ix_orders_planner_id', 'orders', ['planner_id'])

    # events indexes
    op.create_index('ix_events_date', 'events', ['date'])
    op.create_index('ix_events_status', 'events', ['status'])
    op.create_index('ix_events_planner_id', 'events', ['planner_id'])

    # approvals indexes
    op.create_index('ix_approvals_status', 'approvals', ['status'])

    # operation_logs indexes
    op.create_index('ix_operation_logs_user_id', 'operation_logs', ['user_id'])
    op.create_index('ix_operation_logs_module', 'operation_logs', ['module'])


def downgrade() -> None:
    # operation_logs indexes
    op.drop_index('ix_operation_logs_module', table_name='operation_logs')
    op.drop_index('ix_operation_logs_user_id', table_name='operation_logs')

    # approvals indexes
    op.drop_index('ix_approvals_status', table_name='approvals')

    # events indexes
    op.drop_index('ix_events_planner_id', table_name='events')
    op.drop_index('ix_events_status', table_name='events')
    op.drop_index('ix_events_date', table_name='events')

    # orders indexes
    op.drop_index('ix_orders_planner_id', table_name='orders')
    op.drop_index('ix_orders_sale_id', table_name='orders')
    op.drop_index('ix_orders_status', table_name='orders')

    # customers indexes
    op.drop_index('ix_customers_source', table_name='customers')
    op.drop_index('ix_customers_assigned_sale', table_name='customers')
    op.drop_index('ix_customers_status', table_name='customers')
