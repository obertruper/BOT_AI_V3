"""
Кеш рыночных данных для минимизации API запросов
"""

import asyncio
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from core.logger import setup_logger

logger = setup_logger(__name__)


class MarketDataCache:
    """
    Умный кеш для рыночных данных
    - Хранит исторические данные в памяти
    - Обновляет только последнюю свечу
    - Минимизирует API запросы
    """

    def __init__(self, cache_size: int = 1000, ttl_seconds: int = 60):
        """
        Args:
            cache_size: Максимальное количество свечей для каждого символа
            ttl_seconds: Время жизни последней свечи (для обновления)
        """
        # Основной кеш: symbol -> DataFrame с OHLCV данными
        self._data_cache: dict[str, pd.DataFrame] = {}

        # Метаданные кеша
        self._cache_metadata: dict[str, dict] = {}

        # Время последнего обновления для каждого символа
        self._last_update: dict[str, datetime] = {}

        # Блокировки для потокобезопасности
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

        # Настройки
        self.cache_size = cache_size
        self.ttl_seconds = ttl_seconds

        # Статистика
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "api_calls_saved": 0,
            "last_candles_updated": 0,
        }

        logger.info(f"MarketDataCache инициализирован: size={cache_size}, ttl={ttl_seconds}s")

    async def get_data(self, symbol: str, required_candles: int = 96) -> pd.DataFrame | None:
        """
        Получить данные из кеша

        Args:
            symbol: Торговый символ
            required_candles: Минимальное количество требуемых свечей

        Returns:
            DataFrame с OHLCV данными или None
        """
        async with self._locks[symbol]:
            if symbol in self._data_cache:
                df = self._data_cache[symbol]

                if len(df) >= required_candles:
                    self.stats["cache_hits"] += 1
                    self.stats["api_calls_saved"] += 1

                    # Проверяем актуальность последней свечи
                    if self._is_last_candle_stale(symbol):
                        # Помечаем что нужно обновить только последнюю свечу
                        self._cache_metadata[symbol]["needs_last_update"] = True

                    return df.copy()

            self.stats["cache_misses"] += 1
            return None

    async def update_data(
        self, symbol: str, new_data: pd.DataFrame, is_complete: bool = False
    ) -> None:
        """
        Обновить данные в кеше

        Args:
            symbol: Торговый символ
            new_data: Новые данные
            is_complete: True если это полная загрузка, False для инкрементального обновления
        """
        async with self._locks[symbol]:
            current_time = datetime.now(UTC)

            if is_complete:
                # Полная замена данных
                self._data_cache[symbol] = new_data.copy()
                self._cache_metadata[symbol] = {
                    "loaded_at": current_time,
                    "candles_count": len(new_data),
                    "needs_last_update": False,
                }
                logger.info(f"📊 {symbol}: Загружено {len(new_data)} исторических свечей в кеш")

            else:
                # Инкрементальное обновление
                if symbol in self._data_cache:
                    existing_df = self._data_cache[symbol]

                    # Объединяем данные, удаляя дубликаты по timestamp
                    combined_df = pd.concat([existing_df, new_data])
                    combined_df = combined_df[~combined_df.index.duplicated(keep="last")]
                    combined_df = combined_df.sort_index()

                    # Ограничиваем размер кеша
                    if len(combined_df) > self.cache_size:
                        combined_df = combined_df.iloc[-self.cache_size :]

                    self._data_cache[symbol] = combined_df
                    self.stats["last_candles_updated"] += 1

                    logger.debug(f"🔄 {symbol}: Обновлена последняя свеча в кеше")
                else:
                    # Первая загрузка
                    self._data_cache[symbol] = new_data.copy()
                    self._cache_metadata[symbol] = {
                        "loaded_at": current_time,
                        "candles_count": len(new_data),
                        "needs_last_update": False,
                    }

            self._last_update[symbol] = current_time

    async def update_last_candle(self, symbol: str, last_candle: dict[str, Any]) -> None:
        """
        Обновить только последнюю свечу (real-time обновление)

        Args:
            symbol: Торговый символ
            last_candle: Данные последней свечи
        """
        async with self._locks[symbol]:
            if symbol not in self._data_cache:
                return

            df = self._data_cache[symbol]

            # Создаем timestamp для последней свечи
            timestamp = pd.Timestamp(last_candle.get("timestamp", datetime.now(UTC)), tz="UTC")

            # Обновляем последнюю строку если timestamp совпадает
            if len(df) > 0 and df.index[-1] == timestamp:
                # Обновляем существующую свечу
                df.loc[timestamp, "open"] = last_candle["open"]
                df.loc[timestamp, "high"] = last_candle["high"]
                df.loc[timestamp, "low"] = last_candle["low"]
                df.loc[timestamp, "close"] = last_candle["close"]
                df.loc[timestamp, "volume"] = last_candle["volume"]

                self.stats["last_candles_updated"] += 1
                logger.debug(f"📈 {symbol}: Обновлена текущая свеча {timestamp}")
            else:
                # Добавляем новую свечу
                new_row = pd.DataFrame([last_candle], index=[timestamp])
                self._data_cache[symbol] = pd.concat([df, new_row])

                # Ограничиваем размер
                if len(self._data_cache[symbol]) > self.cache_size:
                    self._data_cache[symbol] = self._data_cache[symbol].iloc[-self.cache_size :]

                logger.debug(f"📊 {symbol}: Добавлена новая свеча {timestamp}")

            self._last_update[symbol] = datetime.now(UTC)
            self._cache_metadata[symbol]["needs_last_update"] = False

    def _is_last_candle_stale(self, symbol: str) -> bool:
        """
        Проверить, устарела ли последняя свеча

        Args:
            symbol: Торговый символ

        Returns:
            True если свеча устарела и нужно обновление
        """
        if symbol not in self._last_update:
            return True

        age = (datetime.now(UTC) - self._last_update[symbol]).total_seconds()
        return age > self.ttl_seconds

    def needs_update(self, symbol: str) -> tuple[bool, str]:
        """
        Проверить, нужно ли обновление данных

        Returns:
            (needs_update, update_type) где update_type: 'full', 'last', 'none'
        """
        if symbol not in self._data_cache:
            return True, "full"

        df = self._data_cache[symbol]

        # Проверяем достаточность данных
        if len(df) < 96:  # Минимум для ML
            return True, "full"

        # Проверяем актуальность последней свечи
        if self._is_last_candle_stale(symbol):
            return True, "last"

        # Проверяем метку обновления
        metadata = self._cache_metadata.get(symbol, {})
        if metadata.get("needs_last_update", False):
            return True, "last"

        return False, "none"

    def get_stats(self) -> dict[str, Any]:
        """Получить статистику кеша"""
        total_requests = self.stats["cache_hits"] + self.stats["cache_misses"]
        hit_rate = (self.stats["cache_hits"] / total_requests * 100) if total_requests > 0 else 0

        return {
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "hit_rate": f"{hit_rate:.1f}%",
            "api_calls_saved": self.stats["api_calls_saved"],
            "last_candles_updated": self.stats["last_candles_updated"],
            "symbols_cached": len(self._data_cache),
            "total_candles": sum(len(df) for df in self._data_cache.values()),
        }

    def clear_cache(self, symbol: str | None = None) -> None:
        """
        Очистить кеш

        Args:
            symbol: Если указан, очистить только для этого символа
        """
        if symbol:
            self._data_cache.pop(symbol, None)
            self._cache_metadata.pop(symbol, None)
            self._last_update.pop(symbol, None)
            logger.info(f"🗑️ Кеш очищен для {symbol}")
        else:
            self._data_cache.clear()
            self._cache_metadata.clear()
            self._last_update.clear()
            self.stats = {
                "cache_hits": 0,
                "cache_misses": 0,
                "api_calls_saved": 0,
                "last_candles_updated": 0,
            }
            logger.info("🗑️ Весь кеш очищен")

    async def preload_symbols(
        self, symbols: list[str], data_loader_func, required_candles: int = 1000
    ) -> None:
        """
        Предзагрузка данных для списка символов

        Args:
            symbols: Список символов для загрузки
            data_loader_func: Async функция для загрузки данных
            required_candles: Количество свечей для загрузки
        """
        logger.info(f"📥 Предзагрузка данных для {len(symbols)} символов...")

        tasks = []
        for symbol in symbols:
            if symbol not in self._data_cache:
                task = asyncio.create_task(
                    self._preload_single(symbol, data_loader_func, required_candles)
                )
                tasks.append(task)

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            logger.info(f"✅ Предзагружено {success_count}/{len(tasks)} символов")

    async def _preload_single(self, symbol: str, data_loader_func, required_candles: int) -> None:
        """Предзагрузка данных для одного символа"""
        try:
            data = await data_loader_func(symbol, limit=required_candles)
            if data is not None and len(data) > 0:
                await self.update_data(symbol, data, is_complete=True)
        except Exception as e:
            logger.error(f"Ошибка предзагрузки {symbol}: {e}")
            raise
