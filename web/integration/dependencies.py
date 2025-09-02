"""
Dependency Injection для Web API

Центральная система внедрения зависимостей для интеграции
веб-интерфейса с компонентами BOT_Trading v3.0.

Обеспечивает прямой доступ к:
- TraderManager (из core.system)
- ExchangeFactory (из exchanges)
- ConfigManager (из core.config)
- MetricsCollector (из monitoring)
"""

from contextlib import asynccontextmanager
from typing import Any, Optional

# Условные импорты для разработки
try:
    from core.system.orchestrator import SystemOrchestrator
except ImportError:
    SystemOrchestrator = None

try:
    from core.traders.trader_manager import TraderManager
except ImportError:
    TraderManager = None

try:
    from core.config.config_manager import ConfigManager
except ImportError:
    ConfigManager = None

try:
    from core.logging.logger_factory import get_global_logger_factory
except ImportError:
    get_global_logger_factory = None

try:
    from exchanges.factory import ExchangeFactory
except ImportError:
    ExchangeFactory = None

try:
    from exchanges.registry import ExchangeRegistry
except ImportError:
    ExchangeRegistry = None

try:
    from monitoring.metrics.collector import MetricsCollector
except ImportError:
    MetricsCollector = None

try:
    from core.system.health_checker import HealthChecker
except ImportError:
    HealthChecker = None

# Инициализация логирования
if get_global_logger_factory:
    logger_factory = get_global_logger_factory()
    logger = logger_factory.get_logger("web_dependencies")
else:
    import logging

    logger = logging.getLogger("web_dependencies")

# Глобальные переменные для хранения компонентов системы
_orchestrator: SystemOrchestrator = None
_trader_manager: TraderManager = None

_exchange_factory: ExchangeFactory = None
_exchange_registry: ExchangeRegistry = None
_config_manager: ConfigManager = None
_metrics_collector: MetricsCollector = None
_health_checker: HealthChecker = None

# Дополнительные сервисы
_user_manager: Any = None
_session_manager: Any = None
_stats_service: Any = None
_alerts_service: Any = None
_logs_service: Any = None
_strategy_registry: Any = None
_strategy_manager: Any = None
_backtest_engine: Any = None
_performance_service: Any = None


class DependencyContainer:
    """
    Контейнер зависимостей для веб-интерфейса

    Обеспечивает централизованное управление всеми компонентами
    системы и их внедрение в веб API endpoints.
    """

    def __init__(self, orchestrator: SystemOrchestrator):
        self.orchestrator = orchestrator
        self._initialized = False

    async def initialize(self):
        """Инициализация всех зависимостей"""
        if self._initialized:
            return

        logger.info("Инициализация контейнера зависимостей веб-интерфейса")

        global _orchestrator, _trader_manager, _exchange_factory, _exchange_registry
        global _config_manager, _metrics_collector, _health_checker

        try:
            # Основные компоненты системы
            _orchestrator = self.orchestrator
            _trader_manager = self.orchestrator.trader_manager
            _exchange_factory = self.orchestrator.exchange_factory
            _exchange_registry = self.orchestrator.exchange_registry
            _config_manager = self.orchestrator.config_manager
            _health_checker = self.orchestrator.health_checker

            # Метрики
            if hasattr(self.orchestrator, "metrics_collector"):
                _metrics_collector = self.orchestrator.metrics_collector

            # Инициализируем дополнительные сервисы
            await self._initialize_additional_services()

            self._initialized = True
            logger.info("Контейнер зависимостей успешно инициализирован")

        except Exception as e:
            logger.error(f"Ошибка инициализации контейнера зависимостей: {e}")
            raise

    async def _initialize_additional_services(self):
        """Инициализация дополнительных сервисов"""
        global _user_manager, _session_manager, _stats_service, _alerts_service
        global _logs_service, _strategy_registry, _strategy_manager
        global _backtest_engine, _performance_service

        try:
            # Заглушки для сервисов, которые будут реализованы позже
            from .mock_services import (
                MockAlertsService,
                MockBacktestEngine,
                MockLogsService,
                MockPerformanceService,
                MockSessionManager,
                MockStatsService,
                MockStrategyManager,
                MockStrategyRegistry,
                MockUserManager,
            )

            _user_manager = MockUserManager()
            _session_manager = MockSessionManager()
            _stats_service = MockStatsService()
            _alerts_service = MockAlertsService()
            _logs_service = MockLogsService()
            _strategy_registry = MockStrategyRegistry()
            _strategy_manager = MockStrategyManager()
            _backtest_engine = MockBacktestEngine()
            _performance_service = MockPerformanceService()

            logger.info("Дополнительные сервисы инициализированы (mock)")

        except ImportError:
            logger.warning("Mock сервисы не найдены, используем заглушки")
            # Создаем простые заглушки
            _user_manager = None
            _session_manager = None
            _stats_service = None
            _alerts_service = None
            _logs_service = None
            _strategy_registry = None
            _strategy_manager = None
            _backtest_engine = None
            _performance_service = None

    async def cleanup(self):
        """Очистка ресурсов"""
        logger.info("Очистка контейнера зависимостей")
        self._initialized = False


# =================== CORE DEPENDENCIES ===================


def get_orchestrator_dependency() -> SystemOrchestrator:
    """Получить orchestrator"""
    if _orchestrator is None:
        raise RuntimeError(
            "Orchestrator не инициализирован. Вызовите initialize_dependencies() сначала."
        )
    return _orchestrator


def get_trader_manager_dependency() -> TraderManager:
    """Получить trader_manager"""
    if _trader_manager is None:
        raise RuntimeError(
            "TraderManager не инициализирован. Вызовите initialize_dependencies() сначала."
        )
    return _trader_manager


