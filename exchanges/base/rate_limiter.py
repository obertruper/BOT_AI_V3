"""
Универсальный Rate Limiter для всех бирж BOT_Trading v3.0

Компонент для умного управления API rate limits с поддержкой:
- Индивидуальных лимитов для каждой биржи
- Sliding window алгоритма
- Автоматического backoff при превышении лимитов
- Приоритизации критических запросов
- Мониторинга и логирования
"""

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from core.logger import setup_logger


class RequestPriority(Enum):
    """Приоритеты запросов"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ExchangeRateLimit:
    """Конфигурация rate limit для биржи"""

    # Базовые лимиты (запросов в минуту)
    public_limit: int = 1200  # Публичные API
    private_limit: int = 600  # Приватные API
    websocket_limit: int = 10  # WebSocket подключения

    # Специфичные эндпоинты
    order_limit: int = 100  # Ордеры
    position_limit: int = 50  # Позиции
    balance_limit: int = 20  # Балансы

    # Burst allowance (разрешенные всплески)
    burst_allowance: int = 10
    burst_window_seconds: int = 5

    # Penalty на превышение
    penalty_multiplier: float = 2.0
    penalty_duration_seconds: int = 60

    # Backoff settings
    backoff_base_delay: float = 1.0
    backoff_max_delay: float = 300.0
    backoff_multiplier: float = 2.0


@dataclass
class RequestRecord:
    """Запись о выполненном запросе"""

    timestamp: float
    endpoint: str
    priority: RequestPriority
    success: bool
    response_time: float = 0.0
    retry_after: int | None = None


@dataclass
class RateLimitState:
    """Состояние rate limiter для биржи"""

    # История запросов (sliding window)
    public_requests: deque = field(default_factory=deque)
    private_requests: deque = field(default_factory=deque)
    order_requests: deque = field(default_factory=deque)

    # Penalty состояние
    penalty_until: float = 0.0
    penalty_multiplier: float = 1.0

    # Backoff состояние
    consecutive_errors: int = 0
    last_error_time: float = 0.0
    backoff_delay: float = 0.0

    # Статистика
    total_requests: int = 0
    successful_requests: int = 0
    rate_limited_requests: int = 0

    # Очередь ожидающих запросов
    pending_queue: list[tuple[RequestPriority, asyncio.Event, str]] = field(default_factory=list)


class UniversalRateLimiter:
    """
    Универсальный rate limiter для всех бирж

    Поддерживает:
    - Sliding window алгоритм для точного контроля лимитов
    - Приоритизацию запросов
    - Автоматический backoff при ошибках
    - Burst handling для кратковременных всплесков
    - Индивидуальные настройки для каждой биржи
    """

    def __init__(self):
        self.logger = setup_logger("rate_limiter")

        # Конфигурации для разных бирж
        self.exchange_configs: dict[str, ExchangeRateLimit] = {}

        # Состояния для каждой биржи
        self.exchange_states: dict[str, RateLimitState] = defaultdict(RateLimitState)

        # Блокировки для thread safety
        self.locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

        # Таймер для очистки старых записей
        self._cleanup_task: asyncio.Task | None = None

        # Инициализация стандартных конфигураций
        self._init_exchange_configs()

        # Запуск фоновых задач
        self._start_background_tasks()

    def _init_exchange_configs(self):
        """Инициализация стандартных конфигураций для бирж"""

        # Bybit - уменьшаем лимиты для предотвращения rate limit errors
        self.exchange_configs["bybit"] = ExchangeRateLimit(
            public_limit=30,  # Было 120 - снижаем в 4 раза
            private_limit=20,  # Было 120 - снижаем в 6 раз
            order_limit=5,  # Было 60 - снижаем в 12 раз
            position_limit=5,  # Было 30 - снижаем в 6 раз
            balance_limit=2,  # Было 10 - снижаем в 5 раз
            burst_allowance=2,  # Было 5 - снижаем
            penalty_multiplier=3.0,  # Было 1.5 - увеличиваем штраф
        )

        # Binance
        self.exchange_configs["binance"] = ExchangeRateLimit(
            public_limit=1200,
            private_limit=600,
            order_limit=100,
            position_limit=50,
            balance_limit=20,
            burst_allowance=20,
            penalty_multiplier=2.0,
        )

        # OKX
        self.exchange_configs["okx"] = ExchangeRateLimit(
            public_limit=600,
            private_limit=300,
            order_limit=60,
            position_limit=30,
            balance_limit=10,
            burst_allowance=10,
            penalty_multiplier=1.8,
        )

        # Bitget
        self.exchange_configs["bitget"] = ExchangeRateLimit(
            public_limit=600,
            private_limit=300,
            order_limit=50,
            position_limit=25,
            balance_limit=10,
            burst_allowance=8,
            penalty_multiplier=2.0,
        )

        # Gate.io
        self.exchange_configs["gateio"] = ExchangeRateLimit(
            public_limit=600,
            private_limit=300,
            order_limit=50,
            position_limit=25,
            balance_limit=10,
            burst_allowance=8,
            penalty_multiplier=1.8,
        )

        # KuCoin
        self.exchange_configs["kucoin"] = ExchangeRateLimit(
            public_limit=600,
            private_limit=300,
            order_limit=45,
            position_limit=20,
            balance_limit=10,
            burst_allowance=6,
            penalty_multiplier=2.2,
        )

        # Huobi
        self.exchange_configs["huobi"] = ExchangeRateLimit(
            public_limit=600,
            private_limit=300,
            order_limit=40,
            position_limit=20,
            balance_limit=8,
            burst_allowance=5,
            penalty_multiplier=2.0,
        )

    def _start_background_tasks(self):
        """Запуск фоновых задач"""
        self._cleanup_task = asyncio.create_task(self._cleanup_old_records())

    async def _cleanup_old_records(self):
        """Очистка старых записей из sliding window"""
        while True:
            try:
                current_time = time.time()
                window_start = current_time - 60  # 1 минута

                for exchange_name, state in self.exchange_states.items():
                    async with self.locks[exchange_name]:
                        # Очищаем старые записи
                        while (
                            state.public_requests
                            and state.public_requests[0].timestamp < window_start
                        ):
                            state.public_requests.popleft()

                        while (
                            state.private_requests
                            and state.private_requests[0].timestamp < window_start
                        ):
                            state.private_requests.popleft()

                        while (
                            state.order_requests
                            and state.order_requests[0].timestamp < window_start
                        ):
                            state.order_requests.popleft()

                # Спим 10 секунд между очистками
                await asyncio.sleep(10)

            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(30)

    async def acquire(
        self,
        exchange_name: str,
        endpoint: str,
        is_private: bool = False,
        priority: RequestPriority = RequestPriority.NORMAL,
        timeout: float = 30.0,
    ) -> bool:
        """
        Получение разрешения на выполнение запроса

        Args:
            exchange_name: Название биржи
            endpoint: API endpoint
            is_private: Приватный ли API
            priority: Приоритет запроса
            timeout: Таймаут ожидания в секундах

        Returns:
            True если разрешение получено, False если таймаут
        """
        start_time = time.time()

        async with self.locks[exchange_name]:
            config = self.exchange_configs.get(exchange_name.lower())
            if not config:
                self.logger.warning(f"No rate limit config for {exchange_name}, using default")
                config = ExchangeRateLimit()

            state = self.exchange_states[exchange_name]

            # Проверяем penalty период
            if time.time() < state.penalty_until:
                wait_time = state.penalty_until - time.time()
                if wait_time > timeout:
                    return False

                self.logger.info(
                    f"Waiting {wait_time:.1f}s for penalty period to end for {exchange_name}"
                )
                await asyncio.sleep(wait_time)

            # Проверяем backoff
            if state.backoff_delay > 0:
                if state.backoff_delay > timeout:
                    return False

                self.logger.info(f"Applying backoff {state.backoff_delay:.1f}s for {exchange_name}")
                await asyncio.sleep(state.backoff_delay)
                state.backoff_delay = 0

            # Определяем тип запроса и соответствующий лимит
            current_time = time.time()
            window_start = current_time - 60  # 1 минута

            if "order" in endpoint.lower():
                requests_queue = state.order_requests
                limit = config.order_limit
            elif "position" in endpoint.lower():
                requests_queue = state.order_requests  # Используем тот же лимит
                limit = config.position_limit
            elif "balance" in endpoint.lower() or "wallet" in endpoint.lower():
                requests_queue = state.order_requests  # Используем тот же лимит
                limit = config.balance_limit
            elif is_private:
                requests_queue = state.private_requests
                limit = config.private_limit
            else:
                requests_queue = state.public_requests
                limit = config.public_limit

            # Считаем текущие запросы в окне
            current_requests = sum(1 for req in requests_queue if req.timestamp >= window_start)

            # Проверяем, можем ли сделать запрос
            effective_limit = int(limit * state.penalty_multiplier)

            if current_requests >= effective_limit:
                # Проверяем burst allowance для высокого приоритета
                if priority.value >= RequestPriority.HIGH.value:
                    burst_window_start = current_time - config.burst_window_seconds
                    recent_requests = sum(
                        1 for req in requests_queue if req.timestamp >= burst_window_start
                    )

                    if recent_requests < config.burst_allowance:
                        self.logger.info(
                            f"Using burst allowance for high priority request to {exchange_name}"
                        )
                    else:
                        # Нужно ждать
                        return await self._handle_rate_limit_wait(
                            exchange_name, requests_queue, limit, timeout, start_time
                        )
                else:
                    # Нужно ждать
                    return await self._handle_rate_limit_wait(
                        exchange_name, requests_queue, limit, timeout, start_time
                    )

            # Запрос разрешен
            record = RequestRecord(
                timestamp=current_time,
                endpoint=endpoint,
                priority=priority,
                success=True,
            )
            requests_queue.append(record)
            state.total_requests += 1

            return True

    async def _handle_rate_limit_wait(
        self,
        exchange_name: str,
        requests_queue: deque,
        limit: int,
        timeout: float,
        start_time: float,
    ) -> bool:
        """Обработка ожидания при превышении rate limit"""

        # Находим самый старый запрос в окне
        current_time = time.time()
        window_start = current_time - 60

        oldest_request_time = None
        for req in requests_queue:
            if req.timestamp >= window_start:
                oldest_request_time = req.timestamp
                break

        if oldest_request_time is None:
            return True  # Нет запросов в окне, можно продолжать

        # Время ожидания до освобождения слота
        wait_time = oldest_request_time + 60 - current_time

        if wait_time <= 0:
            return True  # Слот уже освободился

        elapsed = current_time - start_time
        if elapsed + wait_time > timeout:
            self.logger.warning(f"Rate limit timeout for {exchange_name}")
            return False

        self.logger.info(f"Rate limit hit for {exchange_name}, waiting {wait_time:.1f}s")
        await asyncio.sleep(wait_time)

        return True

    def record_success(self, exchange_name: str, endpoint: str, response_time: float):
        """Запись успешного запроса"""
        state = self.exchange_states[exchange_name]
        state.successful_requests += 1
        state.consecutive_errors = 0

        # Сброс backoff при успехе
        state.backoff_delay = 0

    def record_error(
        self,
        exchange_name: str,
        endpoint: str,
        error_code: str | None = None,
        retry_after: int | None = None,
    ):
        """Запись ошибки запроса"""
        config = self.exchange_configs.get(exchange_name.lower(), ExchangeRateLimit())
        state = self.exchange_states[exchange_name]

        state.consecutive_errors += 1
        state.last_error_time = time.time()

        # Обработка rate limit ошибок
        if error_code and self._is_rate_limit_error(error_code, exchange_name):
            state.rate_limited_requests += 1

            # Устанавливаем penalty
            penalty_duration = config.penalty_duration_seconds * config.penalty_multiplier
            state.penalty_until = time.time() + penalty_duration
            state.penalty_multiplier = min(state.penalty_multiplier * 1.2, 3.0)

            if retry_after:
                state.penalty_until = max(state.penalty_until, time.time() + retry_after)

            self.logger.warning(
                f"Rate limit hit for {exchange_name}, penalty until {datetime.fromtimestamp(state.penalty_until)}"
            )

        # Обработка server errors (5xx)
        elif error_code and (
            error_code.startswith("5") or error_code in ["500", "502", "503", "504"]
        ):
            # Exponential backoff
            state.backoff_delay = min(
                config.backoff_base_delay
                * (config.backoff_multiplier ** (state.consecutive_errors - 1)),
                config.backoff_max_delay,
            )

            self.logger.warning(
                f"Server error for {exchange_name}, applying backoff {state.backoff_delay:.1f}s"
            )

    def _is_rate_limit_error(self, error_code: str, exchange_name: str) -> bool:
        """Проверка, является ли ошибка превышением rate limit"""
        rate_limit_codes = {
            "bybit": ["10006", "10018", "10019"],
            "binance": ["-1003", "-1015", "-2010"],
            "okx": ["50011", "50014"],
            "bitget": ["40006", "40007"],
            "gateio": ["429"],
            "kucoin": ["1015", "1016"],
            "huobi": ["1100", "1101"],
        }

        return error_code in rate_limit_codes.get(exchange_name.lower(), [])

    def get_stats(self, exchange_name: str) -> dict[str, Any]:
        """Получение статистики по бирже"""
        config = self.exchange_configs.get(exchange_name.lower(), ExchangeRateLimit())
        state = self.exchange_states[exchange_name]

        current_time = time.time()
        window_start = current_time - 60

        # Подсчет текущих запросов
        public_count = sum(1 for req in state.public_requests if req.timestamp >= window_start)
        private_count = sum(1 for req in state.private_requests if req.timestamp >= window_start)
        order_count = sum(1 for req in state.order_requests if req.timestamp >= window_start)

        return {
            "exchange": exchange_name,
            "current_usage": {
                "public": f"{public_count}/{config.public_limit}",
                "private": f"{private_count}/{config.private_limit}",
                "orders": f"{order_count}/{config.order_limit}",
            },
            "penalty_active": current_time < state.penalty_until,
            "penalty_ends": (
                datetime.fromtimestamp(state.penalty_until).isoformat()
                if state.penalty_until > current_time
                else None
            ),
            "backoff_delay": state.backoff_delay,
            "consecutive_errors": state.consecutive_errors,
            "statistics": {
                "total_requests": state.total_requests,
                "successful_requests": state.successful_requests,
                "rate_limited_requests": state.rate_limited_requests,
                "success_rate": f"{(state.successful_requests / max(state.total_requests, 1)) * 100:.1f}%",
            },
        }

    def update_config(self, exchange_name: str, config: ExchangeRateLimit):
        """Обновление конфигурации для биржи"""
        self.exchange_configs[exchange_name.lower()] = config
        self.logger.info(f"Updated rate limit config for {exchange_name}")

    async def shutdown(self):
        """Корректное завершение работы"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        self.logger.info("Rate limiter shutdown complete")


