"""
Абстрактный базовый класс для всех торговых стратегий
Определяет интерфейс, который должны реализовать все стратегии
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Типы торговых сигналов"""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CLOSE_LONG = "CLOSE_LONG"
    CLOSE_SHORT = "CLOSE_SHORT"


class SignalStrength(Enum):
    """Сила сигнала"""

    WEAK = "WEAK"  # 20-50
    MODERATE = "MODERATE"  # 50-70
    STRONG = "STRONG"  # 70-100


@dataclass
class MarketData:
    """Рыночные данные для анализа"""

    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str

    # Дополнительные поля для криптовалют
    quote_volume: float | None = None
    trades_count: int | None = None
    buy_volume: float | None = None
    sell_volume: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Преобразование в словарь"""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "timeframe": self.timeframe,
            "quote_volume": self.quote_volume,
            "trades_count": self.trades_count,
            "buy_volume": self.buy_volume,
            "sell_volume": self.sell_volume,
        }


@dataclass
class TradingSignal:
    """Торговый сигнал от стратегии"""

    timestamp: datetime
    symbol: str
    signal_type: SignalType
    confidence: float  # 0-100
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float

    # Метаданные
    strategy_name: str
    timeframe: str
    indicators_used: list[str]
    reasoning: str

    # Опциональные поля
    risk_reward_ratio: float | None = None
    expected_duration_hours: float | None = None
    metadata: dict[str, Any] | None = None

    @property
    def signal_strength(self) -> SignalStrength:
        """Определение силы сигнала на основе confidence"""
        if self.confidence >= 70:
            return SignalStrength.STRONG
        elif self.confidence >= 50:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK

    def to_dict(self) -> dict[str, Any]:
        """Преобразование в словарь для сериализации"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "signal_type": self.signal_type.value,
            "confidence": self.confidence,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "position_size": self.position_size,
            "strategy_name": self.strategy_name,
            "timeframe": self.timeframe,
            "indicators_used": self.indicators_used,
            "reasoning": self.reasoning,
            "risk_reward_ratio": self.risk_reward_ratio,
            "expected_duration_hours": self.expected_duration_hours,
            "metadata": self.metadata,
        }


@dataclass
class RiskParameters:
    """Параметры управления рисками для стратегии"""

    max_position_size_pct: float  # Максимальный размер позиции в % от депозита
    max_risk_per_trade_pct: float  # Максимальный риск на сделку в %
    stop_loss_type: str  # 'fixed', 'atr', 'trailing'
    stop_loss_value: float
    take_profit_type: str  # 'fixed', 'atr', 'multi_level'
    take_profit_value: float

    # Дополнительные параметры
    use_trailing_stop: bool = False
    trailing_activation_pct: float = 2.0
    trailing_distance_pct: float = 1.0
    partial_close_levels: list[tuple[float, float]] | None = None  # [(уровень, процент)]

    def validate(self) -> bool:
        """Валидация параметров"""
        if self.max_position_size_pct <= 0 or self.max_position_size_pct > 100:
            return False
        if self.max_risk_per_trade_pct <= 0 or self.max_risk_per_trade_pct > 10:
            return False
        if self.stop_loss_value <= 0:
            return False
        if self.take_profit_value <= 0:
            return False
        return True


class StrategyABC(ABC):
    """Абстрактный базовый класс для всех торговых стратегий"""

    def __init__(self, config: dict[str, Any]):
        """
        Инициализация стратегии

        Args:
            config: Конфигурация стратегии
        """
        self.config = config
        self.name = config.get("name", self.__class__.__name__)
        self.enabled = config.get("enabled", True)
        self.symbols = config.get("symbols", [])
        self.timeframes = config.get("timeframes", ["1h"])
        self._is_initialized = False

    @abstractmethod
    async def initialize(self) -> None:
        """Асинхронная инициализация стратегии"""
        pass

    @abstractmethod
    async def analyze(self, market_data: MarketData) -> TradingSignal | None:
        """
        Анализ рыночных данных и генерация сигнала

        Args:
            market_data: Данные для анализа

        Returns:
            TradingSignal или None если сигнала нет
        """
        pass

    @abstractmethod
    async def generate_signals(self, market_data_batch: list[MarketData]) -> list[TradingSignal]:
        """
        Генерация сигналов для пакета данных

        Args:
            market_data_batch: Список рыночных данных

        Returns:
            Список торговых сигналов
        """
        pass

    @abstractmethod
    def get_risk_parameters(self) -> RiskParameters:
        """Получение параметров управления рисками"""
        pass

    @abstractmethod
    def get_required_history_length(self) -> int:
        """Получение необходимой длины истории для анализа"""
        pass

    @abstractmethod
    def validate_config(self) -> tuple[bool, str | None]:
        """
        Валидация конфигурации стратегии

        Returns:
            (is_valid, error_message)
        """
        pass

    async def on_position_opened(self, position: dict[str, Any]) -> None:
        """Колбэк при открытии позиции"""
        logger.info(f"[{self.name}] Position opened: {position}")

    async def on_position_closed(self, position: dict[str, Any]) -> None:
        """Колбэк при закрытии позиции"""
        logger.info(f"[{self.name}] Position closed: {position}")

    async def on_signal_executed(
        self, signal: TradingSignal, execution_result: dict[str, Any]
    ) -> None:
        """Колбэк при исполнении сигнала"""
        logger.info(f"[{self.name}] Signal executed: {signal.signal_type.value}")

    def get_status(self) -> dict[str, Any]:
        """Получение статуса стратегии"""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "initialized": self._is_initialized,
            "symbols": self.symbols,
            "timeframes": self.timeframes,
            "risk_parameters": self.get_risk_parameters().__dict__,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, enabled={self.enabled})"
