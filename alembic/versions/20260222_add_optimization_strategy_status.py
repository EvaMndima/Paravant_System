"""Add OPTIMIZATION value to strategystatus enum.

Revision ID: e2f8a1c7d9b6
Revises: d9e4f6a8b3c5
Create Date: 2026-02-22 00:00:00.000000

Adds the OPTIMIZATION lifecycle status to the StrategyStatus enum
per PRD §3.5. Strategies can transition:
  UNDERPERFORMING -> OPTIMIZATION -> LIVE|PAUSED|RETIRED

Decision: DEC-2026-02-22-002 - Underperformance auto-transition (PRD §3.5)

SQLite note: SQLAlchemy stores enums as VARCHAR strings in SQLite, so
no DDL change is required for development databases. The ALTER TYPE
below is only executed on PostgreSQL (production).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e2f8a1c7d9b6'
down_revision = 'd9e4f6a8b3c5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add OPTIMIZATION to strategystatus enum (PostgreSQL only)."""
    # Detect the dialect to skip DDL for SQLite
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        # PostgreSQL requires an explicit ALTER TYPE to add enum values.
        # This must be done outside a transaction on older PostgreSQL versions;
        # on PostgreSQL 12+ it is safe inside a transaction.
        op.execute(
            "ALTER TYPE strategystatus ADD VALUE IF NOT EXISTS 'optimization'"
        )

    # SQLite stores enums as VARCHAR — no DDL change needed.
    # The Python StrategyStatus enum already has OPTIMIZATION = "optimization".


def downgrade() -> None:
    """Revert OPTIMIZATION status addition.

    PostgreSQL does not support removing values from an ENUM type without
    recreating the type. For downgrade safety, we only attempt this on
    PostgreSQL by renaming rows away from the value first.

    WARNING: Any strategies in OPTIMIZATION status must be manually
    transitioned before downgrading.
    """
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        # Move any OPTIMIZATION strategies to PAUSED before removing the value
        op.execute(
            "UPDATE strategies SET status = 'paused', "
            "status_reason = 'Downgraded from optimization status' "
            "WHERE status = 'optimization'"
        )
        # PostgreSQL 10+ does not support DROP VALUE; full type recreation needed.
        # Recreating the type is complex and risky — document instead.
        # For a real downgrade, use pg_dump/restore to recreate the type.
        pass
