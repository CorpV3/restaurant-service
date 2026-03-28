"""Baseline — existing schema already created via create_all

Revision ID: f1e2d3c4b5a6
Revises:
Create Date: 2026-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'f1e2d3c4b5a6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Baseline: tables already exist (created via SQLAlchemy create_all).
    # This revision just marks the starting point for future migrations.
    pass


def downgrade() -> None:
    pass
