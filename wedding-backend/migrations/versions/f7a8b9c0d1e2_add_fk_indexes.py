"""Add FK indexes for performance optimization

Revision ID: f7a8b9c0d1e2_add_fk_indexes
Revises: ee2ac8e4af0d
Create Date: 2026-05-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "ee2ac8e4af0d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Indexes for event_resources table
    op.create_index(
        "ix_event_resources_event_id",
        "event_resources",
        ["event_id"],
        unique=False,
    )

    # Indexes for follow_ups table
    op.create_index(
        "ix_follow_ups_customer_id",
        "follow_ups",
        ["customer_id"],
        unique=False,
    )
    op.create_index(
        "ix_follow_ups_sale_id",
        "follow_ups",
        ["sale_id"],
        unique=False,
    )

    # Indexes for order_items table
    op.create_index(
        "ix_order_items_order_id",
        "order_items",
        ["order_id"],
        unique=False,
    )

    # Indexes for payments table
    op.create_index(
        "ix_payments_order_id",
        "payments",
        ["order_id"],
        unique=False,
    )

    # Indexes for staff_schedules table
    op.create_index(
        "ix_staff_schedules_event_id",
        "staff_schedules",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        "ix_staff_schedules_staff_id",
        "staff_schedules",
        ["staff_id"],
        unique=False,
    )
    op.create_index(
        "ix_staff_schedules_date",
        "staff_schedules",
        ["date"],
        unique=False,
    )

    # Indexes for supplier_evaluations table
    op.create_index(
        "ix_supplier_evaluations_supplier_id",
        "supplier_evaluations",
        ["supplier_id"],
        unique=False,
    )

    # Indexes for supplier_services table
    op.create_index(
        "ix_supplier_services_supplier_id",
        "supplier_services",
        ["supplier_id"],
        unique=False,
    )


def downgrade() -> None:
    # Drop indexes in reverse order
    op.drop_index("ix_supplier_services_supplier_id", table_name="supplier_services")
    op.drop_index("ix_supplier_evaluations_supplier_id", table_name="supplier_evaluations")
    op.drop_index("ix_staff_schedules_date", table_name="staff_schedules")
    op.drop_index("ix_staff_schedules_staff_id", table_name="staff_schedules")
    op.drop_index("ix_staff_schedules_event_id", table_name="staff_schedules")
    op.drop_index("ix_payments_order_id", table_name="payments")
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_index("ix_follow_ups_sale_id", table_name="follow_ups")
    op.drop_index("ix_follow_ups_customer_id", table_name="follow_ups")
    op.drop_index("ix_event_resources_event_id", table_name="event_resources")