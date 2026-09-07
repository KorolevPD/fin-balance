"""Add scope column to ai_advices.

Revision ID: 009
Revises: 008
Create Date: 2026-09-08 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '009'
down_revision: Union[str, None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'ai_advices',
        sa.Column(
            'scope',
            sa.String(20),
            nullable=False,
            server_default='family',
        ),
    )


def downgrade() -> None:
    op.drop_column('ai_advices', 'scope')
