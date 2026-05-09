"""Add POS feature toggles: chef display and auto-print

Revision ID: 006
Revises: 005
Create Date: 2026-04-23

Adds per-restaurant POS feature flags:
- chef_display_enabled: show/hide the KDS (Kitchen Display System) in the POS app
- auto_print_enabled: auto-print kitchen ticket when a new order comes in
- auto_print_copies: number of copies to print (default 1)
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('restaurants', sa.Column('chef_display_enabled', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('restaurants', sa.Column('auto_print_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('restaurants', sa.Column('auto_print_copies', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    op.drop_column('restaurants', 'auto_print_copies')
    op.drop_column('restaurants', 'auto_print_enabled')
    op.drop_column('restaurants', 'chef_display_enabled')
