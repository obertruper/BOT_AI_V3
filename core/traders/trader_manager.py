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
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

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
    """Состояния менеджера трейдеров."""

    CREATED = "created"
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class TraderHealthStatus:
    """Содержит информацию о здоровье отдельного трейдера."""

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
    """Содержит общие метрики производительности менеджера трейдеров."""

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
    """Управляет жизненным циклом и координацией всех торговых агентов (трейдеров).

    Этот класс является центральным узлом для мульти-трейдерной архитектуры.
    Он отвечает за создание, запуск, остановку и мониторинг каждого трейдера,
    обеспечивая их изоляцию и отказоустойчивость.
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        trader_factory: TraderFactory | None = None,
    ):
        """Инициализирует TraderManager.

        Args:
            config_manager: Менеджер конфигурации для доступа к настройкам.
            trader_factory: Фабрика для создания экземпляров трейдеров.
        """
        self.config_manager = config_manager
        self.trader_factory = trader_factory or TraderFactory(config_manager)
        self.logger = logging.getLogger(__name__)

        self._state = ManagerState.CREATED
        self._created_at = datetime.now()
        self._started_at: datetime | None = None
        self._stopped_at: datetime | None = None

        self._traders: dict[str, TraderContext] = {}
        self._trader_health: dict[str, TraderHealthStatus] = {}
        self._trader_tasks: dict[str, asyncio.Task] = {}

        self.metrics = ManagerMetrics()
        self._health_check_interval = 30
        self._health_check_task: asyncio.Task | None = None
        self._metrics_update_task: asyncio.Task | None = None

        self._max_traders = config_manager.get_config("system.limits.max_traders", 10)
        self._max_consecutive_errors = 5
        self._auto_recovery_enabled = config_manager.get_config("system.auto_recovery", True)

        self._event_callbacks: dict[str, list[Callable]] = {
            "trader_started": [],
            "trader_stopped": [],
            "trader_error": [],
            "trader_recovered": [],
            "health_check_failed": [],
        }

        self._thread_pool = ThreadPoolExecutor(max_workers=4)
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Асинхронно инициализирует менеджер и его компоненты.

        Загружает конфигурации трейдеров из `config_manager` и подготавливает
        менеджер к запуску.

        Raises:
            TraderManagerError: Если произошла ошибка во время инициализации.
        """
        async with self._lock:
            if self._state != ManagerState.CREATED:
                return
            try:
                self._state = ManagerState.INITIALIZING
                self.logger.info("Инициализация менеджера трейдеров...")
                if not hasattr(self.trader_factory, "_is_initialized"):
                    await self._initialize_trader_factory()
                await self._load_trader_configurations()
                self.logger.info("Менеджер трейдеров инициализирован")
                self._state = ManagerState.RUNNING
            except Exception as e:
                self._state = ManagerState.ERROR
                error_msg = f"Ошибка инициализации менеджера трейдеров: {e}"
                self.logger.error(error_msg)
                raise TraderManagerError(error_msg) from e

    async def start(self) -> None:
        """Запускает менеджер и все включенные в конфигурации трейдеры.

        Также запускает фоновые задачи для мониторинга здоровья и сбора метрик.
        """
        async with self._lock:
            if self._state == ManagerState.RUNNING:
                return
            if self._state != ManagerState.RUNNING:
                await self.initialize()
            try:
                self.logger.info("Запуск менеджера трейдеров...")
                self._started_at = datetime.now()
                await self._start_monitoring()
                await self._start_enabled_traders()
                self.logger.info("Менеджер трейдеров запущен")
            except Exception as e:
                self._state = ManagerState.ERROR
                error_msg = f"Ошибка запуска менеджера трейдеров: {e}"
                self.logger.error(error_msg)
                raise TraderManagerError(error_msg) from e

    async def stop(self) -> None:
        """Корректно останавливает менеджер и всех запущенных трейдеров."""
        async with self._lock:
            if self._state in [ManagerState.STOPPED, ManagerState.STOPPING]:
                return
            try:
                self._state = ManagerState.STOPPING
                self.logger.info("Остановка менеджера трейдеров...")
                await self._stop_monitoring()
                await self._stop_all_traders()
                self._thread_pool.shutdown(wait=True)
                self._state = ManagerState.STOPPED
                self._stopped_at = datetime.now()
                self.logger.info("Менеджер трейдеров остановлен")
            except Exception as e:
                self._state = ManagerState.ERROR
                error_msg = f"Ошибка остановки менеджера трейдеров: {e}"
                self.logger.error(error_msg)
                raise TraderManagerError(error_msg) from e

    async def create_trader(self, trader_id: str) -> TraderContext:
        """Создает, инициализирует и регистрирует нового трейдера.

        Args:
            trader_id: Уникальный идентификатор трейдера, соответствующий
                его конфигурации.

        Returns:
            Экземпляр TraderContext для созданного трейдера.

        Raises:
            TraderAlreadyExistsError: Если трейдер с таким ID уже существует.
            TooManyTradersError: Если превышен лимит на количество трейдеров.
            TraderManagerError: В случае других ошибок при создании.
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
                trader_context = await self.trader_factory.create_trader(trader_id)
                self._traders[trader_id] = trader_context
                self._trader_health[trader_id] = TraderHealthStatus(
                    trader_id=trader_id, is_healthy=True, last_check=datetime.now()
                )
                self.metrics.total_traders = len(self._traders)
                self.logger.info(f"Трейдер {trader_id} создан")
                return trader_context
            except Exception as e:
                error_msg = f"Ошибка создания трейдера {trader_id}: {e}"
                self.logger.error(error_msg)
                raise TraderManagerError(error_msg) from e

    async def start_trader(self, trader_id: str) -> None:
        """Запускает торговую логику для указанного трейдера.

        Создает для трейдера асинхронную задачу и отслеживает ее выполнение.

        Args:
            trader_id: Идентификатор трейдера для запуска.

        Raises:
            TraderNotFoundError: Если трейдер с таким ID не найден.
            TraderManagerError: В случае ошибки при запуске.
        """
        if trader_id not in self._traders:
            await self.create_trader(trader_id)
        trader_context = self._traders[trader_id]
        if trader_context.is_running:
            self.logger.warning(f"Трейдер {trader_id} уже запущен")
            return
        try:
            self.logger.info(f"Запуск трейдера {trader_id}...")
            await trader_context.start()
            task = asyncio.create_task(self._run_trader(trader_context))
            self._trader_tasks[trader_id] = task
            self.metrics.active_traders = len([t for t in self._traders.values() if t.is_running])
            await self._emit_event("trader_started", trader_id, trader_context)
            self.logger.info(f"Трейдер {trader_id} запущен")
        except Exception as e:
            error_msg = f"Ошибка запуска трейдера {trader_id}: {e}"
            self.logger.error(error_msg)
            if trader_id in self._trader_health:
                self._trader_health[trader_id].error_count += 1
                self._trader_health[trader_id].consecutive_errors += 1
            await self._emit_event("trader_error", trader_id, e)
            raise TraderManagerError(error_msg) from e

    async def stop_trader(self, trader_id: str) -> None:
        """Останавливает торговую логику для указанного трейдера.

        Args:
            trader_id: Идентификатор трейдера для остановки.

        Raises:
            TraderNotFoundError: Если трейдер с таким ID не найден.
        """
        if trader_id not in self._traders:
            raise TraderNotFoundError(f"Трейдер {trader_id} не найден")
        trader_context = self._traders[trader_id]
        try:
            self.logger.info(f"Остановка трейдера {trader_id}...")
            if trader_id in self._trader_tasks:
                task = self._trader_tasks[trader_id]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                del self._trader_tasks[trader_id]
            await trader_context.stop()
            self.metrics.active_traders = len([t for t in self._traders.values() if t.is_running])
            await self._emit_event("trader_stopped", trader_id, trader_context)
            self.logger.info(f"Трейдер {trader_id} остановлен")
        except Exception as e:
            error_msg = f"Ошибка остановки трейдера {trader_id}: {e}"
            self.logger.error(error_msg)
            raise TraderManagerError(error_msg) from e

    def get_trader_statistics(self, trader_id: str) -> dict[str, Any]:
        """Получает статистику по трейдеру."""
        trader_context = self.traders.get(trader_id)
        if not trader_context:
            return {}
        
        return {
            'id': trader_id,
            'status': trader_context.status,
            'created_at': trader_context.created_at,
            'last_activity': trader_context.last_activity,
            'trades_count': getattr(trader_context, 'trades_count', 0),
            'performance_metrics': getattr(trader_context, 'performance_metrics', {})
        }
    
    def _cleanup_inactive_traders(self) -> None:
        """Очищает неактивные трейдеры."""
        current_time = datetime.now()
        inactive_threshold = timedelta(hours=1)  # 1 час неактивности
        
        traders_to_remove = []
        for trader_id, trader_context in self.traders.items():
            if (current_time - trader_context.last_activity) > inactive_threshold:
                if trader_context.status == 'stopped':
                    traders_to_remove.append(trader_id)
        
        for trader_id in traders_to_remove:
            self.remove_trader(trader_id)
            self.logger.info(f"Удален неактивный трейдер: {trader_id}")
    
    def _validate_trader_config(self, config: dict) -> None:
        """Валидация конфигурации трейдера перед созданием."""
        required_fields = ['id', 'type', 'exchange', 'strategy']
        
        for field in required_fields:
            if field not in config:
                raise ConfigurationError(f"Отсутствует обязательное поле '{field}' в конфигурации трейдера")
        
        # Проверяем уникальность ID
        if config['id'] in self.traders:
            raise ConfigurationError(f"Трейдер с ID '{config['id']}' уже существует")
    
    def get_active_traders_count(self) -> int:
        """Возвращает количество активных трейдеров."""
        return len([t for t in self.traders.values() if t.status == 'running'])
    
    def get_all_traders_info(self) -> dict[str, dict]:
        """Возвращает информацию о всех трейдерах."""
        return {
            trader_id: self.get_trader_statistics(trader_id) 
            for trader_id in self.traders.keys()
        }


# Глобальная переменная для singleton instance
_global_trader_manager: TraderManager | None = None


def get_global_trader_manager() -> TraderManager:
    """Получает глобальный экземпляр TraderManager (singleton)"""
    global _global_trader_manager
    if _global_trader_manager is None:
        from core.traders.trader_factory import get_global_trader_factory
        from core.config.config_manager import get_global_config_manager
        
        config_manager = get_global_config_manager()
        trader_factory = get_global_trader_factory()
        _global_trader_manager = TraderManager(config_manager, trader_factory)
    return _global_trader_manager
