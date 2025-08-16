"""Add signal fingerprints table

Revision ID: 8fc5ad5d2292
Revises: d1d7660fbd4b
Create Date: 2025-08-14 14:01:18.958144

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "8fc5ad5d2292"
down_revision = "d1d7660fbd4b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create signal fingerprints table
    op.create_table(
        "signal_fingerprints",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("signal_hash", sa.String(length=16), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("strategy", sa.String(length=50), nullable=False),
        sa.Column("timestamp_minute", sa.BigInteger(), nullable=False),
        sa.Column("signal_strength", sa.Float(), nullable=True),
        sa.Column("price_level", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("signal_hash", name="uq_signal_fingerprints_hash"),
    )

    # Create indexes for performance
    op.create_index("idx_signal_fingerprints_symbol", "signal_fingerprints", ["symbol"])
    op.create_index("idx_signal_fingerprints_created_at", "signal_fingerprints", ["created_at"])
    op.create_index("idx_signal_fingerprints_strategy", "signal_fingerprints", ["strategy"])
    op.create_index(
        "idx_signal_fingerprints_symbol_direction", "signal_fingerprints", ["symbol", "direction"]
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_signal_fingerprints_symbol_direction", table_name="signal_fingerprints")
    op.drop_index("idx_signal_fingerprints_strategy", table_name="signal_fingerprints")
    op.drop_index("idx_signal_fingerprints_created_at", table_name="signal_fingerprints")
    op.drop_index("idx_signal_fingerprints_symbol", table_name="signal_fingerprints")

    # Drop table
    op.drop_table("signal_fingerprints")
