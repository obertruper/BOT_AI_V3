"""
RSI (Relative Strength Index) индикатор
Измеряет импульс ценовых изменений для определения перекупленности/перепроданности
"""

import logging
from typing import List, Optional

import pandas as pd

from ..base import IndicatorBase, IndicatorConfig, IndicatorResult

logger = logging.getLogger(__name__)


class RSIIndicator(IndicatorBase):
    """
    Индикатор RSI (Relative Strength Index)

    Параметры из AI кросс-верификации:
    - Период: 14 (стандарт, подходит для крипто)
    - Уровни: 25/75 (адаптированы для волатильности крипто)
    - Дивергенции: отслеживаются для дополнительных сигналов
    """

    def __init__(self, config: IndicatorConfig):
        """
        Инициализация RSI индикатора

        Args:
            config: Конфигурация с параметрами:
                - period: Период расчета (по умолчанию 14)
                - oversold: Уровень перепроданности (по умолчанию 25)
                - overbought: Уровень перекупленности (по умолчанию 75)
        """
        super().__init__(config)

    def _validate_params(self) -> None:
        """Валидация параметров RSI"""
        # Период
        self.period = self.params.get("period", 14)
        if not isinstance(self.period, int) or self.period < 2:
            raise ValueError(f"RSI period must be integer >= 2, got {self.period}")

        # Уровни
        self.oversold = self.params.get("oversold", 25)
        self.overbought = self.params.get("overbought", 75)

        if not 0 < self.oversold < self.overbought < 100:
            raise ValueError(
                f"RSI levels must be 0 < oversold({self.oversold}) < "
                f"overbought({self.overbought}) < 100"
            )

        logger.debug(
            f"RSI initialized: period={self.period}, "
            f"oversold={self.oversold}, overbought={self.overbought}"
        )

    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        """
        Расчет RSI

        Args:
            data: DataFrame с ценами

        Returns:
            Результат с сигналом и значением RSI
        """
        # Расчет изменений цены
        close_prices = data["close"]
        price_diff = close_prices.diff()

        # Разделение на положительные и отрицательные изменения
        gains = price_diff.where(price_diff > 0, 0)
        losses = -price_diff.where(price_diff < 0, 0)

        # Расчет средних значений
        avg_gains = gains.rolling(window=self.period).mean()
        avg_losses = losses.rolling(window=self.period).mean()

        # Избегаем деления на ноль
        rs = avg_gains / avg_losses.replace(0, 1e-10)

        # Расчет RSI
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]

        # Определение сигнала
        signal = self._determine_signal(current_rsi, rsi)

        # Расчет силы сигнала
        strength = self._calculate_strength(current_rsi)

        # Проверка дивергенций
        divergence = self._check_divergence(close_prices, rsi)

        # Метаданные
        metadata = {
            "rsi": round(current_rsi, 2),
            "oversold": self.oversold,
            "overbought": self.overbought,
            "divergence": divergence,
            "trend": self._get_rsi_trend(rsi),
        }

        return IndicatorResult(
            name=self.name,
            signal=signal,
            strength=strength,
            value=current_rsi,
            timestamp=data.index[-1],
            metadata=metadata,
        )

    def _determine_signal(self, current_rsi: float, rsi_series: pd.Series) -> int:
        """
        Определение торгового сигнала на основе RSI

        Args:
            current_rsi: Текущее значение RSI
            rsi_series: Серия значений RSI

        Returns:
            -1 (продажа), 0 (удержание), 1 (покупка)
        """
        # Базовый сигнал по уровням
        if current_rsi <= self.oversold:
            # Проверяем начало выхода из перепроданности
            if len(rsi_series) >= 2 and rsi_series.iloc[-2] < current_rsi:
                return 1  # Покупка при развороте вверх
            return 0  # Ждем разворота

        elif current_rsi >= self.overbought:
            # Проверяем начало выхода из перекупленности
            if len(rsi_series) >= 2 and rsi_series.iloc[-2] > current_rsi:
                return -1  # Продажа при развороте вниз
            return 0  # Ждем разворота

        else:
            # В нейтральной зоне проверяем пересечение 50
            if len(rsi_series) >= 2:
                prev_rsi = rsi_series.iloc[-2]

                # Пересечение 50 снизу вверх
                if prev_rsi < 50 <= current_rsi:
                    return 1

                # Пересечение 50 сверху вниз
                elif prev_rsi > 50 >= current_rsi:
                    return -1

            return 0

    def _calculate_strength(self, rsi_value: float) -> float:
        """
        Расчет силы сигнала (0-100)

        Args:
            rsi_value: Значение RSI

        Returns:
            Сила сигнала от 0 до 100
        """
        # Сила максимальна при экстремальных значениях
        if rsi_value <= self.oversold:
            # Чем ниже RSI, тем сильнее сигнал покупки
            strength = (self.oversold - rsi_value) / self.oversold * 100

        elif rsi_value >= self.overbought:
            # Чем выше RSI, тем сильнее сигнал продажи
            strength = (rsi_value - self.overbought) / (100 - self.overbought) * 100

        else:
            # В нейтральной зоне сила зависит от удаления от 50
            distance_from_50 = abs(rsi_value - 50)
            strength = distance_from_50 / 50 * 50  # Максимум 50 в нейтральной зоне

        return min(100, max(0, strength))

    def _check_divergence(self, prices: pd.Series, rsi: pd.Series) -> Optional[str]:
        """
        Проверка дивергенций между ценой и RSI

        Args:
            prices: Серия цен
            rsi: Серия значений RSI

        Returns:
            Тип дивергенции или None
        """
        if len(prices) < 20:
            return None

        # Последние 20 периодов для анализа
        recent_prices = prices.iloc[-20:]
        recent_rsi = rsi.iloc[-20:]

        # Поиск локальных экстремумов
        price_highs = self._find_peaks(recent_prices)
        price_lows = self._find_peaks(-recent_prices)
        rsi_highs = self._find_peaks(recent_rsi)
        rsi_lows = self._find_peaks(-recent_rsi)

        # Бычья дивергенция: цена делает новый минимум, RSI - нет
        if len(price_lows) >= 2 and len(rsi_lows) >= 2:
            if price_lows[-1] < price_lows[-2] and rsi_lows[-1] > rsi_lows[-2]:
                return "bullish_divergence"

        # Медвежья дивергенция: цена делает новый максимум, RSI - нет
        if len(price_highs) >= 2 and len(rsi_highs) >= 2:
            if price_highs[-1] > price_highs[-2] and rsi_highs[-1] < rsi_highs[-2]:
                return "bearish_divergence"

        return None

    def _find_peaks(self, series: pd.Series, distance: int = 3) -> List[float]:
        """
        Поиск локальных максимумов в серии

        Args:
            series: Анализируемая серия
            distance: Минимальное расстояние между пиками

        Returns:
            Список значений пиков
        """
        peaks = []
        values = series.values

        for i in range(distance, len(values) - distance):
            # Проверяем, является ли точка локальным максимумом
            if all(values[i] >= values[i - j] for j in range(1, distance + 1)) and all(
                values[i] >= values[i + j] for j in range(1, distance + 1)
            ):
                peaks.append(values[i])

        return peaks

    def _get_rsi_trend(self, rsi: pd.Series) -> str:
        """
        Определение тренда RSI

        Args:
            rsi: Серия значений RSI

        Returns:
            Направление тренда
        """
        if len(rsi) < 5:
            return "undefined"

        # Простое сравнение SMA
        sma_short = rsi.iloc[-5:].mean()
        sma_long = rsi.iloc[-10:].mean() if len(rsi) >= 10 else sma_short

        if sma_short > sma_long + 2:
            return "rising"
        elif sma_short < sma_long - 2:
            return "falling"
        else:
            return "neutral"

    def get_required_columns(self) -> List[str]:
        """Необходимые колонки данных"""
        return ["close"]

    def get_min_periods(self) -> int:
        """Минимальное количество периодов для расчета"""
        return self.period + 1
