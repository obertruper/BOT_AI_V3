"""
Универсальный лимитер скорости для API запросов к биржам
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

import redis.asyncio as redis

logger = logging.getLogger(__name__)


@dataclass
class RateLimit:
    """Лимит скорости для API endpoint"""

    requests_per_second: float
    requests_per_minute: int
    burst_limit: int  # Максимальный burst
    weight: int = 1  # Вес запроса


@dataclass
class ExchangeRateLimits:
    """Лимиты для конкретной биржи"""

    exchange: str
    global_limit: RateLimit
    endpoint_limits: dict[str, RateLimit] = field(default_factory=dict)
    ip_weight_per_minute: int = 1200  # Общий вес IP в минуту
    uid_weight_per_minute: int = 6000  # Общий вес UID в минуту


class RateLimiter:
    """
    Универсальный лимитер скорости для всех бирж

    Основные функции:
    - Контроль скорости запросов по биржам и endpoint'ам
    - Интеллектуальная очередь запросов
    - Автоматическая задержка при превышении лимитов
    - Мониторинг и статистика использования
    - Поддержка burst запросов
    """

    def __init__(self, redis_client: redis.Redis | None = None):
        self.redis_client = redis_client
        self.local_counters: dict[str, deque] = defaultdict(deque)
        self.request_queues: dict[str, asyncio.Queue] = {}
        self.processing_tasks: dict[str, asyncio.Task] = {}
        self.stats = defaultdict(
            lambda: {
                "total_requests": 0,
                "blocked_requests": 0,
                "average_wait_time": 0,
                "max_wait_time": 0,
                "queue_size": 0,
            }
        )

        # Настройки лимитов для каждой биржи
        self.exchange_limits = self._init_exchange_limits()

        # Инициализация Redis
        if not self.redis_client:
            self._init_redis()

    def _init_redis(self):
        """Инициализация Redis клиента"""
        try:
            self.redis_client = redis.from_url("redis://localhost:6379/3")  # DB 3 для rate limiting
            logger.info("✅ Redis клиент инициализирован для rate limiter")
        except Exception as e:
            logger.warning(f"⚠️  Redis недоступен для rate limiter: {e}")
            self.redis_client = None

    def _init_exchange_limits(self) -> dict[str, ExchangeRateLimits]:
        """Инициализация лимитов для бирж"""
        limits = {}

        # Bybit
        limits["bybit"] = ExchangeRateLimits(
            exchange="bybit",
            global_limit=RateLimit(requests_per_second=10, requests_per_minute=600, burst_limit=50),
            endpoint_limits={
                "order": RateLimit(
                    requests_per_second=5, requests_per_minute=100, burst_limit=10, weight=1
                ),
                "cancel_order": RateLimit(
                    requests_per_second=10, requests_per_minute=100, burst_limit=10, weight=1
                ),
                "get_positions": RateLimit(
                    requests_per_second=5, requests_per_minute=120, burst_limit=5, weight=1
                ),
                "get_balance": RateLimit(
                    requests_per_second=2, requests_per_minute=120, burst_limit=5, weight=1
                ),
                "market_data": RateLimit(
                    requests_per_second=50, requests_per_minute=1200, burst_limit=100, weight=1
                ),
            },
            ip_weight_per_minute=1200,
            uid_weight_per_minute=6000,
        )

        # Binance
        limits["binance"] = ExchangeRateLimits(
            exchange="binance",
            global_limit=RateLimit(
                requests_per_second=10, requests_per_minute=1200, burst_limit=20
            ),
            endpoint_limits={
                "order": RateLimit(
                    requests_per_second=1, requests_per_minute=60, burst_limit=5, weight=1
                ),
                "cancel_order": RateLimit(
                    requests_per_second=1, requests_per_minute=100, burst_limit=10, weight=1
                ),
                "get_positions": RateLimit(
                    requests_per_second=1, requests_per_minute=10, burst_limit=2, weight=5
                ),
                "get_balance": RateLimit(
                    requests_per_second=1, requests_per_minute=10, burst_limit=2, weight=5
                ),
                "market_data": RateLimit(
                    requests_per_second=20, requests_per_minute=1200, burst_limit=50, weight=1
                ),
            },
        )

        # OKX
        limits["okx"] = ExchangeRateLimits(
            exchange="okx",
            global_limit=RateLimit(requests_per_second=10, requests_per_minute=600, burst_limit=30),
            endpoint_limits={
                "order": RateLimit(
                    requests_per_second=5, requests_per_minute=60, burst_limit=10, weight=1
                ),
                "cancel_order": RateLimit(
                    requests_per_second=10, requests_per_minute=60, burst_limit=15, weight=1
                ),
                "get_positions": RateLimit(
                    requests_per_second=5, requests_per_minute=10, burst_limit=3, weight=1
                ),
                "get_balance": RateLimit(
                    requests_per_second=1, requests_per_minute=10, burst_limit=2, weight=1
                ),
                "market_data": RateLimit(
                    requests_per_second=20, requests_per_minute=600, burst_limit=40, weight=1
                ),
            },
        )

        # Gate.io
        limits["gate"] = ExchangeRateLimits(
            exchange="gate",
            global_limit=RateLimit(requests_per_second=10, requests_per_minute=900, burst_limit=30),
            endpoint_limits={
                "order": RateLimit(
                    requests_per_second=10, requests_per_minute=300, burst_limit=20, weight=1
                ),
                "cancel_order": RateLimit(
                    requests_per_second=10, requests_per_minute=300, burst_limit=20, weight=1
                ),
                "get_positions": RateLimit(
                    requests_per_second=10, requests_per_minute=300, burst_limit=10, weight=1
                ),
                "get_balance": RateLimit(
                    requests_per_second=10, requests_per_minute=300, burst_limit=10, weight=1
                ),
                "market_data": RateLimit(
                    requests_per_second=10, requests_per_minute=900, burst_limit=30, weight=1
                ),
            },
        )

        # Добавляем остальные биржи с дефолтными лимитами
        for exchange in ["kucoin", "htx", "bingx"]:
            limits[exchange] = ExchangeRateLimits(
                exchange=exchange,
                global_limit=RateLimit(
                    requests_per_second=5, requests_per_minute=300, burst_limit=20
                ),
                endpoint_limits={
                    "order": RateLimit(
                        requests_per_second=2, requests_per_minute=60, burst_limit=5, weight=1
                    ),
                    "cancel_order": RateLimit(
                        requests_per_second=5, requests_per_minute=100, burst_limit=10, weight=1
                    ),
                    "get_positions": RateLimit(
                        requests_per_second=2, requests_per_minute=60, burst_limit=3, weight=1
                    ),
                    "get_balance": RateLimit(
                        requests_per_second=1, requests_per_minute=30, burst_limit=2, weight=1
                    ),
                    "market_data": RateLimit(
                        requests_per_second=10, requests_per_minute=300, burst_limit=20, weight=1
                    ),
                },
            )

        return limits

    async def acquire(
        self, exchange: str, endpoint: str = "default", weight: int | None = None
    ) -> float:
        """
        Получение разрешения на выполнение запроса

        Args:
            exchange: Название биржи
            endpoint: Название endpoint'а
            weight: Вес запроса (если не указан, берется из конфигурации)

        Returns:
            Время задержки в секундах (0 если задержки нет)
        """
        start_time = time.time()

        if exchange not in self.exchange_limits:
            logger.warning(f"⚠️  Неизвестная биржа '{exchange}', используем дефолтные лимиты")
            exchange = "default"

        exchange_config = self.exchange_limits.get(exchange)
        if not exchange_config:
            # Дефолтная конфигурация
            exchange_config = ExchangeRateLimits(
                exchange=exchange,
                global_limit=RateLimit(
                    requests_per_second=5, requests_per_minute=300, burst_limit=10
                ),
            )

        # Определяем лимит для endpoint'а
        endpoint_limit = exchange_config.endpoint_limits.get(endpoint, exchange_config.global_limit)

        # Определяем вес запроса
        if weight is None:
            weight = endpoint_limit.weight

        # Ключи для счетчиков
        global_key = f"rate_limit:{exchange}:global"
        endpoint_key = f"rate_limit:{exchange}:{endpoint}"

        # Проверяем лимиты и ожидаем если необходимо
        wait_time = await self._check_and_wait(global_key, exchange_config.global_limit, weight)
        if endpoint != "default":
            endpoint_wait = await self._check_and_wait(endpoint_key, endpoint_limit, weight)
            wait_time = max(wait_time, endpoint_wait)

        # Обновляем статистику
        total_time = time.time() - start_time
        self._update_stats(exchange, endpoint, total_time, wait_time > 0)

        return wait_time

    async def _check_and_wait(self, key: str, limit: RateLimit, weight: int) -> float:
        """Проверка лимитов и ожидание если необходимо"""
        now = time.time()
        wait_time = 0

        # Проверяем через Redis если доступен
        if self.redis_client:
            wait_time = await self._check_redis_limit(key, limit, weight, now)
        else:
            # Fallback на локальные счетчики
            wait_time = await self._check_local_limit(key, limit, weight, now)

        if wait_time > 0:
            logger.debug(f"⏱️  Задержка {wait_time:.2f}с для ключа {key}")
            await asyncio.sleep(wait_time)

        return wait_time

    async def _check_redis_limit(
        self, key: str, limit: RateLimit, weight: int, now: float
    ) -> float:
        """Проверка лимитов через Redis"""
        try:
            # Используем Redis sliding window
            pipeline = self.redis_client.pipeline()

            # Очищаем старые записи (старше 1 минуты)
            minute_ago = now - 60
            await pipeline.zremrangebyscore(key, 0, minute_ago)

            # Получаем текущее количество запросов
            current_requests = await pipeline.zcard(key)

            # Проверяем лимит на минуту
            if current_requests >= limit.requests_per_minute:
                # Находим время следующего доступного слота
                oldest_request = await self.redis_client.zrange(key, 0, 0, withscores=True)
                if oldest_request:
                    next_available = oldest_request[0][1] + 60 - now
                    return max(0, next_available)

            # Проверяем лимит на секунду (последние запросы)
            second_ago = now - 1
            recent_requests = await self.redis_client.zcount(key, second_ago, now)

            if recent_requests >= limit.requests_per_second:
                # Ждем до следующей секунды
                return 1.0 - (now % 1.0)

            # Добавляем текущий запрос
            await pipeline.zadd(key, {f"{now}:{weight}": now})
            await pipeline.expire(key, 60)  # TTL 1 минута
            await pipeline.execute()

            return 0

        except Exception as e:
            logger.warning(f"⚠️  Ошибка Redis rate limit: {e}")
            # Fallback на локальные счетчики
            return await self._check_local_limit(key, limit, weight, now)

    async def _check_local_limit(
        self, key: str, limit: RateLimit, weight: int, now: float
    ) -> float:
        """Проверка лимитов через локальные счетчики"""
        if key not in self.local_counters:
            self.local_counters[key] = deque()

        counter = self.local_counters[key]

        # Очищаем старые записи
        while counter and counter[0] <= now - 60:
            counter.popleft()

        # Проверяем лимит на минуту
        if len(counter) >= limit.requests_per_minute:
            next_available = counter[0] + 60 - now
            return max(0, next_available)

        # Проверяем лимит на секунду
        recent_count = sum(1 for timestamp in counter if timestamp > now - 1)
        if recent_count >= limit.requests_per_second:
            return 1.0 - (now % 1.0)

        # Добавляем запрос
        counter.append(now)

        return 0

    def _update_stats(self, exchange: str, endpoint: str, total_time: float, was_blocked: bool):
        """Обновление статистики"""
        key = f"{exchange}:{endpoint}"
        stats = self.stats[key]

        stats["total_requests"] += 1
        if was_blocked:
            stats["blocked_requests"] += 1

        # Обновляем среднее время ожидания
        if stats["total_requests"] == 1:
            stats["average_wait_time"] = total_time
        else:
            stats["average_wait_time"] = (
                stats["average_wait_time"] * (stats["total_requests"] - 1) + total_time
            ) / stats["total_requests"]

        # Обновляем максимальное время ожидания
        stats["max_wait_time"] = max(stats["max_wait_time"], total_time)

    def get_stats(self, exchange: str | None = None) -> dict[str, Any]:
        """Получение статистики использования"""
        if exchange:
            # Статистика по конкретной бирже
            exchange_stats = {}
            for key, stats in self.stats.items():
                if key.startswith(f"{exchange}:"):
                    endpoint = key.split(":", 1)[1]
                    exchange_stats[endpoint] = stats.copy()
            return exchange_stats
        else:
            # Общая статистика
            return dict(self.stats)

    def reset_stats(self, exchange: str | None = None):
        """Сброс статистики"""
        if exchange:
            keys_to_remove = [key for key in self.stats.keys() if key.startswith(f"{exchange}:")]
            for key in keys_to_remove:
                del self.stats[key]
        else:
            self.stats.clear()

    async def get_current_usage(self, exchange: str) -> dict[str, Any]:
        """Получение текущего использования лимитов"""
        if exchange not in self.exchange_limits:
            return {}

        exchange_config = self.exchange_limits[exchange]
        now = time.time()
        usage = {}

        # Проверяем глобальные лимиты
        global_key = f"rate_limit:{exchange}:global"
        if self.redis_client:
            try:
                minute_ago = now - 60
                total_minute = await self.redis_client.zcount(global_key, minute_ago, now)
                second_ago = now - 1
                total_second = await self.redis_client.zcount(global_key, second_ago, now)

                usage["global"] = {
                    "per_minute": {
                        "current": total_minute,
                        "limit": exchange_config.global_limit.requests_per_minute,
                        "percentage": (
                            total_minute / exchange_config.global_limit.requests_per_minute
                        )
                        * 100,
                    },
                    "per_second": {
                        "current": total_second,
                        "limit": exchange_config.global_limit.requests_per_second,
                        "percentage": (
                            total_second / exchange_config.global_limit.requests_per_second
                        )
                        * 100,
                    },
                }
            except Exception as e:
                logger.warning(f"⚠️  Ошибка получения текущего использования: {e}")

        # Проверяем лимиты по endpoint'ам
        for endpoint, limit in exchange_config.endpoint_limits.items():
            endpoint_key = f"rate_limit:{exchange}:{endpoint}"
            if self.redis_client:
                try:
                    minute_ago = now - 60
                    endpoint_minute = await self.redis_client.zcount(endpoint_key, minute_ago, now)
                    second_ago = now - 1
                    endpoint_second = await self.redis_client.zcount(endpoint_key, second_ago, now)

                    usage[endpoint] = {
                        "per_minute": {
                            "current": endpoint_minute,
                            "limit": limit.requests_per_minute,
                            "percentage": (endpoint_minute / limit.requests_per_minute) * 100,
                        },
                        "per_second": {
                            "current": endpoint_second,
                            "limit": limit.requests_per_second,
                            "percentage": (endpoint_second / limit.requests_per_second) * 100,
                        },
                    }
                except Exception as e:
                    logger.warning(f"⚠️  Ошибка получения использования endpoint '{endpoint}': {e}")

        return usage

    async def cleanup_old_data(self, older_than_minutes: int = 60):
        """Очистка старых данных из счетчиков"""
        try:
            if self.redis_client:
                # Очистка Redis
                cutoff_time = time.time() - (older_than_minutes * 60)

                # Получаем все ключи rate_limit
                keys = await self.redis_client.keys("rate_limit:*")

                for key in keys:
                    await self.redis_client.zremrangebyscore(key, 0, cutoff_time)

                logger.info(
                    f"🧹 Очищены старые данные rate limiter из Redis для {len(keys)} ключей"
                )

            # Очистка локальных счетчиков
            now = time.time()
            cutoff_time = now - (older_than_minutes * 60)

            for key, counter in self.local_counters.items():
                # Удаляем старые записи
                while counter and counter[0] <= cutoff_time:
                    counter.popleft()

            # Удаляем пустые счетчики
            empty_keys = [key for key, counter in self.local_counters.items() if not counter]
            for key in empty_keys:
                del self.local_counters[key]

            logger.info(
                f"🧹 Очищены локальные счетчики rate limiter, удалено {len(empty_keys)} пустых ключей"
            )

        except Exception as e:
            logger.error(f"❌ Ошибка очистки данных rate limiter: {e}")


# Глобальный экземпляр rate limiter
rate_limiter = RateLimiter()
