"""add_timestamps_to_contracts

Revision ID: 693abebeafeb
Revises: 6f85506964fe
Create Date: 2026-06-01 15:02:46.078937

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '693abebeafeb'
down_revision: Union[str, None] = '6f85506964fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('contracts', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('contracts', sa.Column('updated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('contracts', 'updated_at')
    op.drop_column('contracts', 'created_at')
