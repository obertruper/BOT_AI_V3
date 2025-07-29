"""
Базовый класс для индикаторных торговых стратегий
Предоставляет общую функциональность для стратегий на основе технических индикаторов
"""

import logging
from abc import abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .strategy_abc import MarketData, SignalType, StrategyABC, TradingSignal

logger = logging.getLogger(__name__)


class MarketRegime(str):
    """Рыночные режимы для адаптивных весов"""

    TRENDING = "trending"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"


class IndicatorStrategyBase(StrategyABC):
    """Базовый класс для стратегий на основе технических индикаторов"""

    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация индикаторной стратегии

        Args:
            config: Конфигурация стратегии
        """
        super().__init__(config)

        # Параметры индикаторов
        self.indicator_config = config.get("indicators", {})
        self.scoring_config = config.get("scoring", {})
        self.risk_config = config.get("risk_management", {})

        # История данных для расчета индикаторов
        self.market_data_history: Dict[str, pd.DataFrame] = {}
        self.max_history_length = config.get("max_history_length", 500)

        # Кэш рассчитанных индикаторов
        self.indicator_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl_seconds = config.get("cache_ttl_seconds", 60)
        self.last_cache_update: Dict[str, datetime] = {}

        # Веса для скоринга
        self.base_weights = self.scoring_config.get(
            "base_weights",
            {"trend": 0.30, "momentum": 0.25, "volume": 0.25, "volatility": 0.20},
        )

        # Адаптивные множители для разных режимов рынка
        self.regime_multipliers = self.scoring_config.get(
            "regime_multipliers",
            {
                MarketRegime.TRENDING: {"trend": 1.3, "momentum": 1.1},
                MarketRegime.RANGING: {"momentum": 1.4, "volatility": 1.2},
                MarketRegime.HIGH_VOLATILITY: {"volatility": 1.5, "volume": 1.2},
            },
        )

    async def initialize(self) -> None:
        """Асинхронная инициализация стратегии"""
        logger.info(f"Initializing {self.name} indicator strategy")

        # Инициализация индикаторов
        await self._initialize_indicators()

        # Валидация конфигурации
        is_valid, error = self.validate_config()
        if not is_valid:
            raise ValueError(f"Invalid configuration: {error}")

        self._is_initialized = True
        logger.info(f"{self.name} initialized successfully")

    @abstractmethod
    async def _initialize_indicators(self) -> None:
        """Инициализация специфичных для стратегии индикаторов"""
        pass

    async def analyze(self, market_data: MarketData) -> Optional[TradingSignal]:
        """
        Анализ рыночных данных с использованием индикаторов

        Args:
            market_data: Текущие рыночные данные

        Returns:
            Торговый сигнал или None
        """
        if not self._is_initialized:
            logger.warning(f"{self.name} not initialized, skipping analysis")
            return None

        # Обновление истории данных
        self._update_market_history(market_data)

        # Определение рыночного режима
        market_regime = await self._detect_market_regime(market_data.symbol)

        # Расчет индикаторов
        indicators = await self._calculate_all_indicators(market_data.symbol)
        if not indicators:
            return None

        # Расчет общего скора
        total_score = self._calculate_total_score(indicators, market_regime)

        # Генерация сигнала на основе скора
        signal = self._generate_signal_from_score(market_data, total_score, indicators)

        return signal

    def _update_market_history(self, market_data: MarketData) -> None:
        """Обновление истории рыночных данных"""
        symbol = market_data.symbol

        if symbol not in self.market_data_history:
            self.market_data_history[symbol] = pd.DataFrame()

        # Добавление новых данных
        new_row = pd.DataFrame(
            [
                {
                    "timestamp": market_data.timestamp,
                    "open": market_data.open,
                    "high": market_data.high,
                    "low": market_data.low,
                    "close": market_data.close,
                    "volume": market_data.volume,
                    "quote_volume": market_data.quote_volume,
                }
            ]
        )

        self.market_data_history[symbol] = pd.concat(
            [self.market_data_history[symbol], new_row], ignore_index=True
        )

        # Ограничение размера истории
        if len(self.market_data_history[symbol]) > self.max_history_length:
            self.market_data_history[symbol] = self.market_data_history[symbol].iloc[
                -self.max_history_length :
            ]

    async def _detect_market_regime(self, symbol: str) -> MarketRegime:
        """
        Определение текущего режима рынка

        Args:
            symbol: Торговый символ

        Returns:
            Режим рынка
        """
        if (
            symbol not in self.market_data_history
            or len(self.market_data_history[symbol]) < 50
        ):
            return MarketRegime.RANGING

        df = self.market_data_history[symbol].tail(50)
        closes = df["close"].values

        # Расчет волатильности
        returns = np.diff(closes) / closes[:-1]
        volatility = np.std(returns) * np.sqrt(24)  # Дневная волатильность

        # Определение тренда
        sma_short = np.mean(closes[-10:])
        sma_long = np.mean(closes[-30:])
        trend_strength = abs(sma_short - sma_long) / sma_long

        # Классификация режима
        if volatility > 0.05:  # 5% дневная волатильность
            return MarketRegime.HIGH_VOLATILITY
        elif trend_strength > 0.02:  # 2% разница между MA
            return MarketRegime.TRENDING
        else:
            return MarketRegime.RANGING

    @abstractmethod
    async def _calculate_all_indicators(
        self, symbol: str
    ) -> Dict[str, Dict[str, float]]:
        """
        Расчет всех индикаторов для символа

        Returns:
            Словарь с категориями индикаторов и их значениями
        """
        pass

    def _calculate_total_score(
        self, indicators: Dict[str, Dict[str, float]], market_regime: MarketRegime
    ) -> float:
        """
        Расчет общего скора на основе индикаторов и режима рынка

        Args:
            indicators: Рассчитанные индикаторы
            market_regime: Текущий режим рынка

        Returns:
            Общий скор от -100 до +100
        """
        total_score = 0.0

        # Получение адаптивных весов для текущего режима
        adaptive_weights = self._get_adaptive_weights(market_regime)

        # Расчет взвешенного скора по категориям
        for category, weight in adaptive_weights.items():
            if category in indicators:
                category_score = self._calculate_category_score(indicators[category])
                total_score += category_score * weight

        # Ограничение диапазона
        return max(min(total_score, 100), -100)

    def _get_adaptive_weights(self, market_regime: MarketRegime) -> Dict[str, float]:
        """Получение адаптивных весов для режима рынка"""
        weights = self.base_weights.copy()

        if market_regime in self.regime_multipliers:
            multipliers = self.regime_multipliers[market_regime]
            for category, multiplier in multipliers.items():
                if category in weights:
                    weights[category] *= multiplier

        # Нормализация весов
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}

        return weights

    def _calculate_category_score(self, category_indicators: Dict[str, float]) -> float:
        """Расчет скора для категории индикаторов"""
        if not category_indicators:
            return 0.0

        scores = []
        for indicator_name, value in category_indicators.items():
            if "signal" in value:
                signal = value["signal"]
                strength = value.get("strength", 50)
                scores.append(signal * strength)

        return np.mean(scores) if scores else 0.0

    def _generate_signal_from_score(
        self, market_data: MarketData, total_score: float, indicators: Dict[str, Any]
    ) -> Optional[TradingSignal]:
        """
        Генерация торгового сигнала на основе общего скора

        Args:
            market_data: Текущие рыночные данные
            total_score: Общий скор от -100 до +100
            indicators: Рассчитанные индикаторы

        Returns:
            Торговый сигнал или None
        """
        # Пороги для генерации сигналов
        buy_threshold = self.scoring_config.get("buy_threshold", 50)
        sell_threshold = self.scoring_config.get("sell_threshold", -50)

        if abs(total_score) < 20:  # Нейтральная зона
            return None

        # Определение типа сигнала
        if total_score >= buy_threshold:
            signal_type = SignalType.BUY
        elif total_score <= sell_threshold:
            signal_type = SignalType.SELL
        else:
            return None

        # Расчет параметров риска
        risk_params = self.get_risk_parameters()
        entry_price = market_data.close

        # Расчет SL/TP
        if signal_type == SignalType.BUY:
            stop_loss = entry_price * (1 - risk_params.stop_loss_value / 100)
            take_profit = entry_price * (1 + risk_params.take_profit_value / 100)
        else:
            stop_loss = entry_price * (1 + risk_params.stop_loss_value / 100)
            take_profit = entry_price * (1 - risk_params.take_profit_value / 100)

        # Расчет размера позиции
        position_size = self._calculate_position_size(
            abs(total_score), risk_params.max_position_size_pct
        )

        # Создание сигнала
        signal = TradingSignal(
            timestamp=market_data.timestamp,
            symbol=market_data.symbol,
            signal_type=signal_type,
            confidence=abs(total_score),
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            strategy_name=self.name,
            timeframe=market_data.timeframe,
            indicators_used=self._get_active_indicators(indicators),
            reasoning=self._generate_reasoning(total_score, indicators),
            risk_reward_ratio=abs(take_profit - entry_price)
            / abs(entry_price - stop_loss),
        )

        return signal

    def _calculate_position_size(self, confidence: float, max_size_pct: float) -> float:
        """Расчет размера позиции на основе уверенности"""
        # Линейная зависимость от уверенности
        confidence_factor = confidence / 100.0
        base_size = max_size_pct * 0.5  # Базовый размер 50% от максимального

        position_size = base_size + (max_size_pct - base_size) * confidence_factor
        return min(position_size, max_size_pct)

    def _get_active_indicators(self, indicators: Dict[str, Any]) -> List[str]:
        """Получение списка активных индикаторов"""
        active = []
        for category, category_indicators in indicators.items():
            for indicator_name in category_indicators.keys():
                active.append(f"{category}.{indicator_name}")
        return active

    def _generate_reasoning(
        self, total_score: float, indicators: Dict[str, Any]
    ) -> str:
        """Генерация объяснения для сигнала"""
        direction = "бычий" if total_score > 0 else "медвежий"
        strength = "сильный" if abs(total_score) > 70 else "умеренный"

        reasoning = f"{strength} {direction} сигнал (скор: {total_score:.1f}). "

        # Добавление деталей по категориям
        details = []
        for category, category_indicators in indicators.items():
            category_score = self._calculate_category_score(category_indicators)
            if abs(category_score) > 20:
                details.append(f"{category}: {category_score:.1f}")

        if details:
            reasoning += "Основные факторы: " + ", ".join(details)

        return reasoning

    def validate_config(self) -> Tuple[bool, Optional[str]]:
        """Валидация конфигурации стратегии"""
        # Проверка базовых параметров
        if not self.symbols:
            return False, "No symbols configured"

        if not self.timeframes:
            return False, "No timeframes configured"

        # Проверка весов
        total_weight = sum(self.base_weights.values())
        if abs(total_weight - 1.0) > 0.01:
            return False, f"Base weights sum must be 1.0, got {total_weight}"

        # Проверка параметров риска
        risk_params = self.get_risk_parameters()
        if not risk_params.validate():
            return False, "Invalid risk parameters"

        return True, None
