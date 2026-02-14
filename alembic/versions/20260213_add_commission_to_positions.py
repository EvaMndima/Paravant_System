"""Add commission_paid column to positions table

Revision ID: c8d3e5f7a2b4
Revises: b7c2d4e6f8a1
Create Date: 2026-02-13 14:00:00.000000

Adds commission_paid field to track accumulated trading commissions
per position. Required for accurate P&L calculations (Critical
Invariant #3: P&L must always include commission).

Decision: DEC-2026-02-08-007 (input validation at model layer)
Phase: 4B (Position Tracking & Execution Quality)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c8d3e5f7a2b4'
down_revision = 'b7c2d4e6f8a1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add commission_paid column to positions table."""
    op.add_column(
        'positions',
        sa.Column('commission_paid', sa.Float(), nullable=False, server_default='0.0')
    )


def downgrade() -> None:
    """Remove commission_paid column from positions table."""
    op.drop_column('positions', 'commission_paid')
