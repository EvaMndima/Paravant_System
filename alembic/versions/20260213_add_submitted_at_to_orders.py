"""Add submitted_at column to orders table

Revision ID: b7c2d4e6f8a1
Revises: a3f9b82c1e45
Create Date: 2026-02-13 10:00:00.000000

Adds submitted_at timestamp field to track when an order was
submitted to the exchange. Also fixes filled_at to be timezone-aware.

Decision: DEC-2026-02-08-003 (timezone-aware timestamps)
Phase: 4A (Execution Infrastructure)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c2d4e6f8a1'
down_revision = 'a3f9b82c1e45'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add submitted_at column to orders table."""
    op.add_column(
        'orders',
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    """Remove submitted_at column from orders table."""
    op.drop_column('orders', 'submitted_at')
