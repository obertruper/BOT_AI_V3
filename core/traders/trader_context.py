"""
Trader Context для BOT_Trading v3.0

Изолированный контекст для каждого трейдера в мульти-трейдер системе.
Обеспечивает полную изоляцию состояния, ресурсов и конфигурации
между различными трейдерами.

Каждый TraderContext содержит:
- Уникальную конфигурацию и настройки
- Собственный logger с префиксом
- Изолированные соединения с биржей и БД
- Независимое состояние и метрики
- Собственную ML модель и стратегию
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from core.config.config_manager import ConfigManager
from core.exceptions import TraderConfigurationError, TraderInitializationError
from utils.helpers import generate_id


class TraderState(Enum):
    """Состояния трейдера"""

    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class TraderMetrics:
    """Метрики трейдера"""

    trades_total: int = 0
    trades_successful: int = 0
    trades_failed: int = 0
    profit_loss: float = 0.0
    max_drawdown: float = 0.0
    current_positions: int = 0
    last_trade_time: Optional[datetime] = None
    uptime_seconds: float = 0.0
    errors_count: int = 0

    @property
    def success_rate(self) -> float:
        """Процент успешных сделок"""
        if self.trades_total == 0:
            return 0.0
        return (self.trades_successful / self.trades_total) * 100

    @property
    def win_rate(self) -> float:
        """Синоним для success_rate"""
        return self.success_rate


@dataclass
class TraderResources:
    """Ресурсы трейдера"""

    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    network_requests: int = 0
    database_queries: int = 0
    cache_hit_rate: float = 0.0


class TraderContext:
    """
    Изолированный контекст трейдера в BOT_Trading v3.0

    Обеспечивает полную изоляцию между трейдерами:
    - Собственная конфигурация и настройки
    - Изолированное логирование
    - Независимые соединения
    - Собственное состояние и метрики
    - Изоляция ошибок
    """

    def __init__(self, trader_id: str, config_manager: ConfigManager):
        self.trader_id = trader_id
        self.config_manager = config_manager
        self.session_id = generate_id("session")

        # Основные компоненты
        self._config: Dict[str, Any] = {}
        self._logger: Optional[logging.Logger] = None
        self._state = TraderState.CREATED
        self._created_at = datetime.now()
        self._started_at: Optional[datetime] = None
        self._stopped_at: Optional[datetime] = None

        # Метрики и ресурсы
        self.metrics = TraderMetrics()
        self.resources = TraderResources()

        # Компоненты трейдера (будут инициализированы позже)
        self.exchange = None
        self.strategy = None
        self.database = None
        self.ml_model = None
        self.risk_manager = None

        # Состояние и данные
        self._positions: Dict[str, Any] = {}
        self._orders: Dict[str, Any] = {}
        self._signals: List[Dict[str, Any]] = []
        self._errors: List[Dict[str, Any]] = []

        # Флаги управления
        self._is_initialized = False
        self._is_running = False
        self._should_stop = False

        # Lock для thread safety
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Инициализация контекста трейдера"""
        async with self._lock:
            if self._is_initialized:
                return

            try:
                self._state = TraderState.INITIALIZING

                # Загрузка конфигурации трейдера
                await self._load_trader_config()

                # Настройка логирования
                await self._setup_logging()

                # Валидация конфигурации
                await self._validate_config()

                self._logger.info(f"Трейдер {self.trader_id} инициализирован")
                self._state = TraderState.READY
                self._is_initialized = True

            except Exception as e:
                self._state = TraderState.ERROR
                error_msg = f"Ошибка инициализации трейдера {self.trader_id}: {e}"
                if self._logger:
                    self._logger.error(error_msg)
                else:
                    print(error_msg)
                raise TraderInitializationError(error_msg) from e

    async def _load_trader_config(self) -> None:
        """Загрузка конфигурации трейдера"""
        # Получение конфигурации из ConfigManager
        trader_config = self.config_manager.get_trader_config(self.trader_id)
        if not trader_config:
            raise TraderConfigurationError(
                f"Конфигурация для трейдера {self.trader_id} не найдена"
            )

        # Слияние с системной конфигурацией
        system_config = self.config_manager.get_system_config()

        self._config = {
            "trader": trader_config,
            "system": system_config,
            "database": self.config_manager.get_database_config(),
            "logging": self.config_manager.get_logging_config(),
        }

    async def _setup_logging(self) -> None:
        """Настройка логирования для трейдера"""
        from core.logging.logger_factory import LoggerFactory

        # Создание логгера с префиксом трейдера
        logger_name = f"trader.{self.trader_id}"
        self._logger = LoggerFactory.get_logger(
            logger_name, trader_id=self.trader_id, session_id=self.session_id
        )

    async def _validate_config(self) -> None:
        """Валидация конфигурации трейдера"""
        from core.config.validation import ConfigValidator

        validator = ConfigValidator()
        validation_results = validator.validate_trader_config(
            self.trader_id, self._config["trader"]
        )

        # Проверка критических ошибок
        errors = [r for r in validation_results if r.level.value == "error"]
        if errors:
            error_messages = [f"{r.field}: {r.message}" for r in errors]
            raise TraderConfigurationError(
                f"Ошибки конфигурации: {'; '.join(error_messages)}"
            )

        # Логирование предупреждений
        warnings = [r for r in validation_results if r.level.value == "warning"]
        for warning in warnings:
            self._logger.warning(f"Конфигурация {warning.field}: {warning.message}")

    async def start(self) -> None:
        """Запуск трейдера"""
        async with self._lock:
            if not self._is_initialized:
                await self.initialize()

            if self._state != TraderState.READY:
                raise ValueError(
                    f"Трейдер не готов к запуску. Текущее состояние: {self._state}"
                )

            try:
                self._state = TraderState.RUNNING
                self._started_at = datetime.now()
                self._is_running = True
                self._should_stop = False

                self._logger.info(f"Трейдер {self.trader_id} запущен")

            except Exception as e:
                self._state = TraderState.ERROR
                error_msg = f"Ошибка запуска трейдера {self.trader_id}: {e}"
                self._logger.error(error_msg)
                raise

    async def stop(self) -> None:
        """Остановка трейдера"""
        async with self._lock:
            if not self._is_running:
                return

            try:
                self._state = TraderState.STOPPING
                self._should_stop = True

                self._logger.info(f"Останавливаем трейдер {self.trader_id}...")

                # Закрытие соединений и ресурсов
                await self._cleanup_resources()

                self._state = TraderState.STOPPED
                self._stopped_at = datetime.now()
                self._is_running = False

                self._logger.info(f"Трейдер {self.trader_id} остановлен")

            except Exception as e:
                self._state = TraderState.ERROR
                error_msg = f"Ошибка остановки трейдера {self.trader_id}: {e}"
                self._logger.error(error_msg)
                raise

    async def pause(self) -> None:
        """Приостановка трейдера"""
        async with self._lock:
            if self._state == TraderState.RUNNING:
                self._state = TraderState.PAUSED
                self._logger.info(f"Трейдер {self.trader_id} приостановлен")

    async def resume(self) -> None:
        """Возобновление работы трейдера"""
        async with self._lock:
            if self._state == TraderState.PAUSED:
                self._state = TraderState.RUNNING
                self._logger.info(f"Трейдер {self.trader_id} возобновил работу")

    async def _cleanup_resources(self) -> None:
        """Очистка ресурсов трейдера"""
        # Закрытие соединений с биржей
        if self.exchange:
            try:
                await self.exchange.close()
            except Exception as e:
                self._logger.warning(f"Ошибка закрытия соединения с биржей: {e}")

        # Закрытие соединений с БД
        if self.database:
            try:
                await self.database.close()
            except Exception as e:
                self._logger.warning(f"Ошибка закрытия соединения с БД: {e}")

        # Очистка кешей и временных данных
        self._signals.clear()
        self._positions.clear()
        self._orders.clear()

    def get_config(self, key: str = None, default: Any = None) -> Any:
        """Получение конфигурации трейдера"""
        if key is None:
            return self._config.copy()

        # Поддержка вложенных ключей
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_trader_config(self, key: str = None, default: Any = None) -> Any:
        """Получение конфигурации конкретно трейдера"""
        trader_config = self._config.get("trader", {})

        if key is None:
            return trader_config

        # Поддержка вложенных ключей
        keys = key.split(".")
        value = trader_config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def is_enabled(self) -> bool:
        """Проверка, включен ли трейдер"""
        return self.get_trader_config("enabled", False)

    def get_exchange_name(self) -> str:
        """Получение названия биржи"""
        return self.get_trader_config("exchange", "unknown")

    def get_strategy_name(self) -> str:
        """Получение названия стратегии"""
        return self.get_trader_config("strategy", "unknown")

    def get_market_type(self) -> str:
        """Получение типа рынка"""
        return self.get_trader_config("market_type", "futures")

    def get_leverage(self) -> float:
        """Получение leverage для трейдера"""
        # Приоритет: конфигурация трейдера > системная конфигурация
        trader_leverage = self.get_trader_config("risk_management.leverage")
        if trader_leverage is not None:
            return float(trader_leverage)

        # Используем централизованную функцию
        return self.config_manager.get_leverage()

    def update_metrics(self, **kwargs) -> None:
        """Обновление метрик трейдера"""
        for key, value in kwargs.items():
            if hasattr(self.metrics, key):
                setattr(self.metrics, key, value)

    def add_error(self, error: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Добавление ошибки в историю"""
        error_record = {
            "timestamp": datetime.now(),
            "error": error,
            "details": details or {},
            "state": self._state.value,
        }
        self._errors.append(error_record)
        self.metrics.errors_count += 1

        # Ограничиваем размер истории ошибок
        if len(self._errors) > 100:
            self._errors = self._errors[-50:]  # Оставляем последние 50

    def get_status(self) -> Dict[str, Any]:
        """Получение полного статуса трейдера"""
        uptime = 0
        if self._started_at:
            uptime = (datetime.now() - self._started_at).total_seconds()

        return {
            "trader_id": self.trader_id,
            "session_id": self.session_id,
            "state": self._state.value,
            "is_running": self._is_running,
            "is_enabled": self.is_enabled(),
            "exchange": self.get_exchange_name(),
            "strategy": self.get_strategy_name(),
            "market_type": self.get_market_type(),
            "leverage": self.get_leverage(),
            "created_at": self._created_at.isoformat(),
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "stopped_at": self._stopped_at.isoformat() if self._stopped_at else None,
            "uptime_seconds": uptime,
            "metrics": {
                "trades_total": self.metrics.trades_total,
                "trades_successful": self.metrics.trades_successful,
                "success_rate": self.metrics.success_rate,
                "profit_loss": self.metrics.profit_loss,
                "current_positions": self.metrics.current_positions,
                "errors_count": self.metrics.errors_count,
            },
            "resources": {
                "memory_usage_mb": self.resources.memory_usage_mb,
                "cpu_usage_percent": self.resources.cpu_usage_percent,
            },
            "last_errors": self._errors[-5:]
            if self._errors
            else [],  # Последние 5 ошибок
        }

    @property
    def state(self) -> TraderState:
        """Текущее состояние трейдера"""
        return self._state

    @property
    def is_running(self) -> bool:
        """Запущен ли трейдер"""
        return self._is_running

    @property
    def should_stop(self) -> bool:
        """Должен ли трейдер остановиться"""
        return self._should_stop

    @property
    def logger(self) -> Optional[logging.Logger]:
        """Логгер трейдера"""
        return self._logger

    def __str__(self) -> str:
        return f"TraderContext({self.trader_id}, {self._state.value})"

    def __repr__(self) -> str:
        return f"TraderContext(trader_id='{self.trader_id}', state='{self._state.value}', exchange='{self.get_exchange_name()}')"
