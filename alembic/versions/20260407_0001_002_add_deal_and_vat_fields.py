"""Add deal fields to menu_items and VAT fields to restaurants

Revision ID: 002
Revises: f1e2d3c4b5a6
Create Date: 2026-04-07 00:01:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = '002'
down_revision: Union[str, None] = 'f1e2d3c4b5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Deal fields on menu_items
    op.add_column('menu_items', sa.Column('is_deal', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('menu_items', sa.Column('deal_components', JSONB(), nullable=True))

    # VAT fields on restaurants
    op.add_column('restaurants', sa.Column('vat_enabled', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('restaurants', sa.Column('vat_rate', sa.Float(), nullable=False, server_default='20.0'))
    op.add_column('restaurants', sa.Column('vat_number', sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column('menu_items', 'deal_components')
    op.drop_column('menu_items', 'is_deal')
    op.drop_column('restaurants', 'vat_number')
    op.drop_column('restaurants', 'vat_rate')
    op.drop_column('restaurants', 'vat_enabled')
