"""Add payment provider fields to restaurants table

Revision ID: 004
Revises: 003
Create Date: 2026-04-14 00:01:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Worldpay triPOS Cloud
    op.add_column('restaurants', sa.Column('tripos_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('restaurants', sa.Column('tripos_acceptor_id', sa.String(255), nullable=True))
    op.add_column('restaurants', sa.Column('tripos_account_id', sa.String(255), nullable=True))
    op.add_column('restaurants', sa.Column('tripos_account_token', sa.String(500), nullable=True))
    op.add_column('restaurants', sa.Column('tripos_application_id', sa.String(255), nullable=True))
    op.add_column('restaurants', sa.Column('tripos_lane_id', sa.Integer(), nullable=True))
    op.add_column('restaurants', sa.Column('tripos_environment', sa.String(10), nullable=True, server_default='cert'))
    # Stripe
    op.add_column('restaurants', sa.Column('stripe_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('restaurants', sa.Column('stripe_secret_key', sa.String(500), nullable=True))
    # SumUp
    op.add_column('restaurants', sa.Column('sumup_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('restaurants', sa.Column('sumup_api_key', sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column('restaurants', 'sumup_api_key')
    op.drop_column('restaurants', 'sumup_enabled')
    op.drop_column('restaurants', 'stripe_secret_key')
    op.drop_column('restaurants', 'stripe_enabled')
    op.drop_column('restaurants', 'tripos_environment')
    op.drop_column('restaurants', 'tripos_lane_id')
    op.drop_column('restaurants', 'tripos_application_id')
    op.drop_column('restaurants', 'tripos_account_token')
    op.drop_column('restaurants', 'tripos_account_id')
    op.drop_column('restaurants', 'tripos_acceptor_id')
    op.drop_column('restaurants', 'tripos_enabled')
