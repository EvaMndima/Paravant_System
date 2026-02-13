"""Add unique constraint to strategy_assignments

Revision ID: a3f9b82c1e45
Revises: d16d72af193e
Create Date: 2026-02-09 14:30:00.000000

Adds unique constraint on (account_id, strategy_id) to prevent
duplicate strategy assignments to the same account.

Business Rule: One strategy instance per account
Decision: DEC-2026-02-09-001 (data integrity)

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3f9b82c1e45'
down_revision = 'd16d72af193e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add unique constraint to strategy_assignments table."""
    # Create unique constraint on (account_id, strategy_id)
    op.create_unique_constraint(
        'uq_strategy_assignments_account_strategy',
        'strategy_assignments',
        ['account_id', 'strategy_id']
    )


def downgrade() -> None:
    """Remove unique constraint from strategy_assignments table."""
    op.drop_constraint(
        'uq_strategy_assignments_account_strategy',
        'strategy_assignments',
        type_='unique'
    )
