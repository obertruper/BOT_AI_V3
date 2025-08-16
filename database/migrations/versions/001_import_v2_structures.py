"""Import v2 data structures and compatibility fields.

Revision ID: 001_import_v2
Revises:
Create Date: 2025-01-30
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "001_import_v2"
down_revision = "3dcf72ea81e3"
branch_labels = None
depends_on = None


def upgrade():
    """Добавляет поля совместимости с v2 и новые таблицы."""

    # Получаем инспектор для проверки существующих колонок
    import os

    from sqlalchemy import create_engine, inspect

    # Строим DATABASE_URL из переменных окружения
    DATABASE_URL = f"postgresql://{os.getenv('PGUSER', 'obertruper')}:{os.getenv('PGPASSWORD', '')}@:{os.getenv('PGPORT', '5555')}/{os.getenv('PGDATABASE', 'bot_trading_v3')}"
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)

    # Проверяем и добавляем поля ML из v2 в таблицу trades
    trades_columns = [col["name"] for col in inspector.get_columns("trades")]
    if "model_name" not in trades_columns:
        op.add_column("trades", sa.Column("model_name", sa.String(100), nullable=True))
    if "model_score" not in trades_columns:
        op.add_column("trades", sa.Column("model_score", sa.Float(), nullable=True))
    if "profit_probability" not in trades_columns:
        op.add_column("trades", sa.Column("profit_probability", sa.Float(), nullable=True))
    if "loss_probability" not in trades_columns:
        op.add_column("trades", sa.Column("loss_probability", sa.Float(), nullable=True))
    if "confidence" not in trades_columns:
        op.add_column("trades", sa.Column("confidence", sa.Float(), nullable=True))
    if "session_id" not in trades_columns:
        op.add_column("trades", sa.Column("session_id", sa.String(100), nullable=True))

    # Проверяем и добавляем поля для SL/TP ордеров в orders
    orders_columns = [col["name"] for col in inspector.get_columns("orders")]
    if "trigger_by" not in orders_columns:
        op.add_column("orders", sa.Column("trigger_by", sa.String(50), nullable=True))
    if "sl_trigger_price" not in orders_columns:
        op.add_column("orders", sa.Column("sl_trigger_price", sa.Float(), nullable=True))
    if "tp_trigger_price" not in orders_columns:
        op.add_column("orders", sa.Column("tp_trigger_price", sa.Float(), nullable=True))
    if "sl_order_id" not in orders_columns:
        op.add_column("orders", sa.Column("sl_order_id", sa.String(100), nullable=True))
    if "tp_order_id" not in orders_columns:
        op.add_column("orders", sa.Column("tp_order_id", sa.String(100), nullable=True))

    # Проверяем и добавляем поля в signals для совместимости
    signals_columns = [col["name"] for col in inspector.get_columns("signals")]
    # indicators уже существует как JSON, проверяем ml_predictions и processing_time
    if "ml_predictions" not in signals_columns:
        op.add_column("signals", sa.Column("ml_predictions", postgresql.JSONB(), nullable=True))
    if "processing_time" not in signals_columns:
        op.add_column("signals", sa.Column("processing_time", sa.Float(), nullable=True))

    # Проверяем существующие таблицы
    existing_tables = inspector.get_table_names()

    # Создаем таблицы для истории Bybit (из v2)
    if "bybit_trade_history" not in existing_tables:
        op.create_table(
            "bybit_trade_history",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("symbol", sa.String(50), nullable=False),
            sa.Column("order_id", sa.String(100), nullable=False, unique=True),
            sa.Column("order_link_id", sa.String(100)),
            sa.Column("side", sa.String(10), nullable=False),
            sa.Column("price", sa.Float(), nullable=False),
            sa.Column("qty", sa.Float(), nullable=False),
            sa.Column("fee", sa.Float(), default=0.0),
            sa.Column("fee_currency", sa.String(20)),
            sa.Column("order_type", sa.String(50)),
            sa.Column("stop_order_type", sa.String(50)),
            sa.Column("created_time", sa.DateTime(), nullable=False),
            sa.Column("updated_time", sa.DateTime()),
            sa.Column("is_maker", sa.Boolean(), default=False),
            sa.Column("reduce_only", sa.Boolean(), default=False),
            sa.Column("close_on_trigger", sa.Boolean(), default=False),
            sa.Column("cum_exec_qty", sa.Float()),
            sa.Column("cum_exec_value", sa.Float()),
            sa.Column("cum_exec_fee", sa.Float()),
            sa.Column("trigger_price", sa.Float()),
            sa.Column("trigger_by", sa.String(50)),
            sa.Column("imported_at", sa.DateTime(), server_default=sa.func.now()),
        )

    if "bybit_positions" not in existing_tables:
        op.create_table(
            "bybit_positions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("symbol", sa.String(50), nullable=False),
            sa.Column("side", sa.String(10), nullable=False),
            sa.Column("size", sa.Float(), nullable=False),
            sa.Column("position_value", sa.Float()),
            sa.Column("entry_price", sa.Float()),
            sa.Column("mark_price", sa.Float()),
            sa.Column("liq_price", sa.Float()),
            sa.Column("bust_price", sa.Float()),
            sa.Column("leverage", sa.Float()),
            sa.Column("position_status", sa.String(50)),
            sa.Column("adl_rank_indicator", sa.Integer()),
            sa.Column("position_idx", sa.Integer(), default=0),
            sa.Column("position_mm", sa.Float()),
            sa.Column("position_im", sa.Float()),
            sa.Column("take_profit", sa.Float()),
            sa.Column("stop_loss", sa.Float()),
            sa.Column("trailing_stop", sa.Float()),
            sa.Column("unrealised_pnl", sa.Float()),
            sa.Column("cum_realised_pnl", sa.Float()),
            sa.Column("created_time", sa.DateTime()),
            sa.Column("updated_time", sa.DateTime()),
            sa.Column("snapshot_time", sa.DateTime(), server_default=sa.func.now()),
        )

    if "bybit_wallet_balance" not in existing_tables:
        op.create_table(
            "bybit_wallet_balance",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("account_type", sa.String(50), nullable=False),
            sa.Column("coin", sa.String(20), nullable=False),
            sa.Column("wallet_balance", sa.Float(), nullable=False),
            sa.Column("available_balance", sa.Float()),
            sa.Column("bonus", sa.Float(), default=0.0),
            sa.Column("equity", sa.Float()),
            sa.Column("cum_realised_pnl", sa.Float()),
            sa.Column("unrealised_pnl", sa.Float()),
            sa.Column("total_order_im", sa.Float()),
            sa.Column("total_position_im", sa.Float()),
            sa.Column("total_position_mm", sa.Float()),
            sa.Column("snapshot_time", sa.DateTime(), server_default=sa.func.now()),
        )

    if "bybit_closed_pnl" not in existing_tables:
        op.create_table(
            "bybit_closed_pnl",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("symbol", sa.String(50), nullable=False),
            sa.Column("order_id", sa.String(100), nullable=False),
            sa.Column("side", sa.String(10), nullable=False),
            sa.Column("qty", sa.Float(), nullable=False),
            sa.Column("closed_size", sa.Float()),
            sa.Column("avg_entry_price", sa.Float()),
            sa.Column("avg_exit_price", sa.Float()),
            sa.Column("closed_pnl", sa.Float(), nullable=False),
            sa.Column("fill_count", sa.Integer()),
            sa.Column("leverage", sa.Float()),
            sa.Column("created_time", sa.DateTime(), nullable=False),
            sa.Column("updated_time", sa.DateTime()),
        )

    # Создаем таблицу для хранения сессий торговли (из v2)
    if "trading_sessions" not in existing_tables:
        op.create_table(
            "trading_sessions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("session_id", sa.String(100), nullable=False, unique=True),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("ended_at", sa.DateTime()),
            sa.Column("status", sa.String(50), default="active"),
            sa.Column("total_trades", sa.Integer(), default=0),
            sa.Column("profitable_trades", sa.Integer(), default=0),
            sa.Column("total_pnl", sa.Float(), default=0.0),
            sa.Column("max_drawdown", sa.Float(), default=0.0),
            sa.Column("win_rate", sa.Float()),
            sa.Column("config_snapshot", postgresql.JSONB()),
            sa.Column("error_count", sa.Integer(), default=0),
            sa.Column("last_error", sa.Text()),
            sa.Column("metadata", postgresql.JSONB()),
        )

    # Создаем таблицу SLTP Orders (отсутствует в v3)
    if "sltp_orders" not in existing_tables:
        op.create_table(
            "sltp_orders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("trade_id", sa.Integer(), nullable=False),
            sa.Column("symbol", sa.String(50), nullable=False),
            sa.Column("side", sa.String(10), nullable=False),
            sa.Column("stop_loss_price", sa.Float()),
            sa.Column("take_profit_price", sa.Float()),
            sa.Column("sl_order_id", sa.String(100)),
            sa.Column("tp_order_id", sa.String(100)),
            sa.Column("status", sa.String(50), server_default="pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("attempts", sa.Integer(), server_default="0"),
            sa.Column("sl_trigger_by", sa.String(50), server_default="LastPrice"),
            sa.Column("tp_trigger_by", sa.String(50), server_default="LastPrice"),
            sa.Column("trailing_stop", sa.Boolean(), server_default="false"),
            sa.Column("trailing_stop_price", sa.Float()),
            sa.Column("trailing_stop_activation_price", sa.Float()),
            sa.Column("trailing_callback", sa.Float()),
            sa.Column("is_breakeven", sa.Boolean(), server_default="false"),
            sa.Column("partial_close_ratio", sa.Float()),
            sa.Column("partial_close_trigger", sa.Float()),
            sa.Column("original_stop_loss", sa.Float()),
            sa.Column("original_take_profit", sa.Float()),
            sa.Column("error_message", sa.Text()),
            sa.Column("extra_data", postgresql.JSONB()),
        )

    # Создаем индексы для оптимизации
    if "bybit_trade_history" in existing_tables:
        op.create_index("idx_bybit_trade_order_id", "bybit_trade_history", ["order_id"])
        op.create_index(
            "idx_bybit_trade_symbol_time",
            "bybit_trade_history",
            ["symbol", "created_time"],
        )
    if "bybit_positions" in existing_tables:
        op.create_index("idx_bybit_positions_symbol", "bybit_positions", ["symbol"])
    if "bybit_closed_pnl" in existing_tables:
        op.create_index(
            "idx_bybit_closed_pnl_symbol",
            "bybit_closed_pnl",
            ["symbol", "created_time"],
        )
    if "trading_sessions" in existing_tables:
        op.create_index("idx_trading_sessions_id", "trading_sessions", ["session_id"])
    if "sltp_orders" in existing_tables:
        op.create_index("idx_sltp_orders_trade_id", "sltp_orders", ["trade_id"])
        op.create_index("idx_sltp_orders_symbol", "sltp_orders", ["symbol"])

    # Проверяем наличие колонки session_id в trades перед созданием индекса
    if "session_id" in trades_columns:
        op.create_index("idx_trades_session_id", "trades", ["session_id"])


def downgrade():
    """Удаляет поля совместимости с v2."""

    # Удаляем индексы
    op.drop_index("idx_trades_session_id")
    op.drop_index("idx_trading_sessions_id")
    op.drop_index("idx_bybit_closed_pnl_symbol")
    op.drop_index("idx_bybit_positions_symbol")
    op.drop_index("idx_bybit_trade_symbol_time")
    op.drop_index("idx_bybit_trade_order_id")

    # Удаляем таблицы
    op.drop_table("trading_sessions")
    op.drop_table("bybit_closed_pnl")
    op.drop_table("bybit_wallet_balance")
    op.drop_table("bybit_positions")
    op.drop_table("bybit_trade_history")

    # Удаляем колонки из signals
    op.drop_column("signals", "processing_time")
    op.drop_column("signals", "ml_predictions")
    op.drop_column("signals", "indicators")

    # Удаляем колонки из orders
    op.drop_column("orders", "tp_order_id")
    op.drop_column("orders", "sl_order_id")
    op.drop_column("orders", "tp_trigger_price")
    op.drop_column("orders", "sl_trigger_price")
    op.drop_column("orders", "trigger_by")

    # Удаляем колонки из trades
    op.drop_column("trades", "session_id")
    op.drop_column("trades", "confidence")
    op.drop_column("trades", "loss_probability")
    op.drop_column("trades", "profit_probability")
    op.drop_column("trades", "model_score")
    op.drop_column("trades", "model_name")
