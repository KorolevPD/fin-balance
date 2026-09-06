"""Remove family name.

Revision ID: 006
Revises: 005
Create Date: 2026-09-06 03:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('families', 'name')


def downgrade() -> None:
    op.add_column(
        'families',
        sa.Column('name', sa.String(255), nullable=False, server_default='Моя семья'),
    )
