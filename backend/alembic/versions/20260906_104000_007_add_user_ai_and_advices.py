"""Add user AI fields and AiAdvice table.

Revision ID: 007
Revises: 006
Create Date: 2026-09-06 10:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('ai_provider', sa.String(50), nullable=True))
    op.add_column(
        'users', sa.Column('ai_api_key_encrypted', sa.Text(), nullable=True)
    )
    op.add_column('users', sa.Column('ai_base_url', sa.String(255), nullable=True))
    op.create_table(
        'ai_advices',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'family_id',
            UUID(as_uuid=True),
            sa.ForeignKey('families.id'),
            nullable=False,
        ),
        sa.Column(
            'user_id',
            UUID(as_uuid=True),
            sa.ForeignKey('users.id'),
            nullable=False,
        ),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('provider', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('ai_advices')
    op.drop_column('users', 'ai_base_url')
    op.drop_column('users', 'ai_api_key_encrypted')
    op.drop_column('users', 'ai_provider')
