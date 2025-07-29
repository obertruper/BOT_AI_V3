"""
Главный класс indicator_strategy
Реализует торговую стратегию на основе технических индикаторов
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from strategies.base import IndicatorStrategyBase, MarketData, RiskParameters, TradingSignal
from strategies.registry import register_strategy

from ..indicators import get_indicator_manager
from ..scoring import ScoringEngine
from .signal_generator import SignalGenerator

logger = logging.getLogger(__name__)


@register_strategy(
    "indicator_strategy",
    version="2.0",
    author="BOT Trading Team",
    tags=["indicators", "technical", "swing", "1-7days"],
    description="Комплексная стратегия на основе технических индикаторов для позиций 1-7 дней",
)
class IndicatorStrategy(IndicatorStrategyBase):
    """
    Торговая стратегия на основе матрицы скоринга технических индикаторов

    Особенности:
    - Адаптивные веса индикаторов в зависимости от режима рынка
    - Поддержка 12+ технических индикаторов
    - Оптимизированные параметры для криптовалют
    - Управление рисками для позиций 1-7 дней
    """

    def __init__(self, config: Dict[str, Any]):
        """Инициализация стратегии"""
        super().__init__(config)

        # Компоненты стратегии
        self.indicator_manager = None
        self.scoring_engine = None
        self.signal_generator = None

        # Параметры стратегии
        self.min_indicators_required = config.get("min_indicators_required", 3)
        self.signal_threshold = config.get("signal_threshold", 50)
        self.use_dynamic_weights = config.get("use_dynamic_weights", True)

        # Статистика
        self._total_signals = 0
        self._successful_signals = 0

    async def _initialize_indicators(self) -> None:
        """Инициализация индикаторов"""
        # Создание менеджера индикаторов
        self.indicator_manager = get_indicator_manager(self.indicator_config)

        # Создание движка скоринга
        self.scoring_engine = ScoringEngine(
            base_weights=self.base_weights,
            regime_multipliers=self.regime_multipliers,
            use_dynamic_weights=self.use_dynamic_weights,
        )

        # Создание генератора сигналов
        self.signal_generator = SignalGenerator(
            risk_config=self.risk_config, signal_threshold=self.signal_threshold
        )

        logger.info(
            f"Initialized {len(self.indicator_manager.get_indicators())} indicators"
        )

    async def _calculate_all_indicators(self, symbol: str) -> Dict[str, Dict[str, Any]]:
        """
        Расчет всех индикаторов для символа

        Args:
            symbol: Торговый символ

        Returns:
            Словарь с результатами индикаторов по категориям
        """
        if symbol not in self.market_data_history:
            logger.warning(f"No market data history for {symbol}")
            return {}

        df = self.market_data_history[symbol]
        if len(df) < self.get_required_history_length():
            logger.warning(f"Insufficient history for {symbol}: {len(df)} bars")
            return {}

        # Проверка кэша
        cache_key = f"{symbol}_{df.index[-1]}"
        if cache_key in self.indicator_cache:
            cached_time = self.last_cache_update.get(cache_key)
            if (
                cached_time
                and (datetime.now() - cached_time).seconds < self.cache_ttl_seconds
            ):
                return self.indicator_cache[cache_key]

        # Расчет индикаторов
        results = {}

        # Трендовые индикаторы
        trend_indicators = await self.indicator_manager.calculate_trend_indicators(df)
        if trend_indicators:
            results["trend"] = trend_indicators

        # Импульсные индикаторы
        momentum_indicators = (
            await self.indicator_manager.calculate_momentum_indicators(df)
        )
        if momentum_indicators:
            results["momentum"] = momentum_indicators

        # Объемные индикаторы
        volume_indicators = await self.indicator_manager.calculate_volume_indicators(df)
        if volume_indicators:
            results["volume"] = volume_indicators

        # Индикаторы волатильности
        volatility_indicators = (
            await self.indicator_manager.calculate_volatility_indicators(df)
        )
        if volatility_indicators:
            results["volatility"] = volatility_indicators

        # Кэширование результатов
        self.indicator_cache[cache_key] = results
        self.last_cache_update[cache_key] = datetime.now()

        return results

    async def generate_signals(
        self, market_data_batch: List[MarketData]
    ) -> List[TradingSignal]:
        """
        Генерация сигналов для пакета данных

        Args:
            market_data_batch: Список рыночных данных

        Returns:
            Список торговых сигналов
        """
        signals = []

        # Группировка данных по символам
        symbol_data = {}
        for data in market_data_batch:
            if data.symbol not in symbol_data:
                symbol_data[data.symbol] = []
            symbol_data[data.symbol].append(data)

        # Обработка каждого символа
        for symbol, data_list in symbol_data.items():
            # Обновление истории последними данными
            for data in data_list:
                self._update_market_history(data)

            # Анализ последних данных
            latest_data = data_list[-1]
            signal = await self.analyze(latest_data)

            if signal:
                signals.append(signal)
                self._total_signals += 1

        return signals

    def get_risk_parameters(self) -> RiskParameters:
        """Получение параметров управления рисками"""
        return RiskParameters(
            max_position_size_pct=self.risk_config.get("max_position_size", 5.0),
            max_risk_per_trade_pct=self.risk_config.get("max_risk_per_trade", 2.0),
            stop_loss_type=self.risk_config.get("stop_loss_type", "atr"),
            stop_loss_value=self.risk_config.get("stop_loss_value", 3.0),
            take_profit_type=self.risk_config.get("take_profit_type", "multi_level"),
            take_profit_value=self.risk_config.get("take_profit_value", 6.0),
            use_trailing_stop=self.risk_config.get("use_trailing_stop", True),
            trailing_activation_pct=self.risk_config.get("trailing_activation", 2.0),
            trailing_distance_pct=self.risk_config.get("trailing_distance", 1.0),
            partial_close_levels=self.risk_config.get(
                "partial_close_levels",
                [
                    (1.0, 0.25),  # При достижении 1:1 закрыть 25%
                    (1.5, 0.25),  # При достижении 1.5:1 закрыть еще 25%
                    (2.0, 0.50),  # При достижении 2:1 закрыть оставшиеся 50%
                ],
            ),
        )

    def get_required_history_length(self) -> int:
        """Получение необходимой длины истории"""
        # Максимальный период среди всех индикаторов
        max_period = 200  # EMA200

        if self.indicator_config:
            # Проверка конфигурации индикаторов
            for indicator_type, params in self.indicator_config.items():
                if isinstance(params, dict) and "period" in params:
                    max_period = max(max_period, params["period"])
                elif isinstance(params, dict) and "slow_period" in params:
                    max_period = max(max_period, params["slow_period"])

        # Добавляем буфер 20%
        return int(max_period * 1.2)

    async def on_signal_executed(
        self, signal: TradingSignal, execution_result: Dict[str, Any]
    ) -> None:
        """Обработка результата исполнения сигнала"""
        await super().on_signal_executed(signal, execution_result)

        if execution_result.get("success", False):
            self._successful_signals += 1

        # Обновление статистики
        if self._total_signals > 0:
            success_rate = self._successful_signals / self._total_signals
            logger.info(f"[{self.name}] Signal execution rate: {success_rate:.2%}")

    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики стратегии"""
        stats = {
            "total_signals": self._total_signals,
            "successful_signals": self._successful_signals,
            "success_rate": (
                self._successful_signals / self._total_signals
                if self._total_signals > 0
                else 0
            ),
            "active_indicators": (
                len(self.indicator_manager.get_indicators())
                if self.indicator_manager
                else 0
            ),
            "cache_size": len(self.indicator_cache),
            "symbols_tracked": len(self.market_data_history),
        }

        return stats

    def validate_config(self) -> Tuple[bool, Optional[str]]:
        """Валидация конфигурации стратегии"""
        # Базовая валидация
        is_valid, error = super().validate_config()
        if not is_valid:
            return False, error

        # Проверка специфичных параметров
        if self.min_indicators_required < 1:
            return False, "min_indicators_required must be at least 1"

        if self.signal_threshold < 20 or self.signal_threshold > 80:
            return False, "signal_threshold must be between 20 and 80"

        # Проверка наличия индикаторов
        if not self.indicator_config:
            return False, "No indicators configured"

        return True, None
