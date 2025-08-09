#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модели данных для Enhanced SL/TP Manager
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class SLTPStatus(Enum):
    """Статусы SL/TP ордеров"""

    PENDING = "pending"
    ACTIVE = "active"
    TRIGGERED = "triggered"
    CANCELLED = "cancelled"
    PARTIALLY_FILLED = "partially_filled"


class TrailingType(Enum):
    """Типы трейлинг стопа"""

    FIXED = "fixed"  # Фиксированный шаг
    PERCENTAGE = "percentage"  # Процентный шаг
    ATR_BASED = "atr_based"  # На основе ATR
    ADAPTIVE = "adaptive"  # Адаптивный


@dataclass
class PartialTPLevel:
    """Уровень частичного тейк-профита"""

    level: int  # Номер уровня (1, 2, 3...)
    price: float  # Цена TP
    quantity: float  # Количество для закрытия
    percentage: float  # Процент от позиции
    close_ratio: float = 0.0  # Доля позиции для закрытия (0.25 = 25%)
    filled: bool = False  # Исполнен ли уровень
    order_id: Optional[str] = None
    filled_at: Optional[datetime] = None


@dataclass
class TrailingStopConfig:
    """Конфигурация трейлинг стопа"""

    enabled: bool = False
    type: TrailingType = TrailingType.PERCENTAGE
    step: float = 0.5  # Шаг трейлинга (% или пункты)
    activation_price: Optional[float] = None  # Цена активации
    min_profit: float = 0.3  # Минимальная прибыль для активации (%)
    max_distance: float = 2.0  # Макс. расстояние от цены (%)
    adaptive_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProfitProtectionConfig:
    """Конфигурация защиты прибыли"""

    enabled: bool = False
    breakeven_percent: float = 1.0  # Процент прибыли для активации безубытка
    breakeven_offset: float = 0.2  # Смещение от цены входа в %
    lock_percent: List[Dict[str, float]] = field(default_factory=list)
    # Пример lock_percent:
    # [{"trigger": 2.0, "lock": 1.0},  # При 2% прибыли защищаем 1%
    #  {"trigger": 3.0, "lock": 2.0},  # При 3% прибыли защищаем 2%
    #  {"trigger": 4.0, "lock": 3.0}]  # При 4% прибыли защищаем 3%
    max_updates: int = 5  # Максимальное количество обновлений


@dataclass
class SLTPConfig:
    """Основная конфигурация SL/TP"""

    # Базовые параметры
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    # Enhanced функции
    trailing_stop: TrailingStopConfig = field(default_factory=TrailingStopConfig)
    partial_tp_enabled: bool = False
    partial_tp_levels: List[PartialTPLevel] = field(default_factory=list)
    partial_tp_update_sl: bool = True  # Обновлять ли SL после частичного закрытия
    profit_protection: ProfitProtectionConfig = field(
        default_factory=ProfitProtectionConfig
    )

    # Временные корректировки
    time_based_adjustment: bool = False
    time_adjustments: List[Dict[str, Any]] = field(default_factory=list)

    # Волатильность
    volatility_adjustment: bool = False
    volatility_multiplier: float = 1.0

    # Метаданные
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class SLTPOrder:
    """Модель SL/TP ордера"""

    id: str
    symbol: str
    side: str  # Buy/Sell
    order_type: str  # StopLoss/TakeProfit/TrailingStop
    trigger_price: float
    quantity: float
    status: SLTPStatus = SLTPStatus.PENDING

    # Дополнительные поля
    position_id: Optional[str] = None
    parent_order_id: Optional[str] = None
    level: Optional[int] = None  # Для partial TP

    # Временные метки
    created_at: datetime = field(default_factory=datetime.now)
    triggered_at: Optional[datetime] = None
    updated_at: datetime = field(default_factory=datetime.now)

    # Exchange-specific данные
    exchange_order_id: Optional[str] = None
    exchange_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SLTPHistory:
    """История изменений SL/TP"""

    id: str
    position_id: str
    action: str  # create/update/trigger/cancel
    order_type: str  # sl/tp/trailing

    # Изменения
    old_price: Optional[float] = None
    new_price: Optional[float] = None
    reason: Optional[str] = None

    # Метаданные
    timestamp: datetime = field(default_factory=datetime.now)
    extra_data: Dict[str, Any] = field(default_factory=dict)
