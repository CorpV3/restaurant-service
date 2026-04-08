"""Add app_announcements and app_versions system tables

Revision ID: 003
Revises: 002
Create Date: 2026-04-08 00:01:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'app_announcements',
        sa.Column('id', sa.String(36), primary_key=True, server_default=sa.text('gen_random_uuid()::text')),
        sa.Column('message', sa.String(500), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'app_versions',
        sa.Column('id', sa.String(36), primary_key=True, server_default=sa.text('gen_random_uuid()::text')),
        sa.Column('platform', sa.String(20), nullable=False, unique=True),
        sa.Column('version_string', sa.String(50), nullable=False),
        sa.Column('download_url', sa.String(1000), nullable=False),
        sa.Column('release_notes', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('app_versions')
    op.drop_table('app_announcements')
