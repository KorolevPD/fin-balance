"""Add BotLink table

Revision ID: 002
Revises: 001
Create Date: 2026-09-05 07:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bot_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(16), unique=True, nullable=False),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id'),
            nullable=False,
        ),
        sa.Column('telegram_id', sa.String(255), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_bot_links_code', 'bot_links', ['code'])


def downgrade() -> None:
    op.drop_index('ix_bot_links_code', table_name='bot_links')
    op.drop_table('bot_links')
