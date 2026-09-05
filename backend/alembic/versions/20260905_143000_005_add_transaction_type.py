"""Add type column to transactions

Revision ID: 005
Revises: 004
Create Date: 2026-09-05 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'transactions',
        sa.Column('type', sa.String(20), nullable=False, server_default='expense'),
    )


def downgrade() -> None:
    op.drop_column('transactions', 'type')
