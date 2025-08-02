#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Базовые модели для торгового бота
"""

import enum

from sqlalchemy import JSON, Column, DateTime, Enum, Float, Integer, String
from sqlalchemy.sql import func

from database.connections import Base


class OrderStatus(enum.Enum):
    """Статусы ордеров"""

    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderType(enum.Enum):
    """Типы ордеров"""

    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    STOP_LIMIT = "stop_limit"


class OrderSide(enum.Enum):
    """Направление ордера"""

    BUY = "buy"
    SELL = "sell"


class SignalType(enum.Enum):
    """Типы торговых сигналов"""

    LONG = "long"
    SHORT = "short"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"
    NEUTRAL = "neutral"


class Order(Base):
    """Модель ордера"""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    exchange = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False)
    order_id = Column(String(100), unique=True, nullable=False)

    # Параметры ордера
    side = Column(Enum(OrderSide), nullable=False)
    order_type = Column(Enum(OrderType), nullable=False)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)

    # Цены и объемы
    price = Column(Float)
    quantity = Column(Float, nullable=False)
    filled_quantity = Column(Float, default=0)
    average_price = Column(Float)

    # Stop/Take profit
    stop_loss = Column(Float)
    take_profit = Column(Float)

    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    filled_at = Column(DateTime(timezone=True))

    # Дополнительная информация
    strategy_name = Column(String(100))
    trader_id = Column(String(100))
    extra_data = Column(JSON)


class Trade(Base):
    """Модель исполненной сделки"""

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True)
    exchange = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False)
    trade_id = Column(String(100), unique=True, nullable=False)
    order_id = Column(String(100), nullable=False)

    # Параметры сделки
    side = Column(Enum(OrderSide), nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    commission = Column(Float, default=0)
    commission_asset = Column(String(20))

    # PnL
    realized_pnl = Column(Float)

    # Временные метки
    executed_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    strategy_name = Column(String(100))
    trader_id = Column(String(100))


class Signal(Base):
    """Модель торгового сигнала"""

    __tablename__ = "signals"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    exchange = Column(String(50), nullable=False)

    # Параметры сигнала
    signal_type = Column(Enum(SignalType), nullable=False)
    strength = Column(Float)  # Сила сигнала 0-1
    confidence = Column(Float)  # Уверенность 0-1

    # Рекомендуемые параметры
    suggested_price = Column(Float)
    suggested_quantity = Column(Float)
    suggested_stop_loss = Column(Float)
    suggested_take_profit = Column(Float)

    # Источник
    strategy_name = Column(String(100), nullable=False)
    timeframe = Column(String(10))

    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))

    # Дополнительные данные
    indicators = Column(JSON)  # Значения индикаторов
    extra_data = Column(JSON)


class Balance(Base):
    """Модель баланса"""

    __tablename__ = "balances"

    id = Column(Integer, primary_key=True)
    exchange = Column(String(50), nullable=False)
    asset = Column(String(20), nullable=False)

    # Балансы
    free = Column(Float, nullable=False, default=0)
    locked = Column(Float, nullable=False, default=0)
    total = Column(Float, nullable=False, default=0)

    # В USD эквиваленте
    usd_value = Column(Float)

    # Временные метки
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Владелец
    trader_id = Column(String(100))


class Performance(Base):
    """Метрики производительности"""

    __tablename__ = "performance"

    id = Column(Integer, primary_key=True)
    trader_id = Column(String(100), nullable=False)
    strategy_name = Column(String(100))

    # Период
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)

    # Метрики
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)

    total_pnl = Column(Float, default=0)
    total_volume = Column(Float, default=0)

    win_rate = Column(Float)
    profit_factor = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)

    # Временная метка
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Дополнительные метрики
    metrics = Column(JSON)
