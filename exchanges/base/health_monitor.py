"""
Health Monitor для мониторинга состояния бирж BOT_Trading v3.0

Компонент для комплексного мониторинга здоровья бирж с поддержкой:
- Проверки доступности API endpoints
- Мониторинга качества подключения
- Отслеживания производительности
- Алертов при проблемах
- Автоматических действий при сбоях
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import aiohttp

from core.logger import setup_logger


class HealthStatus(Enum):
    """Статусы здоровья биржи"""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"
    MAINTENANCE = "maintenance"


class CheckType(Enum):
    """Типы проверок"""

    CONNECTIVITY = "connectivity"
    LATENCY = "latency"
    API_HEALTH = "api_health"
    RATE_LIMITS = "rate_limits"
    AUTH_STATUS = "auth_status"
    WEBSOCKET = "websocket"


@dataclass
class HealthMetric:
    """Метрика здоровья"""

    name: str
    value: float
    status: HealthStatus
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    """Результат проверки здоровья"""

    check_type: CheckType
    status: HealthStatus
    latency_ms: float
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ExchangeHealthStatus:
    """Общий статус здоровья биржи"""

    exchange_name: str
    overall_status: HealthStatus
    last_check: datetime
    checks: Dict[CheckType, HealthCheckResult] = field(default_factory=dict)
    metrics: List[HealthMetric] = field(default_factory=list)
    consecutive_failures: int = 0
    uptime_percentage: float = 100.0

    @property
    def is_healthy(self) -> bool:
        """Проверка общего здоровья"""
        return self.overall_status in [HealthStatus.HEALTHY, HealthStatus.WARNING]

    @property
    def avg_latency(self) -> float:
        """Средняя латентность"""
        latencies = [
            check.latency_ms for check in self.checks.values() if check.latency_ms > 0
        ]
        return sum(latencies) / len(latencies) if latencies else 0.0


class ExchangeHealthMonitor:
    """
    Мониторинг здоровья бирж

    Выполняет:
    - Периодические проверки состояния
    - Сбор метрик производительности
    - Алертинг при проблемах
    - Автоматические recovery действия
    """

    def __init__(self):
        self.logger = setup_logger("exchange_health_monitor")

        # Состояние мониторинга
        self.exchange_status: Dict[str, ExchangeHealthStatus] = {}
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.is_running = False

        # HTTP session для проверок
        self.session: Optional[aiohttp.ClientSession] = None

        # Конфигурация проверок
        self.check_interval = 30  # Интервал проверок в секундах
        self.timeout = 10  # Таймаут для проверок
        self.max_consecutive_failures = 5

        # Обработчики событий
        self.alert_handlers: List[Callable] = []
        self.recovery_handlers: Dict[str, Callable] = {}

        # Конфигурации endpoints для разных бирж
        self.exchange_endpoints = self._init_exchange_endpoints()

    def _init_exchange_endpoints(self) -> Dict[str, Dict[str, str]]:
        """Инициализация endpoints для проверки здоровья"""
        return {
            "bybit": {
                "api_base": "https://api.bybit.com",
                "health_endpoint": "/v5/market/time",
                "status_check": "retCode",
                "expected_status": "0",
            },
            "binance": {
                "api_base": "https://api.binance.com",
                "health_endpoint": "/api/v3/ping",
                "status_check": "response_code",
                "expected_status": "200",
            },
            "okx": {
                "api_base": "https://www.okx.com",
                "health_endpoint": "/api/v5/public/time",
                "status_check": "code",
                "expected_status": "0",
            },
            "bitget": {
                "api_base": "https://api.bitget.com",
                "health_endpoint": "/api/spot/v1/public/time",
                "status_check": "code",
                "expected_status": "00000",
            },
            "gateio": {
                "api_base": "https://api.gateio.ws",
                "health_endpoint": "/api/v4/spot/time",
                "status_check": "response_code",
                "expected_status": "200",
            },
            "kucoin": {
                "api_base": "https://api.kucoin.com",
                "health_endpoint": "/api/v1/timestamp",
                "status_check": "code",
                "expected_status": "200000",
            },
            "huobi": {
                "api_base": "https://api.huobi.pro",
                "health_endpoint": "/v1/common/timestamp",
                "status_check": "status",
                "expected_status": "ok",
            },
        }

    async def initialize(self):
        """Инициализация мониторинга"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)

        self.is_running = True
        self.logger.info("Exchange Health Monitor инициализирован")

    async def shutdown(self):
        """Корректное завершение работы"""
        self.is_running = False

        # Останавливаем все задачи мониторинга
        for task in self.monitoring_tasks.values():
            task.cancel()

        if self.monitoring_tasks:
            await asyncio.gather(
                *self.monitoring_tasks.values(), return_exceptions=True
            )

        if self.session:
            await self.session.close()

        self.logger.info("Exchange Health Monitor остановлен")

    def add_exchange(self, exchange_name: str):
        """Добавление биржи для мониторинга"""
        exchange_name = exchange_name.lower()

        if exchange_name not in self.exchange_status:
            self.exchange_status[exchange_name] = ExchangeHealthStatus(
                exchange_name=exchange_name,
                overall_status=HealthStatus.UNKNOWN,
                last_check=datetime.now(),
            )

            # Запускаем мониторинг для этой биржи
            if self.is_running:
                task = asyncio.create_task(self._monitor_exchange(exchange_name))
                self.monitoring_tasks[exchange_name] = task

            self.logger.info(f"Добавлена биржа для мониторинга: {exchange_name}")

    def remove_exchange(self, exchange_name: str):
        """Удаление биржи из мониторинга"""
        exchange_name = exchange_name.lower()

        # Останавливаем задачу мониторинга
        if exchange_name in self.monitoring_tasks:
            self.monitoring_tasks[exchange_name].cancel()
            del self.monitoring_tasks[exchange_name]

        # Удаляем статус
        if exchange_name in self.exchange_status:
            del self.exchange_status[exchange_name]

        self.logger.info(f"Биржа удалена из мониторинга: {exchange_name}")

    async def start_monitoring(self):
        """Запуск мониторинга для всех добавленных бирж"""
        if not self.is_running:
            await self.initialize()

        for exchange_name in self.exchange_status.keys():
            if exchange_name not in self.monitoring_tasks:
                task = asyncio.create_task(self._monitor_exchange(exchange_name))
                self.monitoring_tasks[exchange_name] = task

        self.logger.info(f"Запущен мониторинг для {len(self.monitoring_tasks)} бирж")

    async def _monitor_exchange(self, exchange_name: str):
        """Основной цикл мониторинга биржи"""
        while self.is_running:
            try:
                await self._perform_health_checks(exchange_name)
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Ошибка мониторинга {exchange_name}: {e}")
                await asyncio.sleep(self.check_interval)

    async def _perform_health_checks(self, exchange_name: str):
        """Выполнение всех проверок для биржи"""
        status = self.exchange_status[exchange_name]
        endpoint_config = self.exchange_endpoints.get(exchange_name)

        if not endpoint_config:
            self.logger.warning(f"Нет конфигурации для {exchange_name}")
            return

        # Выполняем различные типы проверок
        checks = {}

        # 1. Проверка подключения и API health
        connectivity_result = await self._check_connectivity(
            exchange_name, endpoint_config
        )
        checks[CheckType.CONNECTIVITY] = connectivity_result
        checks[CheckType.API_HEALTH] = connectivity_result  # Одновременно проверяем API

        # 2. Проверка латентности (более детальная)
        latency_result = await self._check_latency(exchange_name, endpoint_config)
        checks[CheckType.LATENCY] = latency_result

        # 3. Проверка rate limits (если есть информация)
        rate_limit_result = await self._check_rate_limits(exchange_name)
        checks[CheckType.RATE_LIMITS] = rate_limit_result

        # Обновляем статус
        status.checks = checks
        status.last_check = datetime.now()

        # Определяем общий статус
        overall_status = self._calculate_overall_status(checks)

        # Обрабатываем изменение статуса
        if overall_status != status.overall_status:
            await self._handle_status_change(
                exchange_name, status.overall_status, overall_status
            )

        status.overall_status = overall_status

        # Обновляем счетчики
        if overall_status == HealthStatus.CRITICAL:
            status.consecutive_failures += 1
        else:
            status.consecutive_failures = 0

        # Вычисляем uptime
        self._update_uptime(status)

        # Добавляем метрики
        self._add_metrics(status, checks)

    async def _check_connectivity(
        self, exchange_name: str, endpoint_config: Dict[str, str]
    ) -> HealthCheckResult:
        """Проверка подключения к бирже"""
        start_time = time.time()

        try:
            url = endpoint_config["api_base"] + endpoint_config["health_endpoint"]

            async with self.session.get(url) as response:
                latency = (time.time() - start_time) * 1000

                if response.status == 200:
                    data = await response.json()

                    # Проверяем специфичный для биржи статус
                    status_check = endpoint_config["status_check"]
                    expected_status = endpoint_config["expected_status"]

                    if status_check == "response_code":
                        # Просто проверяем HTTP код
                        status = HealthStatus.HEALTHY
                        error_message = None
                    else:
                        # Проверяем поле в ответе
                        actual_status = str(data.get(status_check, ""))

                        if actual_status == expected_status:
                            status = HealthStatus.HEALTHY
                            error_message = None
                        else:
                            status = HealthStatus.WARNING
                            error_message = f"Unexpected status: {actual_status}, expected: {expected_status}"

                    return HealthCheckResult(
                        check_type=CheckType.CONNECTIVITY,
                        status=status,
                        latency_ms=latency,
                        error_message=error_message,
                        details={"response_data": data, "http_status": response.status},
                    )
                else:
                    return HealthCheckResult(
                        check_type=CheckType.CONNECTIVITY,
                        status=HealthStatus.CRITICAL,
                        latency_ms=latency,
                        error_message=f"HTTP {response.status}",
                        details={"http_status": response.status},
                    )

        except asyncio.TimeoutError:
            return HealthCheckResult(
                check_type=CheckType.CONNECTIVITY,
                status=HealthStatus.CRITICAL,
                latency_ms=self.timeout * 1000,
                error_message="Connection timeout",
            )
        except Exception as e:
            return HealthCheckResult(
                check_type=CheckType.CONNECTIVITY,
                status=HealthStatus.CRITICAL,
                latency_ms=(time.time() - start_time) * 1000,
                error_message=str(e),
            )

    async def _check_latency(
        self, exchange_name: str, endpoint_config: Dict[str, str]
    ) -> HealthCheckResult:
        """Проверка латентности (множественные запросы)"""
        latencies = []
        errors = []

        # Делаем 3 запроса для получения средней латентности
        for i in range(3):
            try:
                start_time = time.time()
                url = endpoint_config["api_base"] + endpoint_config["health_endpoint"]

                async with self.session.get(url) as response:
                    latency = (time.time() - start_time) * 1000

                    if response.status == 200:
                        latencies.append(latency)
                    else:
                        errors.append(f"HTTP {response.status}")

            except Exception as e:
                errors.append(str(e))

            # Небольшая пауза между запросами
            if i < 2:
                await asyncio.sleep(0.1)

        if latencies:
            avg_latency = sum(latencies) / len(latencies)

            # Определяем статус на основе латентности
            if avg_latency < 100:
                status = HealthStatus.HEALTHY
            elif avg_latency < 500:
                status = HealthStatus.WARNING
            else:
                status = HealthStatus.CRITICAL

            return HealthCheckResult(
                check_type=CheckType.LATENCY,
                status=status,
                latency_ms=avg_latency,
                details={
                    "latencies": latencies,
                    "min_latency": min(latencies),
                    "max_latency": max(latencies),
                    "errors": errors,
                },
            )
        else:
            return HealthCheckResult(
                check_type=CheckType.LATENCY,
                status=HealthStatus.CRITICAL,
                latency_ms=0,
                error_message=f"All requests failed: {'; '.join(errors)}",
            )

    async def _check_rate_limits(self, exchange_name: str) -> HealthCheckResult:
        """Проверка статуса rate limits"""
        # Получаем информацию из rate limiter
        from .rate_limiter import get_rate_limiter

        try:
            rate_limiter = get_rate_limiter()
            stats = rate_limiter.get_stats(exchange_name)

            # Анализируем статистику
            current_usage = stats.get("current_usage", {})
            penalty_active = stats.get("penalty_active", False)

            if penalty_active:
                status = HealthStatus.CRITICAL
                error_message = "Rate limit penalty active"
            else:
                # Проверяем загрузку
                usage_levels = []
                for limit_type, usage_str in current_usage.items():
                    if "/" in usage_str:
                        current, maximum = map(int, usage_str.split("/"))
                        usage_percent = (current / maximum) * 100
                        usage_levels.append(usage_percent)

                if usage_levels:
                    max_usage = max(usage_levels)
                    if max_usage > 90:
                        status = HealthStatus.CRITICAL
                        error_message = f"High rate limit usage: {max_usage:.1f}%"
                    elif max_usage > 70:
                        status = HealthStatus.WARNING
                        error_message = f"Moderate rate limit usage: {max_usage:.1f}%"
                    else:
                        status = HealthStatus.HEALTHY
                        error_message = None
                else:
                    status = HealthStatus.HEALTHY
                    error_message = None

            return HealthCheckResult(
                check_type=CheckType.RATE_LIMITS,
                status=status,
                latency_ms=0,
                error_message=error_message,
                details=stats,
            )

        except Exception as e:
            return HealthCheckResult(
                check_type=CheckType.RATE_LIMITS,
                status=HealthStatus.UNKNOWN,
                latency_ms=0,
                error_message=str(e),
            )

    def _calculate_overall_status(
        self, checks: Dict[CheckType, HealthCheckResult]
    ) -> HealthStatus:
        """Вычисление общего статуса на основе всех проверок"""
        if not checks:
            return HealthStatus.UNKNOWN

        statuses = [check.status for check in checks.values()]

        # Если есть критические ошибки
        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL

        # Если есть предупреждения
        if HealthStatus.WARNING in statuses:
            return HealthStatus.WARNING

        # Если все здоровы
        if all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY

        # По умолчанию неизвестно
        return HealthStatus.UNKNOWN

    async def _handle_status_change(
        self, exchange_name: str, old_status: HealthStatus, new_status: HealthStatus
    ):
        """Обработка изменения статуса биржи"""
        self.logger.info(
            f"Статус {exchange_name}: {old_status.value} → {new_status.value}"
        )

        # Генерируем алерт
        if new_status == HealthStatus.CRITICAL:
            await self._send_alert(
                exchange_name, "CRITICAL", f"Exchange {exchange_name} is critical"
            )
        elif new_status == HealthStatus.HEALTHY and old_status == HealthStatus.CRITICAL:
            await self._send_alert(
                exchange_name, "RECOVERY", f"Exchange {exchange_name} recovered"
            )

        # Выполняем recovery действия
        if (
            exchange_name in self.recovery_handlers
            and new_status == HealthStatus.CRITICAL
        ):
            try:
                await self.recovery_handlers[exchange_name](exchange_name, new_status)
            except Exception as e:
                self.logger.error(f"Recovery action failed for {exchange_name}: {e}")

    async def _send_alert(self, exchange_name: str, alert_type: str, message: str):
        """Отправка алерта"""
        alert_data = {
            "exchange": exchange_name,
            "type": alert_type,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }

        for handler in self.alert_handlers:
            try:
                await handler(alert_data)
            except Exception as e:
                self.logger.error(f"Alert handler failed: {e}")

    def _update_uptime(self, status: ExchangeHealthStatus):
        """Обновление метрики uptime"""
        # Простой расчет uptime на основе последних проверок
        if status.is_healthy:
            # Uptime остается высоким при здоровом статусе
            status.uptime_percentage = min(100.0, status.uptime_percentage + 0.1)
        else:
            # Снижаем uptime при проблемах
            status.uptime_percentage = max(0.0, status.uptime_percentage - 1.0)

    def _add_metrics(
        self, status: ExchangeHealthStatus, checks: Dict[CheckType, HealthCheckResult]
    ):
        """Добавление метрик"""
        current_time = datetime.now()

        # Добавляем метрику латентности
        if CheckType.LATENCY in checks:
            latency_metric = HealthMetric(
                name="latency_ms",
                value=checks[CheckType.LATENCY].latency_ms,
                status=checks[CheckType.LATENCY].status,
                timestamp=current_time,
            )
            status.metrics.append(latency_metric)

        # Добавляем метрику uptime
        uptime_metric = HealthMetric(
            name="uptime_percentage",
            value=status.uptime_percentage,
            status=status.overall_status,
            timestamp=current_time,
        )
        status.metrics.append(uptime_metric)

        # Ограничиваем количество метрик (храним последние 100)
        if len(status.metrics) > 100:
            status.metrics = status.metrics[-100:]

    def add_alert_handler(self, handler: Callable):
        """Добавление обработчика алертов"""
        self.alert_handlers.append(handler)

    def add_recovery_handler(self, exchange_name: str, handler: Callable):
        """Добавление обработчика восстановления для биржи"""
        self.recovery_handlers[exchange_name.lower()] = handler

    def get_exchange_status(self, exchange_name: str) -> Optional[ExchangeHealthStatus]:
        """Получение статуса биржи"""
        return self.exchange_status.get(exchange_name.lower())

    def get_all_statuses(self) -> Dict[str, ExchangeHealthStatus]:
        """Получение статусов всех бирж"""
        return self.exchange_status.copy()

    def get_health_summary(self) -> Dict[str, Any]:
        """Получение сводки по здоровью всех бирж"""
        total_exchanges = len(self.exchange_status)
        healthy_count = sum(
            1 for status in self.exchange_status.values() if status.is_healthy
        )

        summary = {
            "total_exchanges": total_exchanges,
            "healthy_exchanges": healthy_count,
            "unhealthy_exchanges": total_exchanges - healthy_count,
            "overall_health_percentage": (
                (healthy_count / total_exchanges * 100) if total_exchanges > 0 else 0
            ),
            "exchanges": {},
        }

        for exchange_name, status in self.exchange_status.items():
            summary["exchanges"][exchange_name] = {
                "status": status.overall_status.value,
                "uptime": f"{status.uptime_percentage:.1f}%",
                "avg_latency": f"{status.avg_latency:.1f}ms",
                "consecutive_failures": status.consecutive_failures,
                "last_check": status.last_check.isoformat(),
            }

        return summary


# Глобальный экземпляр health monitor
_global_health_monitor: Optional[ExchangeHealthMonitor] = None


def get_health_monitor() -> ExchangeHealthMonitor:
    """Получение глобального экземпляра health monitor"""
    global _global_health_monitor

    if _global_health_monitor is None:
        _global_health_monitor = ExchangeHealthMonitor()

    return _global_health_monitor
