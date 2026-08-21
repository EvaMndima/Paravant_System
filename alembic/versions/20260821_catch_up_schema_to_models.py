"""Catch the migration chain up to the ORM models

Revision ID: 621b6ee74fd9
Revises: e2f8a1c7d9b6
Create Date: 2026-08-21

Four objects existed in `src/data/models/` and in no migration:

  paper_trading_sessions   table   -- where live AND paper trading persist state
  symbols                  table
  ix_symbols_symbol        index
  signals.symbol           column

None of this was noticed for six months, because no runtime invokes Alembic --
every path calls `Base.metadata.create_all()` -- and nothing compared the two
schemas. The chain additionally aborted at revision two of six on SQLite until
DEC-2026-08-21-004 switched that revision to batch mode, so the drift could not
even be measured.

`paper_trading_sessions` is the notable one. Despite the name, it is the table
`scripts/run_live_trading.py` writes live position state to, keyed by a
`live_` session-id prefix. A database built from this chain rather than from
`create_all()` would have had no table for live trading to write to.

Generated with `alembic revision --autogenerate` against a database migrated to
`e2f8a1c7d9b6`, then adjusted: `signals.symbol` is added through batch mode with
a temporary server default, because `ALTER TABLE ... ADD COLUMN NOT NULL` with
no default fails against a table that already holds rows, and SQLite cannot add
a NOT NULL column without one at all.

Decision: DEC-2026-08-21-005
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '621b6ee74fd9'
down_revision: Union[str, Sequence[str], None] = 'e2f8a1c7d9b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the two missing tables, the missing index and the missing column."""
    op.create_table(
        'paper_trading_sessions',
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('template_id', sa.String(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('initial_capital', sa.Float(), nullable=False),
        sa.Column('cash', sa.Float(), nullable=False),
        sa.Column('position_data', sa.JSON(), nullable=True),
        sa.Column('trade_log', sa.JSON(), nullable=False),
        sa.Column('equity_curve', sa.JSON(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('total_trades', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('session_id'),
    )

    op.create_table(
        'symbols',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('base_asset', sa.String(length=10), nullable=False),
        sa.Column('quote_asset', sa.String(length=10), nullable=False),
        sa.Column('min_quantity', sa.Float(), nullable=False),
        sa.Column('max_quantity', sa.Float(), nullable=False),
        sa.Column('step_size', sa.Float(), nullable=False),
        sa.Column('tick_size', sa.Float(), nullable=False),
        sa.Column('min_price', sa.Float(), nullable=True),
        sa.Column('max_price', sa.Float(), nullable=True),
        sa.Column('min_notional', sa.Float(), nullable=False),
        sa.Column('is_trading', sa.Boolean(), nullable=False),
        sa.Column('is_spot_trading_allowed', sa.Boolean(), nullable=False),
        sa.Column('is_margin_trading_allowed', sa.Boolean(), nullable=False),
        sa.Column('filters', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_symbols_symbol'), 'symbols', ['symbol'], unique=True)

    # A temporary server default so existing rows get a value. Dropped
    # immediately afterwards so the column matches the model, which declares no
    # default -- leaving it would be a difference the comparison test reports.
    with op.batch_alter_table('signals', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('symbol', sa.String(length=20), nullable=False, server_default=''),
        )
    with op.batch_alter_table('signals', schema=None) as batch_op:
        batch_op.alter_column('symbol', server_default=None)


def downgrade() -> None:
    """Reverse the above, in dependency order."""
    with op.batch_alter_table('signals', schema=None) as batch_op:
        batch_op.drop_column('symbol')

    op.drop_index(op.f('ix_symbols_symbol'), table_name='symbols')
    op.drop_table('symbols')
    op.drop_table('paper_trading_sessions')
