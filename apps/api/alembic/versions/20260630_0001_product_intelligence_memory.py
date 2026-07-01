"""Create product-intelligence memory tables.

Revision ID: 20260630_0001
Revises:
Create Date: 2026-06-30
"""

from __future__ import annotations

from alembic import op

from marketing_agent.infrastructure.database.models import Base

revision = "20260630_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
