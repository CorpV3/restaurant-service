"""Add delivery integration and partner/tier fields to restaurants

Revision ID: 005
Revises: 004
Create Date: 2026-04-17

Adds columns that existed in the SQLAlchemy model but were never migrated:
- Delivery integrations: Uber Eats, JustEat, Deliveroo
- Partner/Tier: tier, billing_model, monthly_charge, partner_id,
  commission_type, commission_value
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Delivery integrations
    op.add_column('restaurants', sa.Column('uber_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('restaurants', sa.Column('uber_store_id', sa.String(255), nullable=True))
    op.add_column('restaurants', sa.Column('justeat_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('restaurants', sa.Column('justeat_restaurant_id', sa.String(255), nullable=True))
    op.add_column('restaurants', sa.Column('deliveroo_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('restaurants', sa.Column('deliveroo_restaurant_id', sa.String(255), nullable=True))

    # Partner & Tier
    op.add_column('restaurants', sa.Column('tier', sa.String(20), nullable=False, server_default='enterprise'))
    op.add_column('restaurants', sa.Column('billing_model', sa.String(20), nullable=False, server_default='per_booking'))
    op.add_column('restaurants', sa.Column('monthly_charge', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('restaurants', sa.Column('partner_id', UUID(as_uuid=True), nullable=True))
    op.add_column('restaurants', sa.Column('commission_type', sa.String(20), nullable=True))
    op.add_column('restaurants', sa.Column('commission_value', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('restaurants', 'commission_value')
    op.drop_column('restaurants', 'commission_type')
    op.drop_column('restaurants', 'partner_id')
    op.drop_column('restaurants', 'monthly_charge')
    op.drop_column('restaurants', 'billing_model')
    op.drop_column('restaurants', 'tier')
    op.drop_column('restaurants', 'deliveroo_restaurant_id')
    op.drop_column('restaurants', 'deliveroo_enabled')
    op.drop_column('restaurants', 'justeat_restaurant_id')
    op.drop_column('restaurants', 'justeat_enabled')
    op.drop_column('restaurants', 'uber_store_id')
    op.drop_column('restaurants', 'uber_enabled')
