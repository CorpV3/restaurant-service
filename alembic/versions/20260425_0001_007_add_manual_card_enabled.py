"""Add manual_card_enabled to restaurants

Revision ID: 007
Revises: 006
Create Date: 2026-04-25
"""
from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('restaurants', sa.Column('manual_card_enabled', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('restaurants', 'manual_card_enabled')
