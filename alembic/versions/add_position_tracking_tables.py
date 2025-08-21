"""Add position tracking tables

Revision ID: add_position_tracking_tables
Revises:
Create Date: 2025-08-20 11:45:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "add_position_tracking_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add tables for enhanced position tracking"""

    # Таблица для отслеживания позиций
    op.create_table(
        "tracked_positions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("position_id", sa.String(50), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("size", sa.Numeric(18, 8), nullable=False),
        sa.Column("entry_price", sa.Numeric(18, 8), nullable=False),
        sa.Column("current_price", sa.Numeric(18, 8), nullable=True, default=0),
        sa.Column("stop_loss", sa.Numeric(18, 8), nullable=True),
        sa.Column("take_profit", sa.Numeric(18, 8), nullable=True),
        sa.Column("exchange", sa.String(20), nullable=False, default="bybit"),
        sa.Column("status", sa.String(20), nullable=False, default="active"),
        sa.Column("health", sa.String(20), nullable=False, default="unknown"),
        sa.Column("unrealized_pnl", sa.Numeric(18, 8), nullable=True, default=0),
        sa.Column("realized_pnl", sa.Numeric(18, 8), nullable=True, default=0),
        sa.Column("roi_percent", sa.Numeric(10, 4), nullable=True, default=0),
        sa.Column("hold_time_minutes", sa.Integer(), nullable=True, default=0),
        sa.Column("max_profit", sa.Numeric(18, 8), nullable=True, default=0),
        sa.Column("max_drawdown", sa.Numeric(18, 8), nullable=True, default=0),
        sa.Column("health_score", sa.Float(), nullable=True, default=1.0),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("position_id", name="uq_tracked_positions_position_id"),
    )

    # Индексы для оптимизации запросов
    op.create_index("ix_tracked_positions_symbol", "tracked_positions", ["symbol"])
    op.create_index("ix_tracked_positions_status", "tracked_positions", ["status"])
    op.create_index("ix_tracked_positions_health", "tracked_positions", ["health"])
    op.create_index("ix_tracked_positions_created_at", "tracked_positions", ["created_at"])

    # Таблица для истории метрик позиций
    op.create_table(
        "position_metrics_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("position_id", sa.String(50), nullable=False),
        sa.Column(
            "timestamp", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("current_price", sa.Numeric(18, 8), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(18, 8), nullable=False),
        sa.Column("roi_percent", sa.Numeric(10, 4), nullable=False),
        sa.Column("health_score", sa.Float(), nullable=False),
        sa.Column("volume_24h", sa.Numeric(18, 8), nullable=True),
        sa.Column("volatility", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Индексы для истории метрик
    op.create_index(
        "ix_position_metrics_history_position_id", "position_metrics_history", ["position_id"]
    )
    op.create_index(
        "ix_position_metrics_history_timestamp", "position_metrics_history", ["timestamp"]
    )

    # Таблица для системных алертов
    op.create_table(
        "position_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("position_id", sa.String(50), nullable=False),
        sa.Column("alert_type", sa.String(20), nullable=False),  # critical, warning, info
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False, default=1),  # 1-5
        sa.Column("is_resolved", sa.Boolean(), nullable=False, default=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Индексы для алертов
    op.create_index("ix_position_alerts_position_id", "position_alerts", ["position_id"])
    op.create_index("ix_position_alerts_alert_type", "position_alerts", ["alert_type"])
    op.create_index("ix_position_alerts_is_resolved", "position_alerts", ["is_resolved"])
    op.create_index("ix_position_alerts_created_at", "position_alerts", ["created_at"])


def downgrade() -> None:
    """Remove position tracking tables"""

    # Удаляем таблицы в обратном порядке
    op.drop_table("position_alerts")
    op.drop_table("position_metrics_history")
    op.drop_table("tracked_positions")
