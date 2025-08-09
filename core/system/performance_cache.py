#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Система кеширования для критических операций
Обеспечивает высокую производительность через intelligent caching
"""

import asyncio
import time
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional
from weakref import WeakValueDictionary

from core.logger import setup_logger

logger = setup_logger(__name__)


class PerformanceCache:
    """
    Высокопроизводительная система кеширования с:
    - LRU eviction policy
    - TTL для записей
    - Batch operations
    - Memory pressure monitoring
    """

    def __init__(self, max_size: int = 10000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl

        # Основное хранилище
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}
        self._access_order = deque()
        self._access_count = defaultdict(int)

        # TTL tracking
        self._expiry_times: Dict[str, float] = {}

        # Batch операции
        self._batch_queue: List[Dict[str, Any]] = []
        self._batch_lock = asyncio.Lock()

        # Метрики производительности
        self.hits = 0
        self.misses = 0
        self.evictions = 0

        # Weak references для автоочистки
        self._weak_refs: WeakValueDictionary = WeakValueDictionary()

        # Фоновая очистка
        self._cleanup_task = None

    def start_cleanup_task(self):
        """Запуск фоновой задачи очистки"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def _cleanup_loop(self):
        """Фоновая очистка устаревших записей"""
        while True:
            try:
                await asyncio.sleep(60)  # Очистка каждую минуту
                await self._cleanup_expired()
                await self._check_memory_pressure()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в cleanup loop: {e}")

    async def _cleanup_expired(self):
        """Удаление устаревших записей"""
        current_time = time.time()
        expired_keys = [
            key for key, expiry in self._expiry_times.items() if expiry < current_time
        ]

        for key in expired_keys:
            await self._remove_key(key)

        if expired_keys:
            logger.debug(f"Удалено {len(expired_keys)} устаревших записей из кеша")

    async def _check_memory_pressure(self):
        """Проверка и освобождение памяти при необходимости"""
        if len(self._cache) > self.max_size * 0.9:
            # Удаляем 20% наименее используемых записей
            to_remove = int(self.max_size * 0.2)

            # Сортируем по частоте использования и времени доступа
            sorted_keys = sorted(
                self._cache.keys(),
                key=lambda k: (self._access_count[k], self._access_times.get(k, 0)),
            )

            for key in sorted_keys[:to_remove]:
                await self._remove_key(key)
                self.evictions += 1

            logger.info(f"Освобождено {to_remove} записей кеша из-за memory pressure")

    async def _remove_key(self, key: str):
        """Безопасное удаление ключа из всех структур"""
        self._cache.pop(key, None)
        self._access_times.pop(key, None)
        self._expiry_times.pop(key, None)
        self._access_count.pop(key, None)

        # Удаляем из очереди доступа
        try:
            self._access_order.remove(key)
        except ValueError:
            pass

    async def get(self, key: str) -> Optional[Any]:
        """Получение значения из кеша"""
        current_time = time.time()

        # Проверяем TTL
        if key in self._expiry_times and self._expiry_times[key] < current_time:
            await self._remove_key(key)
            self.misses += 1
            return None

        if key in self._cache:
            # Обновляем статистику доступа
            self._access_times[key] = current_time
            self._access_count[key] += 1
            self._access_order.append(key)

            # Ограничиваем размер очереди доступа
            if len(self._access_order) > self.max_size:
                self._access_order.popleft()

            self.hits += 1
            return self._cache[key]["value"]

        self.misses += 1
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Сохранение значения в кеш"""
        current_time = time.time()
        ttl = ttl or self.default_ttl

        # Проверяем размер кеша
        if len(self._cache) >= self.max_size and key not in self._cache:
            await self._evict_lru()

        self._cache[key] = {"value": value, "created_at": current_time}
        self._access_times[key] = current_time
        self._expiry_times[key] = current_time + ttl
        self._access_count[key] += 1
        self._access_order.append(key)

    async def _evict_lru(self):
        """Удаление наименее используемой записи"""
        if not self._access_order:
            return

        # Находим ключ с самым старым временем доступа
        lru_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
        await self._remove_key(lru_key)
        self.evictions += 1

    async def delete(self, key: str) -> bool:
        """Удаление ключа из кеша"""
        if key in self._cache:
            await self._remove_key(key)
            return True
        return False

    async def clear(self):
        """Очистка всего кеша"""
        self._cache.clear()
        self._access_times.clear()
        self._access_order.clear()
        self._expiry_times.clear()
        self._access_count.clear()

    # Batch операции для высокой производительности
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Получение множественных значений"""
        result = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value
        return result

    async def set_many(self, items: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """Сохранение множественных значений"""
        async with self._batch_lock:
            for key, value in items.items():
                await self.set(key, value, ttl)

    async def batch_update(self, operations: List[Dict[str, Any]]) -> List[Any]:
        """Выполнение batch операций"""
        results = []
        async with self._batch_lock:
            for op in operations:
                op_type = op.get("type")
                if op_type == "get":
                    result = await self.get(op["key"])
                    results.append(result)
                elif op_type == "set":
                    await self.set(op["key"], op["value"], op.get("ttl"))
                    results.append(True)
                elif op_type == "delete":
                    result = await self.delete(op["key"])
                    results.append(result)
        return results

    # Специальные методы для торговых данных
    async def cache_market_data(
        self, symbol: str, timeframe: str, data: Any, ttl: int = 60
    ):
        """Кеширование рыночных данных"""
        key = f"market_data:{symbol}:{timeframe}"
        await self.set(key, data, ttl)

    async def get_market_data(self, symbol: str, timeframe: str) -> Optional[Any]:
        """Получение рыночных данных"""
        key = f"market_data:{symbol}:{timeframe}"
        return await self.get(key)

    async def cache_indicator(
        self, symbol: str, indicator: str, period: int, data: Any, ttl: int = 30
    ):
        """Кеширование технических индикаторов"""
        key = f"indicator:{symbol}:{indicator}:{period}"
        await self.set(key, data, ttl)

    async def get_indicator(
        self, symbol: str, indicator: str, period: int
    ) -> Optional[Any]:
        """Получение технических индикаторов"""
        key = f"indicator:{symbol}:{indicator}:{period}"
        return await self.get(key)

    # Методы для мониторинга производительности
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики кеша"""
        total_requests = self.hits + self.misses
        hit_ratio = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_ratio": round(hit_ratio, 2),
            "memory_usage_percent": round(len(self._cache) / self.max_size * 100, 2),
        }

    def reset_stats(self):
        """Сброс статистики"""
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    async def stop(self):
        """Остановка фоновых задач"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass


# Глобальный экземпляр кеша
performance_cache = PerformanceCache()


# Декораторы для автоматического кеширования
def cached(ttl: int = 300, key_prefix: str = ""):
    """Декоратор для автоматического кеширования результатов функций"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Генерируем ключ кеша
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(filter(None, key_parts))

            # Пытаемся получить из кеша
            result = await performance_cache.get(cache_key)
            if result is not None:
                return result

            # Выполняем функцию и кешируем результат
            result = await func(*args, **kwargs)
            await performance_cache.set(cache_key, result, ttl)
            return result

        return wrapper

    return decorator


# Вспомогательные функции
async def warm_up_cache():
    """Предварительный прогрев кеша"""
    logger.info("🔥 Прогрев кеша производительности...")

    # Здесь можно добавить предварительную загрузку часто используемых данных
    # Например, основные торговые пары, популярные индикаторы и т.д.

    common_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    common_indicators = ["RSI", "MACD", "EMA"]

    for symbol in common_symbols:
        for indicator in common_indicators:
            cache_key = f"warmup:{symbol}:{indicator}"
            await performance_cache.set(cache_key, {"warmed": True}, 60)

    logger.info(
        f"✅ Кеш прогрет: {len(common_symbols) * len(common_indicators)} записей"
    )


async def get_cache_health() -> Dict[str, Any]:
    """Проверка здоровья кеша"""
    stats = performance_cache.get_stats()

    health_status = "healthy"
    if stats["hit_ratio"] < 50:
        health_status = "poor_performance"
    elif stats["memory_usage_percent"] > 90:
        health_status = "memory_pressure"

    return {
        "status": health_status,
        "stats": stats,
        "recommendations": _get_cache_recommendations(stats),
    }


def _get_cache_recommendations(stats: Dict[str, Any]) -> List[str]:
    """Получение рекомендаций по оптимизации кеша"""
    recommendations = []

    if stats["hit_ratio"] < 50:
        recommendations.append("Увеличьте TTL для часто используемых данных")
        recommendations.append("Рассмотрите возможность увеличения размера кеша")

    if stats["memory_usage_percent"] > 90:
        recommendations.append("Увеличьте максимальный размер кеша")
        recommendations.append("Уменьшите TTL для редко используемых данных")

    if stats["evictions"] > stats["hits"] * 0.1:
        recommendations.append("Слишком много вытеснений - увеличьте размер кеша")

    return recommendations
