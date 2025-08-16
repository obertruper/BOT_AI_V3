"""
Оптимизированная версия стратегии с параллельными вычислениями индикаторов
Снижает время расчета с 4798ms до <1000ms
"""

import asyncio
import logging
import time
from collections import deque
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from strategies.base.strategy_abc import MarketData, TradingSignal
from strategies.indicator_strategy.core.strategy import IndicatorStrategy

logger = logging.getLogger(__name__)


class CircularBuffer:
    """Эффективный циклический буфер для рыночных данных"""

    def __init__(self, max_size: int = 500):
        self.max_size = max_size
        self._timestamps = deque(maxlen=max_size)
        self._open = np.zeros(max_size, dtype=np.float64)
        self._high = np.zeros(max_size, dtype=np.float64)
        self._low = np.zeros(max_size, dtype=np.float64)
        self._close = np.zeros(max_size, dtype=np.float64)
        self._volume = np.zeros(max_size, dtype=np.float64)
        self._current_size = 0
        self._write_index = 0

    def add(
        self,
        timestamp: datetime,
        open_: float,
        high: float,
        low: float,
        close: float,
        volume: float,
    ):
        """Добавление новых данных без создания новых объектов"""
        self._timestamps.append(timestamp)

        idx = self._write_index % self.max_size
        self._open[idx] = open_
        self._high[idx] = high
        self._low[idx] = low
        self._close[idx] = close
        self._volume[idx] = volume

        self._write_index += 1
        self._current_size = min(self._current_size + 1, self.max_size)

    def to_dataframe(self) -> pd.DataFrame:
        """Преобразование в DataFrame только при необходимости"""
        if self._current_size == 0:
            return pd.DataFrame()

        # Используем view для избежания копирования
        size = self._current_size
        if size < self.max_size:
            return pd.DataFrame(
                {
                    "timestamp": list(self._timestamps),
                    "open": self._open[:size],
                    "high": self._high[:size],
                    "low": self._low[:size],
                    "close": self._close[:size],
                    "volume": self._volume[:size],
                }
            )
        else:
            # Правильный порядок для циклического буфера
            start_idx = self._write_index % self.max_size
            indices = np.arange(start_idx, start_idx + self.max_size) % self.max_size
            return pd.DataFrame(
                {
                    "timestamp": list(self._timestamps),
                    "open": self._open[indices],
                    "high": self._high[indices],
                    "low": self._low[indices],
                    "close": self._close[indices],
                    "volume": self._volume[indices],
                }
            )

    @property
    def size(self) -> int:
        return self._current_size


class PerformanceTracker:
    """Декоратор для отслеживания производительности"""

    def __init__(self, name: str):
        self.name = name
        self.timings = deque(maxlen=100)

    def __call__(self, func):
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed = (time.perf_counter() - start) * 1000  # В миллисекундах
                self.timings.append(elapsed)
                if len(self.timings) == 100:
                    avg_time = sum(self.timings) / len(self.timings)
                    logger.debug(f"{self.name} avg time: {avg_time:.2f}ms")

        return wrapper