def get_exchange_factory_dependency() -> ExchangeFactory:
    """Получить exchange_factory"""
    if _exchange_factory is None:
        raise RuntimeError(
            "ExchangeFactory не инициализирован. Вызовите initialize_dependencies() сначала."
        )
    return _exchange_factory


def get_exchange_registry_dependency() -> ExchangeRegistry:
    """Получить exchange_registry"""
    if _exchange_registry is None:
        raise RuntimeError(
            "ExchangeRegistry не инициализирован. Вызовите initialize_dependencies() сначала."
        )
    return _exchange_registry


def get_config_manager_dependency() -> ConfigManager:
    """Получить config_manager"""
    if _config_manager is None:
        raise RuntimeError(
            "ConfigManager не инициализирован. Вызовите initialize_dependencies() сначала."
        )
    return _config_manager


def get_metrics_collector_dependency() -> Optional[MetricsCollector]:
    """Получить metrics_collector"""
    return _metrics_collector


def get_health_checker_dependency() -> HealthChecker:
    """Получить health_checker"""
    if _health_checker is None:
        raise RuntimeError(
            "HealthChecker не инициализирован. Вызовите initialize_dependencies() сначала."
        )
    return _health_checker


# =================== ADDITIONAL SERVICES DEPENDENCIES ===================


def get_user_manager_dependency():
    """Получить user_manager"""
    return _user_manager


def get_session_manager_dependency():
    """Получить session_manager"""
    return _session_manager


def get_stats_service_dependency():
    """Получить stats_service"""
    return _stats_service


def get_alerts_service_dependency():
    """Получить alerts_service"""
    return _alerts_service


def get_logs_service_dependency():
    """Получить logs_service"""
    return _logs_service


def get_strategy_registry_dependency():
    """Получить strategy_registry"""
    return _strategy_registry


def get_strategy_manager_dependency():
    """Получить strategy_manager"""
    return _strategy_manager


def get_backtest_engine_dependency():
    """Получить backtest_engine"""
    return _backtest_engine


def get_performance_service_dependency():
    """Получить performance_service"""
    return _performance_service


# =================== INITIALIZATION FUNCTIONS ===================


async def initialize_dependencies(orchestrator: SystemOrchestrator):
    """
    Инициализация всех зависимостей для веб-интерфейса

    Args:
        orchestrator: Главный оркестратор системы
    """
    container = DependencyContainer(orchestrator)
    await container.initialize()

    logger.info("Зависимости веб-интерфейса инициализированы")


async def cleanup_dependencies():
    """Очистка всех зависимостей"""
    global _orchestrator, _trader_manager, _exchange_factory, _exchange_registry
    global _config_manager, _metrics_collector, _health_checker
    global _user_manager, _session_manager, _stats_service, _alerts_service
    global _logs_service, _strategy_registry, _strategy_manager
    global _backtest_engine, _performance_service

    logger.info("Очистка зависимостей веб-интерфейса")

    # Сбрасываем все глобальные переменные
    _orchestrator = None
    _trader_manager = None
    _exchange_factory = None
    _exchange_registry = None
    _config_manager = None
    _metrics_collector = None
    _health_checker = None
    _user_manager = None
    _session_manager = None
    _stats_service = None
    _alerts_service = None
    _logs_service = None
    _strategy_registry = None
    _strategy_manager = None
    _backtest_engine = None
    _performance_service = None


# =================== DEPENDENCY CONTEXT MANAGER ===================


@asynccontextmanager
async def dependency_context(orchestrator: SystemOrchestrator):
    """
    Контекстный менеджер для управления жизненным циклом зависимостей

    Использование:
    async with dependency_context(orchestrator):
        # Веб-сервер работает с инициализированными зависимостями
        pass
    """
    try:
        await initialize_dependencies(orchestrator)
        yield
    finally:
        await cleanup_dependencies()


# =================== HEALTH CHECK ===================


def check_dependencies_health() -> dict:
    """Проверка здоровья всех зависимостей"""
    health_status = {
        "orchestrator": _orchestrator is not None,
        "trader_manager": _trader_manager is not None,
        "exchange_factory": _exchange_factory is not None,
        "exchange_registry": _exchange_registry is not None,
        "config_manager": _config_manager is not None,
        "metrics_collector": _metrics_collector is not None,
        "health_checker": _health_checker is not None,
        "user_manager": _user_manager is not None,
        "session_manager": _session_manager is not None,
        "stats_service": _stats_service is not None,
        "alerts_service": _alerts_service is not None,
        "logs_service": _logs_service is not None,
        "strategy_registry": _strategy_registry is not None,
        "strategy_manager": _strategy_manager is not None,
        "backtest_engine": _backtest_engine is not None,
        "performance_service": _performance_service is not None,
    }

    all_healthy = all(health_status.values())

    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "components": health_status,
        "initialized_count": sum(health_status.values()),
        "total_count": len(health_status),
    }


# =================== UTILITY FUNCTIONS ===================


def get_dependency_info() -> dict:
    """Получить информацию о текущих зависимостях"""
    return {
        "orchestrator": {
            "class": type(_orchestrator).__name__ if _orchestrator else None,
            "initialized": _orchestrator is not None,
        },
        "trader_manager": {
            "class": type(_trader_manager).__name__ if _trader_manager else None,
            "initialized": _trader_manager is not None,
        },
        "exchange_factory": {
            "class": type(_exchange_factory).__name__ if _exchange_factory else None,
            "initialized": _exchange_factory is not None,
        },
        "config_manager": {
            "class": type(_config_manager).__name__ if _config_manager else None,
            "initialized": _config_manager is not None,
        },
    }
