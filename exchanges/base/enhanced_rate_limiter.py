"""
Улучшенный rate limiter с кешированием и умными лимитами
"""

import asyncio
import hashlib
import json
import time
from collections import defaultdict, deque
from typing import Any, Dict, Optional, Tuple

from core.logger import setup_logger

logger = setup_logger(__name__)


class EnhancedRateLimiter:
    """
    Продвинутый rate limiter с:
    - Кешированием результатов
    - Exponential backoff
    - Специфичными лимитами для каждой биржи
    - Умным планированием запросов
    """

    # Лимиты для Bybit (https://bybit-exchange.github.io/docs/v5/rate-limit)
    BYBIT_LIMITS = {
        "default": {"requests": 120, "window": 60},  # 120 запросов в минуту
        "get_klines": {
            "requests": 60,
            "window": 60,
        },  # 60 запросов в минуту для исторических данных
        "get_tickers": {"requests": 120, "window": 60},
        "get_orderbook": {"requests": 100, "window": 60},
        "place_order": {"requests": 10, "window": 1},  # 10 ордеров в секунду
        "cancel_order": {"requests": 10, "window": 1},
        "get_positions": {"requests": 120, "window": 60},
        "get_orders": {"requests": 120, "window": 60},
        "get_balances": {"requests": 120, "window": 60},
    }

    def __init__(
        self,
        exchange: str = "bybit",
        enable_cache: bool = True,
        cache_ttl: int = 60,
        max_retries: int = 3,
    ):
        """
        Args:
            exchange: Название биржи
            enable_cache: Включить кеширование результатов
            cache_ttl: Время жизни кеша в секундах
            max_retries: Максимальное количество повторов
        """
        self.exchange = exchange.lower()
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.max_retries = max_retries

        # Выбираем лимиты для биржи
        if self.exchange == "bybit":
            self.limits = self.BYBIT_LIMITS
        else:
            # Дефолтные безопасные лимиты
            self.limits = {"default": {"requests": 60, "window": 60}}

        # Трекеры запросов для каждого endpoint
        self.request_trackers: Dict[str, deque] = defaultdict(deque)

        # Кеш результатов
        self.cache: Dict[str, Tuple[Any, float]] = {}

        # Блокировки для каждого endpoint
        self.locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

        # Счетчики для статистики
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "rate_limited": 0,
            "retries": 0,
        }

        # Backoff состояние
        self.backoff_until: Dict[str, float] = {}

        logger.info(f"EnhancedRateLimiter инициализирован для {exchange}")

    async def acquire(
        self, endpoint: str = "default", cache_key: Optional[str] = None
    ) -> Optional[Any]:
        """
        Получить разрешение на запрос или вернуть кешированный результат

        Args:
            endpoint: Тип endpoint (get_klines, place_order и т.д.)
            cache_key: Ключ для кеширования

        Returns:
            Кешированный результат или None
        """
        # Проверяем кеш
        if self.enable_cache and cache_key:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                self.stats["cache_hits"] += 1
                return cached

        # Получаем лимиты для endpoint
        limit_config = self.limits.get(endpoint, self.limits["default"])
        max_requests = limit_config["requests"]
        window = limit_config["window"]

        async with self.locks[endpoint]:
            # Проверяем backoff
            if endpoint in self.backoff_until:
                wait_time = self.backoff_until[endpoint] - time.time()
                if wait_time > 0:
                    logger.warning(
                        f"⏳ Rate limit backoff для {endpoint}: ждем {wait_time:.1f}s"
                    )
                    await asyncio.sleep(wait_time)
                    del self.backoff_until[endpoint]

            # Очищаем старые записи
            current_time = time.time()
            tracker = self.request_trackers[endpoint]

            while tracker and tracker[0] < current_time - window:
                tracker.popleft()

            # Проверяем лимит
            if len(tracker) >= max_requests:
                # Вычисляем время ожидания
                oldest_request = tracker[0]
                wait_time = oldest_request + window - current_time

                if wait_time > 0:
                    self.stats["rate_limited"] += 1
                    logger.warning(
                        f"⚠️ Rate limit для {endpoint}: {len(tracker)}/{max_requests}, ждем {wait_time:.1f}s"
                    )
                    await asyncio.sleep(wait_time)

                    # Очищаем после ожидания
                    while tracker and tracker[0] < time.time() - window:
                        tracker.popleft()

            # Добавляем текущий запрос
            tracker.append(time.time())
            self.stats["total_requests"] += 1

        return None

    async def execute_with_retry(
        self,
        func,
        *args,
        endpoint: str = "default",
        cache_key: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        Выполнить функцию с rate limiting, retry и кешированием

        Args:
            func: Async функция для выполнения
            endpoint: Тип endpoint
            cache_key: Ключ для кеширования
            *args, **kwargs: Аргументы для функции

        Returns:
            Результат выполнения функции
        """
        # Проверяем кеш
        cached_result = await self.acquire(endpoint, cache_key)
        if cached_result is not None:
            return cached_result

        last_error = None
        backoff_delay = 1.0  # Начальная задержка для exponential backoff

        for attempt in range(self.max_retries):
            try:
                # Выполняем функцию
                result = await func(*args, **kwargs)

                # Кешируем результат
                if self.enable_cache and cache_key:
                    self._add_to_cache(cache_key, result)

                return result

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Проверяем типы ошибок
                if "rate limit" in error_str or "too many requests" in error_str:
                    self.stats["rate_limited"] += 1

                    # Устанавливаем backoff
                    self.backoff_until[endpoint] = time.time() + backoff_delay

                    logger.warning(
                        f"🔄 Rate limit hit для {endpoint}, попытка {attempt + 1}/{self.max_retries}, backoff {backoff_delay}s"
                    )

                    # Exponential backoff
                    await asyncio.sleep(backoff_delay)
                    backoff_delay = min(backoff_delay * 2, 60)  # Максимум 60 секунд

                    self.stats["retries"] += 1
                    continue

                elif "invalid api key" in error_str or "unauthorized" in error_str:
                    # Критическая ошибка, не повторяем
                    logger.error(f"❌ Критическая ошибка API: {e}")
                    raise

                else:
                    # Другие ошибки - повторяем с меньшей задержкой
                    logger.warning(
                        f"⚠️ Ошибка {endpoint}: {e}, попытка {attempt + 1}/{self.max_retries}"
                    )
                    await asyncio.sleep(min(backoff_delay, 5))
                    self.stats["retries"] += 1

        # Если все попытки исчерпаны
        logger.error(f"❌ Все {self.max_retries} попыток исчерпаны для {endpoint}")
        raise last_error

    def _get_cache_key(self, method: str, params: Dict[str, Any]) -> str:
        """Генерация ключа кеша"""
        # Создаем уникальный ключ на основе метода и параметров
        key_data = {"method": method, "params": params, "exchange": self.exchange}
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Получить данные из кеша"""
        if cache_key in self.cache:
            result, timestamp = self.cache[cache_key]

            # Проверяем TTL
            if time.time() - timestamp < self.cache_ttl:
                return result
            else:
                # Удаляем устаревшую запись
                del self.cache[cache_key]

        return None

    def _add_to_cache(self, cache_key: str, result: Any) -> None:
        """Добавить данные в кеш"""
        self.cache[cache_key] = (result, time.time())

        # Ограничиваем размер кеша
        if len(self.cache) > 1000:
            # Удаляем самые старые записи
            oldest_keys = sorted(self.cache.keys(), key=lambda k: self.cache[k][1])[
                :100
            ]

            for key in oldest_keys:
                del self.cache[key]

    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику"""
        cache_hit_rate = 0
        if self.stats["total_requests"] > 0:
            cache_hit_rate = (
                self.stats["cache_hits"] / self.stats["total_requests"]
            ) * 100

        return {
            "total_requests": self.stats["total_requests"],
            "cache_hits": self.stats["cache_hits"],
            "cache_hit_rate": f"{cache_hit_rate:.1f}%",
            "rate_limited": self.stats["rate_limited"],
            "retries": self.stats["retries"],
            "cache_size": len(self.cache),
            "active_trackers": len(self.request_trackers),
        }

    def reset_stats(self) -> None:
        """Сбросить статистику"""
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "rate_limited": 0,
            "retries": 0,
        }

    def clear_cache(self) -> None:
        """Очистить кеш"""
        self.cache.clear()
        logger.info("🗑️ Кеш rate limiter очищен")

    def get_cached(self, cache_key: str) -> Optional[Any]:
        """
        Получить кешированный результат

        Args:
            cache_key: Ключ кеша

        Returns:
            Кешированный результат или None
        """
        return self._get_from_cache(cache_key)

    async def check_and_wait(self, endpoint: str = "default") -> None:
        """
        Проверить rate limit и подождать если необходимо

        Args:
            endpoint: Тип endpoint
        """
        await self.acquire(endpoint)

    def cache_result(self, cache_key: str, result: Any) -> None:
        """
        Кешировать результат

        Args:
            cache_key: Ключ кеша
            result: Результат для кеширования
        """
        self._add_to_cache(cache_key, result)
