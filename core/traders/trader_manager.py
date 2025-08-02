"""
Trader Manager для BOT_Trading v3.0

Менеджер жизненного цикла трейдеров с поддержкой:
- Создания и инициализации мульти-трейдеров
- Управления состоянием (запуск/остановка/пауза)
- Мониторинга производительности
- Автоматического восстановления при ошибках
- Балансировки нагрузки между трейдерами
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from core.config.config_manager import ConfigManager
from core.exceptions import (
    TooManyTradersError,
    TraderAlreadyExistsError,
    TraderManagerError,
    TraderNotFoundError,
)
from core.traders.trader_context import TraderContext, TraderState
from core.traders.trader_factory import TraderFactory


class ManagerState(Enum):
    """Состояния менеджера трейдеров"""

    CREATED = "created"
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class TraderHealthStatus:
    """Статус здоровья трейдера"""

    trader_id: str
    is_healthy: bool
    last_check: datetime
    error_count: int = 0
    consecutive_errors: int = 0
    uptime_seconds: float = 0.0
    response_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0


@dataclass
class ManagerMetrics:
    """Метрики менеджера трейдеров"""

    total_traders: int = 0
    active_traders: int = 0
    healthy_traders: int = 0
    total_trades: int = 0
    total_profit_loss: float = 0.0
    average_response_time: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    uptime_seconds: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)


class TraderManager:
    """
    Менеджер жизненного цикла трейдеров BOT_Trading v3.0

    Функциональность:
    - Создание и управление множественными трейдерами
    - Мониторинг состояния и здоровья
    - Автоматическое восстановление
    - Балансировка нагрузки
    - Координация между трейдерами
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        trader_factory: Optional[TraderFactory] = None,
    ):
        self.config_manager = config_manager
        self.trader_factory = trader_factory or TraderFactory(config_manager)
        self.logger = logging.getLogger(__name__)

        # Состояние менеджера
        self._state = ManagerState.CREATED
        self._created_at = datetime.now()
        self._started_at: Optional[datetime] = None
        self._stopped_at: Optional[datetime] = None

        # Трейдеры и их состояние
        self._traders: Dict[str, TraderContext] = {}
        self._trader_health: Dict[str, TraderHealthStatus] = {}
        self._trader_tasks: Dict[str, asyncio.Task] = {}

        # Метрики и мониторинг
        self.metrics = ManagerMetrics()
        self._health_check_interval = 30  # секунд
        self._health_check_task: Optional[asyncio.Task] = None
        self._metrics_update_task: Optional[asyncio.Task] = None

        # Настройки и лимиты
        self._max_traders = config_manager.get_config("system.limits.max_traders", 10)
        self._max_consecutive_errors = 5
        self._auto_recovery_enabled = config_manager.get_config(
            "system.auto_recovery", True
        )

        # Callback'и для событий
        self._event_callbacks: Dict[str, List[Callable]] = {
            "trader_started": [],
            "trader_stopped": [],
            "trader_error": [],
            "trader_recovered": [],
            "health_check_failed": [],
        }

        # Thread pool для CPU-intensive операций
        self._thread_pool = ThreadPoolExecutor(max_workers=4)

        # Lock для thread safety
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Инициализация менеджера"""
        async with self._lock:
            if self._state != ManagerState.CREATED:
                return

            try:
                self._state = ManagerState.INITIALIZING
                self.logger.info("Инициализация менеджера трейдеров...")

                # Инициализация фабрики трейдеров
                if not hasattr(self.trader_factory, "_is_initialized"):
                    await self._initialize_trader_factory()

                # Загрузка конфигураций трейдеров
                await self._load_trader_configurations()

                self.logger.info("Менеджер трейдеров инициализирован")
                self._state = ManagerState.RUNNING

            except Exception as e:
                self._state = ManagerState.ERROR
                error_msg = f"Ошибка инициализации менеджера трейдеров: {e}"
                self.logger.error(error_msg)
                raise TraderManagerError(error_msg) from e

    async def _initialize_trader_factory(self) -> None:
        """Инициализация фабрики трейдеров"""
        # Дополнительная настройка фабрики если нужно
        self.trader_factory._is_initialized = True

    async def _load_trader_configurations(self) -> None:
        """Загрузка конфигураций трейдеров"""
        trader_ids = self.config_manager.get_all_trader_ids()

        for trader_id in trader_ids:
            if self.config_manager.is_trader_enabled(trader_id):
                self.logger.info(f"Конфигурация трейдера {trader_id} загружена")
            else:
                self.logger.info(f"Трейдер {trader_id} отключен в конфигурации")

    async def start(self) -> None:
        """Запуск менеджера и всех включенных трейдеров"""
        async with self._lock:
            if self._state == ManagerState.RUNNING:
                return

            if self._state != ManagerState.RUNNING:
                await self.initialize()

            try:
                self.logger.info("Запуск менеджера трейдеров...")
                self._started_at = datetime.now()

                # Запуск мониторинга
                await self._start_monitoring()

                # Автоматический запуск включенных трейдеров
                await self._start_enabled_traders()

                self.logger.info("Менеджер трейдеров запущен")

            except Exception as e:
                self._state = ManagerState.ERROR
                error_msg = f"Ошибка запуска менеджера трейдеров: {e}"
                self.logger.error(error_msg)
                raise TraderManagerError(error_msg) from e

    async def stop(self) -> None:
        """Остановка менеджера и всех трейдеров"""
        async with self._lock:
            if self._state in [ManagerState.STOPPED, ManagerState.STOPPING]:
                return

            try:
                self._state = ManagerState.STOPPING
                self.logger.info("Остановка менеджера трейдеров...")

                # Остановка мониторинга
                await self._stop_monitoring()

                # Остановка всех трейдеров
                await self._stop_all_traders()

                # Закрытие thread pool
                self._thread_pool.shutdown(wait=True)

                self._state = ManagerState.STOPPED
                self._stopped_at = datetime.now()
                self.logger.info("Менеджер трейдеров остановлен")

            except Exception as e:
                self._state = ManagerState.ERROR
                error_msg = f"Ошибка остановки менеджера трейдеров: {e}"
                self.logger.error(error_msg)
                raise TraderManagerError(error_msg) from e

    async def _start_monitoring(self) -> None:
        """Запуск фоновых задач мониторинга"""
        # Запуск health check
        self._health_check_task = asyncio.create_task(self._health_check_loop())

        # Запуск обновления метрик
        self._metrics_update_task = asyncio.create_task(self._metrics_update_loop())

    async def _stop_monitoring(self) -> None:
        """Остановка фоновых задач мониторинга"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        if self._metrics_update_task:
            self._metrics_update_task.cancel()
            try:
                await self._metrics_update_task
            except asyncio.CancelledError:
                pass

    async def _start_enabled_traders(self) -> None:
        """Запуск всех включенных трейдеров"""
        trader_ids = self.config_manager.get_all_trader_ids()

        for trader_id in trader_ids:
            if self.config_manager.is_trader_enabled(trader_id):
                try:
                    await self.start_trader(trader_id)
                except Exception as e:
                    self.logger.error(f"Ошибка запуска трейдера {trader_id}: {e}")

    async def _stop_all_traders(self) -> None:
        """Остановка всех трейдеров"""
        stop_tasks = []

        for trader_id in list(self._traders.keys()):
            task = asyncio.create_task(self.stop_trader(trader_id))
            stop_tasks.append(task)

        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)

    async def create_trader(self, trader_id: str) -> TraderContext:
        """
        Создание нового трейдера

        Args:
            trader_id: Идентификатор трейдера

        Returns:
            Созданный TraderContext

        Raises:
            TraderAlreadyExistsError: Трейдер уже существует
            TooManyTradersError: Превышен лимит трейдеров
        """
        async with self._lock:
            if trader_id in self._traders:
                raise TraderAlreadyExistsError(f"Трейдер {trader_id} уже существует")

            if len(self._traders) >= self._max_traders:
                raise TooManyTradersError(
                    f"Превышен лимит трейдеров ({self._max_traders}). "
                    f"Текущее количество: {len(self._traders)}"
                )

            try:
                self.logger.info(f"Создание трейдера {trader_id}...")

                # Создание трейдера через фабрику
                trader_context = await self.trader_factory.create_trader(trader_id)

                # Регистрация трейдера
                self._traders[trader_id] = trader_context

                # Инициализация статуса здоровья
                self._trader_health[trader_id] = TraderHealthStatus(
                    trader_id=trader_id, is_healthy=True, last_check=datetime.now()
                )

                # Обновление метрик
                self.metrics.total_traders = len(self._traders)

                self.logger.info(f"Трейдер {trader_id} создан")
                return trader_context

            except Exception as e:
                error_msg = f"Ошибка создания трейдера {trader_id}: {e}"
                self.logger.error(error_msg)
                raise TraderManagerError(error_msg) from e

    async def start_trader(self, trader_id: str) -> None:
        """
        Запуск трейдера

        Args:
            trader_id: Идентификатор трейдера

        Raises:
            TraderNotFoundError: Трейдер не найден
        """
        # Создание трейдера если он не существует
        if trader_id not in self._traders:
            await self.create_trader(trader_id)

        trader_context = self._traders[trader_id]

        if trader_context.is_running:
            self.logger.warning(f"Трейдер {trader_id} уже запущен")
            return

        try:
            self.logger.info(f"Запуск трейдера {trader_id}...")

            # Запуск трейдера
            await trader_context.start()

            # Создание задачи для выполнения трейдера
            task = asyncio.create_task(self._run_trader(trader_context))
            self._trader_tasks[trader_id] = task

            # Обновление метрик
            self.metrics.active_traders = len(
                [t for t in self._traders.values() if t.is_running]
            )

            # Уведомление о событии
            await self._emit_event("trader_started", trader_id, trader_context)

            self.logger.info(f"Трейдер {trader_id} запущен")

        except Exception as e:
            error_msg = f"Ошибка запуска трейдера {trader_id}: {e}"
            self.logger.error(error_msg)

            # Обновление статуса здоровья
            if trader_id in self._trader_health:
                self._trader_health[trader_id].error_count += 1
                self._trader_health[trader_id].consecutive_errors += 1

            await self._emit_event("trader_error", trader_id, e)
            raise TraderManagerError(error_msg) from e

    async def stop_trader(self, trader_id: str) -> None:
        """
        Остановка трейдера

        Args:
            trader_id: Идентификатор трейдера

        Raises:
            TraderNotFoundError: Трейдер не найден
        """
        if trader_id not in self._traders:
            raise TraderNotFoundError(f"Трейдер {trader_id} не найден")

        trader_context = self._traders[trader_id]

        try:
            self.logger.info(f"Остановка трейдера {trader_id}...")

            # Отмена задачи трейдера
            if trader_id in self._trader_tasks:
                task = self._trader_tasks[trader_id]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                del self._trader_tasks[trader_id]

            # Остановка трейдера
            await trader_context.stop()

            # Обновление метрик
            self.metrics.active_traders = len(
                [t for t in self._traders.values() if t.is_running]
            )

            # Уведомление о событии
            await self._emit_event("trader_stopped", trader_id, trader_context)

            self.logger.info(f"Трейдер {trader_id} остановлен")

        except Exception as e:
            error_msg = f"Ошибка остановки трейдера {trader_id}: {e}"
            self.logger.error(error_msg)
            raise TraderManagerError(error_msg) from e

    async def remove_trader(self, trader_id: str) -> None:
        """
        Удаление трейдера

        Args:
            trader_id: Идентификатор трейдера
        """
        if trader_id not in self._traders:
            return

        # Остановка трейдера если он запущен
        if self._traders[trader_id].is_running:
            await self.stop_trader(trader_id)

        # Удаление из реестров
        del self._traders[trader_id]
        if trader_id in self._trader_health:
            del self._trader_health[trader_id]

        # Обновление метрик
        self.metrics.total_traders = len(self._traders)
        self.metrics.active_traders = len(
            [t for t in self._traders.values() if t.is_running]
        )

        self.logger.info(f"Трейдер {trader_id} удален")

    async def _run_trader(self, trader_context: TraderContext) -> None:
        """Основной цикл выполнения трейдера"""
        trader_id = trader_context.trader_id

        try:
            while trader_context.is_running and not trader_context.should_stop:
                # Основная логика трейдера выполняется через стратегию
                if trader_context.strategy:
                    await trader_context.strategy.execute()

                # Небольшая пауза между итерациями
                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            self.logger.info(f"Выполнение трейдера {trader_id} отменено")
            raise
        except Exception as e:
            self.logger.error(f"Ошибка в цикле трейдера {trader_id}: {e}")
            trader_context.add_error(str(e))

            # Попытка автоматического восстановления
            if self._auto_recovery_enabled:
                await self._attempt_recovery(trader_context, e)

    async def _attempt_recovery(
        self, trader_context: TraderContext, error: Exception
    ) -> None:
        """Попытка автоматического восстановления трейдера"""
        trader_id = trader_context.trader_id

        # Проверка лимита consecutive errors
        health_status = self._trader_health.get(trader_id)
        if (
            health_status
            and health_status.consecutive_errors >= self._max_consecutive_errors
        ):
            self.logger.error(
                f"Трейдер {trader_id} превысил лимит последовательных ошибок "
                f"({self._max_consecutive_errors}). Автоматическое восстановление отключено."
            )
            await self.stop_trader(trader_id)
            return

        try:
            self.logger.info(f"Попытка восстановления трейдера {trader_id}...")

            # Пауза перед восстановлением
            await asyncio.sleep(5)

            # Переинициализация компонентов
            if trader_context.exchange:
                await trader_context.exchange.reconnect()

            if trader_context.strategy:
                await trader_context.strategy.reset()

            # Сброс consecutive errors при успешном восстановлении
            if health_status:
                health_status.consecutive_errors = 0
                health_status.is_healthy = True

            await self._emit_event("trader_recovered", trader_id, trader_context)
            self.logger.info(f"Трейдер {trader_id} восстановлен")

        except Exception as recovery_error:
            self.logger.error(
                f"Ошибка восстановления трейдера {trader_id}: {recovery_error}"
            )
            if health_status:
                health_status.consecutive_errors += 1

    async def _health_check_loop(self) -> None:
        """Цикл проверки здоровья трейдеров"""
        while self._state == ManagerState.RUNNING:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self._health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Ошибка в health check: {e}")
                await asyncio.sleep(self._health_check_interval)

    async def _perform_health_checks(self) -> None:
        """Выполнение проверок здоровья всех трейдеров"""
        check_tasks = []

        for trader_id, trader_context in self._traders.items():
            task = asyncio.create_task(
                self._check_trader_health(trader_id, trader_context)
            )
            check_tasks.append(task)

        if check_tasks:
            await asyncio.gather(*check_tasks, return_exceptions=True)

    async def _check_trader_health(
        self, trader_id: str, trader_context: TraderContext
    ) -> None:
        """Проверка здоровья отдельного трейдера"""
        try:
            start_time = datetime.now()

            # Проверка состояния трейдера
            is_healthy = (
                trader_context.state not in [TraderState.ERROR, TraderState.STOPPED]
                and trader_context.metrics.errors_count < 10  # Пример порога
            )

            # Обновление статуса здоровья
            if trader_id in self._trader_health:
                health_status = self._trader_health[trader_id]
                health_status.is_healthy = is_healthy
                health_status.last_check = datetime.now()
                health_status.response_time_ms = (
                    datetime.now() - start_time
                ).total_seconds() * 1000

                if not is_healthy:
                    health_status.consecutive_errors += 1
                    await self._emit_event(
                        "health_check_failed", trader_id, health_status
                    )
                else:
                    health_status.consecutive_errors = 0

        except Exception as e:
            self.logger.error(f"Ошибка проверки здоровья трейдера {trader_id}: {e}")

    async def _metrics_update_loop(self) -> None:
        """Цикл обновления метрик"""
        while self._state == ManagerState.RUNNING:
            try:
                await self._update_metrics()
                await asyncio.sleep(10)  # Обновление каждые 10 секунд
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Ошибка обновления метрик: {e}")
                await asyncio.sleep(10)

    async def _update_metrics(self) -> None:
        """Обновление общих метрик менеджера"""
        self.metrics.total_traders = len(self._traders)
        self.metrics.active_traders = len(
            [t for t in self._traders.values() if t.is_running]
        )
        self.metrics.healthy_traders = len(
            [h for h in self._trader_health.values() if h.is_healthy]
        )

        # Агрегирование метрик трейдеров
        total_trades = 0
        total_pnl = 0.0
        response_times = []

        for trader_context in self._traders.values():
            total_trades += trader_context.metrics.trades_total
            total_pnl += trader_context.metrics.profit_loss

        for health_status in self._trader_health.values():
            if health_status.response_time_ms > 0:
                response_times.append(health_status.response_time_ms)

        self.metrics.total_trades = total_trades
        self.metrics.total_profit_loss = total_pnl
        self.metrics.average_response_time = (
            sum(response_times) / len(response_times) if response_times else 0
        )
        self.metrics.last_updated = datetime.now()

        # Время работы менеджера
        if self._started_at:
            self.metrics.uptime_seconds = (
                datetime.now() - self._started_at
            ).total_seconds()

    async def _emit_event(self, event_name: str, *args) -> None:
        """Уведомление о событии"""
        callbacks = self._event_callbacks.get(event_name, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args)
                else:
                    callback(*args)
            except Exception as e:
                self.logger.error(f"Ошибка в callback для события {event_name}: {e}")

    def add_event_listener(self, event_name: str, callback: Callable) -> None:
        """Добавление слушателя события"""
        if event_name not in self._event_callbacks:
            self._event_callbacks[event_name] = []
        self._event_callbacks[event_name].append(callback)

    def get_trader(self, trader_id: str) -> Optional[TraderContext]:
        """Получение трейдера по ID"""
        return self._traders.get(trader_id)

    def get_all_traders(self) -> Dict[str, TraderContext]:
        """Получение всех трейдеров"""
        return self._traders.copy()

    def get_trader_health(self, trader_id: str) -> Optional[TraderHealthStatus]:
        """Получение статуса здоровья трейдера"""
        return self._trader_health.get(trader_id)

    def get_manager_status(self) -> Dict[str, Any]:
        """Получение статуса менеджера"""
        return {
            "state": self._state.value,
            "created_at": self._created_at.isoformat(),
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "stopped_at": self._stopped_at.isoformat() if self._stopped_at else None,
            "metrics": {
                "total_traders": self.metrics.total_traders,
                "active_traders": self.metrics.active_traders,
                "healthy_traders": self.metrics.healthy_traders,
                "total_trades": self.metrics.total_trades,
                "total_profit_loss": self.metrics.total_profit_loss,
                "uptime_seconds": self.metrics.uptime_seconds,
            },
            "traders": {
                trader_id: trader.get_status()
                for trader_id, trader in self._traders.items()
            },
        }

    async def get_health_status(self):
        """Получение статуса здоровья всех трейдеров"""

        @dataclass
        class HealthResult:
            failed_traders: List[str] = field(default_factory=list)
            warnings: List[str] = field(default_factory=list)

        result = HealthResult()

        # Проверяем здоровье каждого трейдера
        for trader_id, health in self._trader_health.items():
            if not health.is_healthy:
                result.failed_traders.append(trader_id)
            elif health.consecutive_errors > 3:
                result.warnings.append(
                    f"Трейдер {trader_id} имеет {health.consecutive_errors} последовательных ошибок"
                )

        # Проверяем общее состояние
        if self._state == ManagerState.ERROR:
            result.warnings.append("Менеджер трейдеров в состоянии ошибки")

        return result

    async def get_active_traders(self) -> List[TraderContext]:
        """Получение списка активных трейдеров"""
        active_traders = []
        for trader in self._traders.values():
            if trader.state in [TraderState.RUNNING, TraderState.PAUSED]:
                active_traders.append(trader)
        return active_traders

    async def get_total_traders(self) -> int:
        """Получение общего количества трейдеров"""
        return len(self._traders)

    async def get_statistics(self):
        """Получение статистики трейдеров"""

        @dataclass
        class TradingStats:
            active_traders: int = 0
            total_trades: int = 0

        stats = TradingStats()
        stats.active_traders = len(await self.get_active_traders())
        stats.total_trades = self.metrics.total_trades

        return stats

    async def emergency_stop(self):
        """Экстренная остановка всех трейдеров"""
        self.logger.error("🚨 Выполняется экстренная остановка всех трейдеров!")
        await self.stop_all_traders()


# Глобальный менеджер для удобства использования
_global_trader_manager: Optional[TraderManager] = None


def get_global_trader_manager() -> TraderManager:
    """Получение глобального экземпляра TraderManager"""
    global _global_trader_manager
    if _global_trader_manager is None:
        from core.config.config_manager import get_global_config_manager
        from core.traders.trader_factory import get_global_trader_factory

        _global_trader_manager = TraderManager(
            get_global_config_manager(), get_global_trader_factory()
        )
    return _global_trader_manager
