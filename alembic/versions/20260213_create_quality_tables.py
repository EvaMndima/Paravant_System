"""Create execution quality tracking tables

Revision ID: d9e4f6a8b3c5
Revises: c8d3e5f7a2b4
Create Date: 2026-02-13 14:30:00.000000

Creates slippage_records and fill_rate_records tables for execution
quality monitoring. These tables support the SlippageTracker and
FillRateTracker classes in quality.py.

Phase: 4B (Position Tracking & Execution Quality)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd9e4f6a8b3c5'
down_revision = 'c8d3e5f7a2b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create slippage_records and fill_rate_records tables."""
    op.create_table(
        'slippage_records',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('order_id', sa.String(), sa.ForeignKey('orders.id'), nullable=False, index=True),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('side', sa.String(10), nullable=False),
        sa.Column('expected_price', sa.Float(), nullable=False),
        sa.Column('actual_price', sa.Float(), nullable=False),
        sa.Column('slippage_pct', sa.Float(), nullable=False),
        sa.Column('slippage_bps', sa.Float(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'fill_rate_records',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('order_id', sa.String(), sa.ForeignKey('orders.id'), nullable=False, index=True),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('order_type', sa.String(20), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('filled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('time_to_fill_seconds', sa.Float(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    """Drop execution quality tables."""
    op.drop_table('fill_rate_records')
    op.drop_table('slippage_records')