# Глобальный экземпляр rate limiter
_global_rate_limiter: UniversalRateLimiter | None = None


def get_rate_limiter() -> UniversalRateLimiter:
    """Получение глобального экземпляра rate limiter"""
    global _global_rate_limiter

    if _global_rate_limiter is None:
        _global_rate_limiter = UniversalRateLimiter()

    return _global_rate_limiter


async def with_rate_limit(
    exchange_name: str,
    endpoint: str,
    is_private: bool = False,
    priority: RequestPriority = RequestPriority.NORMAL,
    timeout: float = 30.0,
):
    """
    Декоратор для автоматического применения rate limiting

    Usage:
        async with with_rate_limit("bybit", "/v5/order/create", is_private=True):
            response = await make_api_request()
    """

    class RateLimitContext:
        def __init__(self):
            self.rate_limiter = get_rate_limiter()
            self.exchange_name = exchange_name
            self.endpoint = endpoint

        async def __aenter__(self):
            success = await self.rate_limiter.acquire(
                exchange_name, endpoint, is_private, priority, timeout
            )
            if not success:
                raise TimeoutError(f"Rate limit timeout for {exchange_name} {endpoint}")
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if exc_type is None:
                self.rate_limiter.record_success(exchange_name, endpoint, 0.0)
            else:
                error_code = None
                retry_after = None

                # Извлекаем код ошибки из исключения
                if hasattr(exc_val, "context") and exc_val.context:
                    error_code = exc_val.context.get("api_error_code")
                    retry_after = exc_val.context.get("retry_after")

                self.rate_limiter.record_error(exchange_name, endpoint, error_code, retry_after)

    return RateLimitContext()