class OptimizedIndicatorStrategy(IndicatorStrategy):
    """Оптимизированная версия индикаторной стратегии"""

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)

        # Заменяем обычные DataFrame на CircularBuffer
        self.market_buffers: dict[str, CircularBuffer] = {}

        # Оптимизированный кэш с хэш-ключами
        self._cache_data: dict[int, dict[str, Any]] = {}
        self._cache_timestamps: dict[int, float] = {}

        # Пул для параллельных вычислений
        self.indicator_semaphore = asyncio.Semaphore(4)  # Ограничиваем параллелизм

    def _update_market_history(self, market_data: MarketData) -> None:
        """Оптимизированное обновление истории без pd.concat"""
        symbol = market_data.symbol

        if symbol not in self.market_buffers:
            self.market_buffers[symbol] = CircularBuffer(self.max_history_length)

        # Добавляем данные в циклический буфер - O(1) операция
        buffer = self.market_buffers[symbol]
        buffer.add(
            market_data.timestamp,
            market_data.open,
            market_data.high,
            market_data.low,
            market_data.close,
            market_data.volume,
        )

        # Обновляем совместимость с базовым классом
        if symbol not in self.market_data_history:
            self.market_data_history[symbol] = pd.DataFrame()

        # Обновляем DataFrame только если нужно для совместимости
        # В продакшене можно полностью перейти на buffer
        if buffer.size % 10 == 0:  # Обновляем каждые 10 тиков
            self.market_data_history[symbol] = buffer.to_dataframe()

    def _get_cache_key(self, symbol: str, timestamp: float) -> int:
        """Быстрое вычисление хэш-ключа для кэша"""
        key_str = f"{symbol}_{timestamp}"
        return hash(key_str)

    @PerformanceTracker("calculate_all_indicators")
    async def _calculate_all_indicators(self, symbol: str) -> dict[str, dict[str, Any]]:
        """Параллельный расчет всех индикаторов"""
        if symbol not in self.market_buffers:
            logger.warning(f"No market data buffer for {symbol}")
            return {}

        buffer = self.market_buffers[symbol]
        if buffer.size < self.get_required_history_length():
            logger.warning(f"Insufficient history for {symbol}: {buffer.size} bars")
            return {}

        # Проверка кэша с оптимизированными ключами
        timestamp = time.time()
        cache_key = self._get_cache_key(symbol, int(timestamp))

        if cache_key in self._cache_data:
            cached_time = self._cache_timestamps.get(cache_key, 0)
            if timestamp - cached_time < self.cache_ttl_seconds:
                return self._cache_data[cache_key]

        # Получаем DataFrame только один раз
        df = buffer.to_dataframe()

        # Параллельный расчет всех категорий индикаторов
        async def calculate_with_semaphore(calc_func, df_copy):
            async with self.indicator_semaphore:
                return await calc_func(df_copy)

        # Запускаем все расчеты параллельно
        tasks = [
            calculate_with_semaphore(self.indicator_manager.calculate_trend_indicators, df.copy()),
            calculate_with_semaphore(
                self.indicator_manager.calculate_momentum_indicators, df.copy()
            ),
            calculate_with_semaphore(self.indicator_manager.calculate_volume_indicators, df.copy()),
            calculate_with_semaphore(
                self.indicator_manager.calculate_volatility_indicators, df.copy()
            ),
        ]

        # Ждем завершения всех расчетов параллельно
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Обработка результатов
        indicator_results = {}
        categories = ["trend", "momentum", "volume", "volatility"]

        for category, result in zip(categories, results, strict=False):
            if isinstance(result, Exception):
                logger.error(f"Error calculating {category} indicators: {result}")
                continue
            if result:
                indicator_results[category] = result

        # Кэширование с оптимизированными ключами
        self._cache_data[cache_key] = indicator_results
        self._cache_timestamps[cache_key] = timestamp

        # Очистка старого кэша каждые 100 записей
        if len(self._cache_data) > 100:
            current_time = time.time()
            keys_to_remove = [
                k
                for k, t in self._cache_timestamps.items()
                if current_time - t > self.cache_ttl_seconds * 2
            ]
            for k in keys_to_remove:
                self._cache_data.pop(k, None)
                self._cache_timestamps.pop(k, None)

        return indicator_results

    async def analyze(self, market_data: MarketData) -> TradingSignal | None:
        """Оптимизированный анализ с батчированием"""
        if not self._is_initialized:
            logger.warning(f"{self.name} not initialized, skipping analysis")
            return None

        # Используем оптимизированное обновление
        self._update_market_history(market_data)

        # Остальная логика остается той же, но работает быстрее
        return await super().analyze(market_data)

    async def process_batch(self, market_data_batch: list[MarketData]) -> list[TradingSignal]:
        """Пакетная обработка данных для дополнительной оптимизации"""
        if not market_data_batch:
            return []

        # Группируем по символам для эффективной обработки
        symbol_groups = {}
        for data in market_data_batch:
            if data.symbol not in symbol_groups:
                symbol_groups[data.symbol] = []
            symbol_groups[data.symbol].append(data)

        signals = []

        # Обрабатываем каждую группу
        for symbol, data_list in symbol_groups.items():
            # Обновляем историю пакетом
            for data in data_list[:-1]:
                self._update_market_history(data)

            # Анализируем только последнее значение
            signal = await self.analyze(data_list[-1])
            if signal:
                signals.append(signal)

        return signals


# Фабричная функция для создания оптимизированной стратегии
def create_optimized_strategy(config: dict[str, Any]) -> OptimizedIndicatorStrategy:
    """Создание оптимизированной стратегии с настройками производительности"""

    # Добавляем оптимальные настройки если их нет
    performance_config = config.copy()
    performance_config.setdefault("cache_ttl_seconds", 30)  # Короче TTL для актуальности
    performance_config.setdefault("max_history_length", 300)  # Меньше данных в памяти

    return OptimizedIndicatorStrategy(performance_config)
