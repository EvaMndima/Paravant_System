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


# revision identifiers, used by Alembic.
revision = 'a3f9b82c1e45'
down_revision = 'd16d72af193e'
branch_labels = None
depends_on = None


CONSTRAINT_NAME = 'uq_strategy_assignments_account_strategy'


def upgrade() -> None:
    """Add unique constraint to strategy_assignments table.

    Uses ``batch_alter_table`` because SQLite cannot ALTER a constraint into an
    existing table -- it raises::

        NotImplementedError: No support for ALTER of constraints in SQLite
        dialect. Please refer to the batch mode feature.

    Batch mode is the documented answer: it recreates the table with the
    constraint and copies the rows. On PostgreSQL it emits a plain
    ``ALTER TABLE ... ADD CONSTRAINT`` and costs nothing.

    This migration had never been applied anywhere. No runtime invoked Alembic
    -- every path called ``Base.metadata.create_all()`` -- so the chain stopped
    at this revision, on this line, and the four revisions after it never ran.
    Nothing compared the migrated schema to the models, so nothing said so.
    Editing a migration in place is normally wrong; it is safe here precisely
    because no database in existence has this revision stamped.

    Decision: DEC-2026-08-21-004
    """
    with op.batch_alter_table('strategy_assignments', schema=None) as batch_op:
        batch_op.create_unique_constraint(
            CONSTRAINT_NAME,
            ['account_id', 'strategy_id'],
        )


def downgrade() -> None:
    """Remove unique constraint from strategy_assignments table."""
    with op.batch_alter_table('strategy_assignments', schema=None) as batch_op:
        batch_op.drop_constraint(CONSTRAINT_NAME, type_='unique')
