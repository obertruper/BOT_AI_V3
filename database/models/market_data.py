#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модели для хранения рыночных данных (OHLCV) и обработанных данных с индикаторами
Адаптировано из LLM TRANSFORM для интеграции с BOT_AI_V3
"""

import enum

from sqlalchemy import (
    DECIMAL,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.connections import Base


class MarketType(enum.Enum):
    """Типы рынков"""

    SPOT = "SPOT"
    FUTURES = "FUTURES"
    PERP = "PERP"


class IntervalType(enum.Enum):
    """Временные интервалы"""

    M1 = 1  # 1 минута
    M5 = 5  # 5 минут
    M15 = 15  # 15 минут
    M30 = 30  # 30 минут
    H1 = 60  # 1 час
    H4 = 240  # 4 часа
    D1 = 1440  # 1 день


class RawMarketData(Base):
    """
    Модель для хранения сырых OHLCV данных
    Основная таблица для исторических данных
    """

    __tablename__ = "raw_market_data"

    id = Column(BigInteger, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(
        BigInteger, nullable=False, index=True
    )  # Unix timestamp в миллисекундах
    datetime = Column(DateTime(timezone=True), nullable=False, index=True)

    # OHLCV данные
    open = Column(DECIMAL(20, 8), nullable=False)
    high = Column(DECIMAL(20, 8), nullable=False)
    low = Column(DECIMAL(20, 8), nullable=False)
    close = Column(DECIMAL(20, 8), nullable=False)
    volume = Column(DECIMAL(20, 8), nullable=False)
    turnover = Column(DECIMAL(20, 8), default=0)  # Объем в базовой валюте (USDT)

    # Метаданные
    interval_minutes = Column(Integer, nullable=False, default=15)
    market_type = Column(
        Enum(MarketType), default=MarketType.FUTURES
    )  # Торгуем на фьючерсах
    exchange = Column(String(50), default="bybit")

    # Дополнительные поля для futures
    open_interest = Column(DECIMAL(20, 8))  # Открытый интерес для фьючерсов
    funding_rate = Column(DECIMAL(10, 8))  # Ставка финансирования

    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Связь с обработанными данными
    processed_data = relationship(
        "ProcessedMarketData", back_populates="raw_data", uselist=False
    )

    # Уникальный индекс для предотвращения дубликатов
    __table_args__ = (
        UniqueConstraint(
            "symbol",
            "timestamp",
            "interval_minutes",
            "exchange",
            name="_symbol_timestamp_interval_exchange_uc",
        ),
        Index("idx_raw_market_data_symbol_datetime", "symbol", "datetime"),
        Index("idx_raw_market_data_datetime_desc", "datetime"),
    )


class ProcessedMarketData(Base):
    """
    Модель для хранения обработанных данных с техническими индикаторами
    Используется для ML предсказаний
    """

    __tablename__ = "processed_market_data"

    id = Column(BigInteger, primary_key=True)
    raw_data_id = Column(BigInteger, ForeignKey("raw_market_data.id"), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(BigInteger, nullable=False, index=True)
    datetime = Column(DateTime(timezone=True), nullable=False, index=True)

    # Базовые OHLCV (дублируются для быстрого доступа)
    open = Column(DECIMAL(20, 8), nullable=False)
    high = Column(DECIMAL(20, 8), nullable=False)
    low = Column(DECIMAL(20, 8), nullable=False)
    close = Column(DECIMAL(20, 8), nullable=False)
    volume = Column(DECIMAL(20, 8), nullable=False)

    # Технические индикаторы в JSON формате для гибкости
    # Включает: SMA, EMA, RSI, MACD, Bollinger Bands, ATR, и др.
    technical_indicators = Column(JSONB, nullable=False, default={})

    # Микроструктурные признаки
    microstructure_features = Column(JSONB, default={})

    # ML признаки (240+ features из feature_engineering.py)
    ml_features = Column(JSONB, default={})

    # Целевые переменные для ML (из LLM TRANSFORM)
    # Direction predictions (0=UP, 1=DOWN, 2=FLAT)
    direction_15m = Column(Integer)
    direction_1h = Column(Integer)
    direction_4h = Column(Integer)
    direction_12h = Column(Integer)

    # Future returns
    future_return_15m = Column(Float)
    future_return_1h = Column(Float)
    future_return_4h = Column(Float)
    future_return_12h = Column(Float)

    # Вероятности достижения уровней
    long_will_reach_1pct_4h = Column(Float)
    long_will_reach_2pct_4h = Column(Float)
    short_will_reach_1pct_4h = Column(Float)
    short_will_reach_2pct_4h = Column(Float)

    # Риск метрики
    max_drawdown_1h = Column(Float)
    max_rally_1h = Column(Float)
    max_drawdown_4h = Column(Float)
    max_rally_4h = Column(Float)

    # Метаданные
    processing_version = Column(String(10), default="1.0")
    model_version = Column(String(50))  # Версия модели, которая обработала данные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Связь с сырыми данными
    raw_data = relationship("RawMarketData", back_populates="processed_data")

    # Уникальный индекс
    __table_args__ = (
        UniqueConstraint("symbol", "timestamp", name="_symbol_timestamp_processed_uc"),
        Index("idx_processed_market_data_symbol_datetime", "symbol", "datetime"),
        Index("idx_processed_market_data_directions", "direction_15m", "direction_1h"),
        Index(
            "idx_processed_technical_indicators",
            "technical_indicators",
            postgresql_using="gin",
        ),
    )


class TechnicalIndicators(Base):
    """
    Отдельная таблица для хранения рассчитанных технических индикаторов
    Для оптимизации можно хранить часто используемые индикаторы отдельно
    """

    __tablename__ = "technical_indicators"

    id = Column(BigInteger, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(BigInteger, nullable=False, index=True)
    datetime = Column(DateTime(timezone=True), nullable=False)
    interval_minutes = Column(Integer, nullable=False, default=15)

    # Трендовые индикаторы
    sma_10 = Column(Float)
    sma_20 = Column(Float)
    sma_50 = Column(Float)
    sma_100 = Column(Float)
    sma_200 = Column(Float)

    ema_10 = Column(Float)
    ema_20 = Column(Float)
    ema_50 = Column(Float)

    # Моментум индикаторы
    rsi_14 = Column(Float)
    rsi_7 = Column(Float)
    stoch_k = Column(Float)
    stoch_d = Column(Float)

    # MACD
    macd_line = Column(Float)
    macd_signal = Column(Float)
    macd_histogram = Column(Float)

    # Волатильность
    atr_14 = Column(Float)
    bb_upper = Column(Float)
    bb_middle = Column(Float)
    bb_lower = Column(Float)
    bb_width = Column(Float)

    # Объемные индикаторы
    obv = Column(Float)  # On Balance Volume
    vwap = Column(Float)  # Volume Weighted Average Price
    mfi = Column(Float)  # Money Flow Index

    # Дополнительные индикаторы в JSON
    additional_indicators = Column(JSONB, default={})

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "symbol",
            "timestamp",
            "interval_minutes",
            name="_symbol_timestamp_interval_indicators_uc",
        ),
        Index("idx_technical_indicators_symbol_datetime", "symbol", "datetime"),
    )


class MarketDataSnapshot(Base):
    """
    Текущий снимок рынка для быстрого доступа
    Обновляется каждую минуту для активных символов
    """

    __tablename__ = "market_data_snapshots"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, unique=True)

    # Последние данные
    last_price = Column(DECIMAL(20, 8))
    last_volume = Column(DECIMAL(20, 8))
    last_update = Column(DateTime(timezone=True))

    # 24h статистика
    price_24h_change = Column(Float)
    price_24h_change_pct = Column(Float)
    volume_24h = Column(DECIMAL(20, 8))
    high_24h = Column(DECIMAL(20, 8))
    low_24h = Column(DECIMAL(20, 8))

    # ML предсказания (последние)
    ml_direction_prediction = Column(Integer)  # 0=UP, 1=DOWN, 2=FLAT
    ml_confidence = Column(Float)
    ml_predicted_return = Column(Float)
    ml_prediction_time = Column(DateTime(timezone=True))

    # Статус
    is_active = Column(Boolean, default=True)
    data_quality_score = Column(Float, default=1.0)  # 0-1, качество данных

    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_snapshot_symbol", "symbol"),
        Index("idx_snapshot_updated", "updated_at"),
    )
