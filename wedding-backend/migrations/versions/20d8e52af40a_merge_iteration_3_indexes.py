"""merge iteration 3 indexes

Revision ID: 20d8e52af40a
Revises: a1b2c3d4e5f6, f7a8b9c0d1e2
Create Date: 2026-05-29 20:26:56.982267

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20d8e52af40a'
down_revision: Union[str, None] = ('a1b2c3d4e5f6', 'f7a8b9c0d1e2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
