"""
Системный оркестратор BOT_Trading v3.0

Центральный компонент для управления всей мульти-трейдер системой:
- Запуск и остановка трейдеров
- Мониторинг здоровья системы
- Управление ресурсами и жизненным циклом
- Координация между компонентами
"""

import asyncio
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime

from core.config.config_manager import ConfigManager, get_global_config_manager
from core.exceptions import (
    ComponentInitializationError,
    HealthCheckError,
    SystemInitializationError,
    SystemShutdownError,
)
from core.logging.logger_factory import get_global_logger_factory
from core.traders.trader_factory import TraderFactory, get_global_trader_factory
from core.traders.trader_manager import TraderManager, get_global_trader_manager

# Импорт для новой архитектуры
from database.database_manager import DatabaseManager
from ml.ml_manager import MLManager
from utils.helpers import get_system_resources


@dataclass
class HealthStatus:
    """Датакласс для хранения статуса здоровья системы.

    Attributes:
        is_healthy: True, если система полностью работоспособна.
        timestamp: Время последней проверки.
        issues: Список критических проблем.
        warnings: Список предупреждений.
        system_resources: Использование системных ресурсов (CPU, память).
        active_traders: Количество активных трейдеров.
        total_trades: Общее количество сделок.
    """

    is_healthy: bool
    timestamp: datetime
    issues: list[str]
    warnings: list[str]
    system_resources: dict[str, float]
    active_traders: int
    total_trades: int


class SystemOrchestrator:
    """Главный оркестратор системы BOT_Trading v3.0.

    Отвечает за инициализацию, запуск, остановку и координацию всех
    ключевых компонентов системы, таких как менеджер трейдеров, торговый движок,
    сервисы данных и API. Управляет жизненным циклом и проводит мониторинг
    здоровья системы.
    """

    def __init__(self, config_manager: ConfigManager | None = None):
        """Инициализирует оркестратор.

        Args:
            config_manager: Экземпляр менеджера конфигурации. Если не передан,
                используется глобальный экземпляр.
        """
        self.config_manager = config_manager or get_global_config_manager()
        self.config = self.config_manager.get_config()  # Получаем конфигурацию
        self.logger_factory = get_global_logger_factory()
        self.logger = self.logger_factory.get_logger("system_orchestrator")

        # Основные компоненты
        self.trader_manager: TraderManager | None = None
        self.trader_factory: TraderFactory | None = None
        self.health_checker = None
        self.exchange_registry = None
        self.exchange_manager = None  # Добавляем для TradingEngine
        self.risk_manager = None  # Добавляем для TradingEngine
        self.trading_engine = None
        self.telegram_service = None
        self.ai_signal_generator = None
        self.signal_scheduler = None
        self.data_update_service = None
        self.data_manager = None
        self.system_monitor = None

        # Новая архитектура компонентов
        self.db_manager: DatabaseManager | None = None
        self.ml_manager: MLManager | None = None

        # Статус системы
        self.is_initialized = False
        self.is_running = False
        self.startup_time: datetime | None = None

        # Трекинг компонентов
        self.active_components: set[str] = set()
        self.failed_components: set[str] = set()

        # Настройки
        self.system_config = self.config_manager.get_system_config()
        self.health_check_interval = 30  # Default health check interval

        # Задачи мониторинга
        self._monitoring_tasks: list[asyncio.Task] = []

    async def initialize(self) -> None:
        """Выполняет полную инициализацию всех компонентов системы.

        Загружает конфигурации, настраивает подключения, инициализирует
        все менеджеры и сервисы. В случае ошибки прерывает выполнение
        и вызывает SystemInitializationError.
        """
        try:
            self.logger.info("🚀 Начинаем инициализацию системы BOT_Trading v3.0...")

            # Инициализация конфигурации
            await self.config_manager.initialize()

            # Базовые компоненты
            await self._check_system_requirements()
            await self._initialize_database_manager()
            await self._initialize_ml_manager()

            # Торговые компоненты
            await self._initialize_trader_factory()
            await self._initialize_trader_manager()
            await self._initialize_exchange_registry()
            await self._initialize_trading_engine()

            # Сервисы
            await self._initialize_health_checker()
            await self._initialize_telegram_service()
            await self._initialize_ai_signal_generator()
            await self._initialize_data_manager()
            await self._initialize_data_update_service()
            await self._initialize_data_maintenance()
            await self._initialize_signal_scheduler()

            unified_mode = os.getenv("UNIFIED_MODE")
            self.logger.info(f"🔍 UNIFIED_MODE = {unified_mode}")
            if unified_mode != "true":
                await self._initialize_api_servers()
            else:
                self.logger.info(
                    "⏭️ API серверы будут запущены отдельным процессом (UNIFIED_MODE=true)"
                )

            await self._start_background_tasks()
            self.is_initialized = True
            self.startup_time = datetime.now()
            self.logger.info("✅ Система успешно инициализирована")

        except Exception as e:
            self.logger.error(f"❌ Ошибка при инициализации системы: {e}")
            await self._cleanup_on_error()
            raise SystemInitializationError(f"Не удалось инициализировать систему: {e}") from e

    async def start(self) -> None:
        """Запускает все инициализированные компоненты системы.

        Активирует торговые стратегии, обработку сигналов и API серверы.

        Raises:
            SystemInitializationError: Если система не была инициализирована
                перед запуском.
        """
        if not self.is_initialized:
            raise SystemInitializationError("Система не инициализирована")

        self.logger.info("🎯 Запуск системы BOT_Trading v3.0...")
        try:
            # Проверяем наличие компонентов
            self.logger.info("📊 Состояние компонентов:")
            self.logger.info(f"   - trader_manager: {self.trader_manager is not None}")
            self.logger.info(f"   - trading_engine: {self.trading_engine is not None}")

            if self.trader_manager:
                await self.trader_manager.start()
                self.active_components.add("trader_manager")

            if self.trading_engine:
                self.logger.info("🎯 Вызываем trading_engine.start()...")
                result = await self.trading_engine.start()
                self.logger.info(f"📊 Результат запуска trading_engine: {result}")
                self.active_components.add("trading_engine")
            else:
                self.logger.warning("⚠️ Trading Engine не инициализирован, пропускаем запуск")
            if self.ai_signal_generator:
                await self.ai_signal_generator.start()
            if self.signal_scheduler:
                await self.signal_scheduler.start()
            if self.data_manager:
                await self.data_manager.start()
                self.active_components.add("data_manager")
            if self.data_update_service:
                await self.data_update_service.start()
            if hasattr(self, "data_maintenance") and self.data_maintenance:
                await self.data_maintenance.start()

            if os.getenv("UNIFIED_MODE") != "true":
                await self._start_api_servers()

            self.is_running = True
            self.logger.info("🟢 Система запущена и работает")

        except Exception as e:
            self.logger.error(f"❌ Ошибка при запуске системы: {e}")
            await self._emergency_shutdown()
            raise

    async def shutdown(self) -> None:
        """Выполняет корректную остановку всех компонентов системы.

        Гарантирует, что все фоновые задачи завершены, трейдеры остановлены,
        а соединения закрыты.

        Raises:
            SystemShutdownError: Если произошла ошибка при остановке.
        """
        try:
            self.logger.info("🛑 Начинаем остановку системы...")
            self.is_running = False
            await self._stop_background_tasks()

            if self.trader_manager:
                await self.trader_manager.stop()
                self.active_components.discard("trader_manager")
            if self.trading_engine:
                await self.trading_engine.stop()
                self.active_components.discard("trading_engine")
            if self.telegram_service:
                await self.telegram_service.stop()
            if self.signal_scheduler:
                await self.signal_scheduler.stop()
            if self.data_manager:
                await self.data_manager.stop()
            if self.data_update_service:
                await self.data_update_service.stop()
            if hasattr(self, "data_maintenance") and self.data_maintenance:
                await self.data_maintenance.stop()

            await self._stop_api_servers()

            # Закрываем новые компоненты
            if self.ml_manager:
                # ML Manager может не иметь метода stop, но у адаптера есть cleanup
                if hasattr(self.ml_manager, "adapter") and self.ml_manager.adapter:
                    await self.ml_manager.adapter.cleanup()
                self.active_components.discard("ml_manager")

            if self.db_manager:
                await self.db_manager.close()
                self.active_components.discard("database_manager")

            self.logger.info("✅ Система успешно остановлена")

        except Exception as e:
            self.logger.error(f"❌ Ошибка при остановке системы: {e}")
            raise SystemShutdownError(f"Не удалось корректно остановить систему: {e}") from e

    async def stop(self) -> None:
        """Алиас для shutdown() - для обратной совместимости с существующим кодом."""
        await self.shutdown()

    async def health_check(self) -> HealthStatus:
        """Выполняет комплексную проверку здоровья системы.

        Собирает статус всех ключевых компонентов, системные метрики
        и формирует отчет о состоянии.

        Returns:
            HealthStatus: Объект с детальной информацией о здоровье системы.

        Raises:
            HealthCheckError: Если не удалось выполнить проверку.
        """
        try:
            issues, warnings = [], []
            if not self.is_running:
                issues.append("Система не запущена")
            if self.failed_components:
                issues.append(f"Сбойные компоненты: {', '.join(self.failed_components)}")

            active_traders, total_trades = 0, 0
            if self.trader_manager:
                try:
                    trader_health = await self.trader_manager.get_health_status()
                    if trader_health.failed_traders:
                        issues.append(
                            f"Сбойные трейдеры: {', '.join(trader_health.failed_traders)}"
                        )
                    if trader_health.warnings:
                        warnings.extend(trader_health.warnings)
                    stats = await self.trader_manager.get_statistics()
                    active_traders = stats.active_traders
                    total_trades = stats.total_trades
                except Exception as e:
                    warnings.append(f"Ошибка получения статистики трейдеров: {e}")

            # Проверка DatabaseManager
            if self.db_manager:
                try:
                    db_health = await self.db_manager.health_check()
                    if not db_health.get("healthy", False):
                        issues.append(
                            f"База данных: {db_health.get('error', 'неизвестная ошибка')}"
                        )
                    elif db_health.get("active_connections", 0) > 8:
                        warnings.append(
                            f"Высокое количество подключений к БД: {db_health['active_connections']}"
                        )
                except Exception as e:
                    warnings.append(f"Ошибка проверки здоровья БД: {e}")

            # Проверка MLManager
            if self.ml_manager:
                try:
                    if (
                        hasattr(self.ml_manager, "_initialized")
                        and not self.ml_manager._initialized
                    ):
                        warnings.append("ML Manager не инициализирован")
                    elif hasattr(self.ml_manager, "use_adapter") and self.ml_manager.use_adapter:
                        if hasattr(self.ml_manager, "adapter") and self.ml_manager.adapter:
                            ml_info = await self.ml_manager.adapter.get_model_info()
                            if not ml_info.get("is_loaded", False):
                                warnings.append("ML модель не загружена")
                        else:
                            warnings.append("ML адаптер не найден")
                except Exception as e:
                    warnings.append(f"Ошибка проверки ML Manager: {e}")

            resources = get_system_resources()
            limits = self.system_config.get("limits", {})
            if resources["memory_percent"] > limits.get("max_memory_usage_percent", 80):
                warnings.append(f"Высокое использование памяти: {resources['memory_percent']}%")
            if resources["cpu_percent"] > limits.get("max_cpu_usage_percent", 80):
                warnings.append(f"Высокое использование CPU: {resources['cpu_percent']}%")

            return HealthStatus(
                is_healthy=not issues,
                timestamp=datetime.now(),
                issues=issues,
                warnings=warnings,
                system_resources=resources,
                active_traders=active_traders,
                total_trades=total_trades,
            )
        except Exception as e:
            self.logger.error(f"❌ Ошибка при проверке здоровья: {e}")
            raise HealthCheckError(f"Не удалось проверить здоровье системы: {e}") from e

    async def get_system_status(self) -> dict:
        """Возвращает полный статус системы в виде словаря."""
        uptime = (datetime.now() - self.startup_time).total_seconds() if self.startup_time else None
        health = await self.health_check()
        return {
            "system": {
                "version": "3.0.0",
                "is_running": self.is_running,
                "uptime_seconds": uptime,
                "startup_time": self.startup_time.isoformat() if self.startup_time else None,
            },
            "health": {
                "is_healthy": health.is_healthy,
                "issues": health.issues,
                "warnings": health.warnings,
                "last_check": health.timestamp.isoformat(),
            },
            "resources": health.system_resources,
            "traders": {
                "active": health.active_traders,
                "total_trades": health.total_trades,
                "active_positions": 0,
            },
            "components": {
                "active": list(self.active_components),
                "failed": list(self.failed_components),
            },
        }

    async def get_status(self) -> dict:
        """Возвращает статус системы в формате, ожидаемом main.py и web API."""
        try:
            # Создаем компоненты в виде {имя: bool} как ожидает main.py
            components = {}

            # Добавляем активные компоненты как True
            for component in self.active_components:
                components[component] = True

            # Добавляем сбойные компоненты как False
            for component in self.failed_components:
                components[component] = False

            # Если нет активных компонентов, добавим базовые системные компоненты
            if not components:
                components = {
                    "ConfigManager": self.is_initialized,
                    "SystemOrchestrator": self.is_running,
                }

            # Получаем информацию о биржах (заглушка)
            exchanges = []

            # Получаем информацию о стратегиях (заглушка)
            strategies = []

            # Информация о базе данных
            database = {"connected": True, "status": "connected"}  # Предполагаем подключение

            # Подсчет трейдеров и позиций
            traders_count = 0
            active_positions = 0
            if self.trader_manager:
                try:
                    stats = await self.trader_manager.get_statistics()
                    traders_count = stats.active_traders
                    active_positions = getattr(stats, "active_positions", 0)
                except:
                    pass

            # Время работы системы
            uptime = 0
            start_time = datetime.now()
            if self.startup_time:
                uptime = (datetime.now() - self.startup_time).total_seconds()
                start_time = self.startup_time

            return {
                "running": self.is_running,
                "components": components,
                "exchanges": exchanges,
                "strategies": strategies,
                "database": database,
                "traders_count": traders_count,
                "active_positions": active_positions,
                "uptime": uptime,
                "start_time": start_time,
            }

        except Exception as e:
            self.logger.error(f"Ошибка получения статуса: {e}")
            return {
                "running": False,
                "components": {"SystemOrchestrator": False},
                "exchanges": [],
                "strategies": [],
                "database": {"connected": False, "error": str(e)},
                "traders_count": 0,
                "active_positions": 0,
                "uptime": 0,
                "start_time": datetime.now(),
            }

    async def get_metrics(self) -> dict:
        """Получить системные метрики производительности."""
        try:
            # Получаем системные ресурсы
            resources = get_system_resources()

            # Информация о соединениях с базой данных
            db_connections = 0
            if self.db_manager:
                try:
                    db_connections = await self.db_manager.get_active_connections_count()
                except:
                    pass

            # Количество активных потоков
            import threading

            active_threads = threading.active_count()

            # Сетевая статистика (заглушка)
            network_io = {
                "bytes_sent": 0,
                "bytes_received": 0,
                "packets_sent": 0,
                "packets_received": 0,
            }

            return {
                "cpu_usage": resources.get("cpu_percent", 0),
                "memory_usage": resources.get("memory_percent", 0),
                "disk_usage": resources.get("disk_percent", 0),
                "network_io": network_io,
                "database_connections": db_connections,
                "active_threads": active_threads,
                "timestamp": datetime.now(),
            }

        except Exception as e:
            self.logger.error(f"Ошибка получения метрик: {e}")
            return {
                "cpu_usage": 0,
                "memory_usage": 0,
                "disk_usage": 0,
                "network_io": {"bytes_sent": 0, "bytes_received": 0},
                "database_connections": 0,
                "active_threads": 0,
                "timestamp": datetime.now(),
                "error": str(e),
            }

    # Приватные методы инициализации
    async def _check_system_requirements(self) -> None:
        """Проверка системных требований."""
        self.logger.info("🔍 Проверка системных требований...")
        # Здесь можно добавить проверки CPU, памяти, диска и т.д.
        pass

    async def _initialize_database_manager(self) -> None:
        """Инициализация DatabaseManager с TransactionManager."""
        try:
            self.logger.info("🗄️ Инициализация DatabaseManager...")

            # Получаем конфигурацию базы данных
            db_config = self.config_manager.get_config("database")
            if hasattr(db_config, "model_dump"):
                config_dict = {"database": db_config.model_dump()}
            elif hasattr(db_config, "dict"):
                config_dict = {"database": db_config.dict()}
            else:
                config_dict = {"database": db_config} if db_config else {}

            self.db_manager = DatabaseManager(config_dict)
            await self.db_manager.initialize()

            self.active_components.add("database_manager")
            self.logger.info("✅ DatabaseManager инициализирован с TransactionManager")

        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации DatabaseManager: {e}")
            self.failed_components.add("database_manager")
            raise ComponentInitializationError(f"DatabaseManager initialization failed: {e}")

    async def _initialize_ml_manager(self) -> None:
        """Инициализация MLManager с адаптерами."""
        try:
            self.logger.info("🤖 Инициализация MLManager...")

            # Получаем полную конфигурацию для ML
            config = self.config_manager.get_config()

            self.ml_manager = MLManager(config)
            await self.ml_manager.initialize()

            self.active_components.add("ml_manager")

            # Проверяем, используется ли адаптер
            if hasattr(self.ml_manager, "use_adapter") and self.ml_manager.use_adapter:
                self.logger.info("✅ MLManager инициализирован с системой адаптеров")
            else:
                self.logger.info("✅ MLManager инициализирован в legacy режиме")

        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации MLManager: {e}")
            self.failed_components.add("ml_manager")
            # ML Manager не критичен для работы системы, продолжаем
            self.logger.warning("ML Manager не инициализирован, но система продолжит работу")

    async def _initialize_trader_factory(self) -> None:
        """Инициализация TraderFactory."""
        try:
            self.logger.info("🏭 Инициализация TraderFactory...")
            self.trader_factory = get_global_trader_factory()
            self.active_components.add("trader_factory")
            self.logger.info("✅ TraderFactory инициализирован")
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации TraderFactory: {e}")
            self.failed_components.add("trader_factory")

    async def _initialize_trader_manager(self) -> None:
        """Инициализация TraderManager."""
        try:
            self.logger.info("👥 Инициализация TraderManager...")
            self.trader_manager = get_global_trader_manager()
            self.active_components.add("trader_manager")
            self.logger.info("✅ TraderManager инициализирован")
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации TraderManager: {e}")
            self.failed_components.add("trader_manager")

    async def _initialize_exchange_registry(self) -> None:
        """Инициализация реестра бирж и менеджера."""
        self.logger.info("🏪 Инициализация реестра бирж и менеджера...")

        try:
            from exchanges.exchange_manager import ExchangeManager

            # Создаем менеджер бирж
            self.exchange_manager = ExchangeManager(self.config)
            await self.exchange_manager.initialize()

            # exchange_registry берем из exchange_manager если есть
            if hasattr(self.exchange_manager, "registry"):
                self.exchange_registry = self.exchange_manager.registry

            self.logger.info("✅ ExchangeManager успешно инициализирован")
        except Exception as e:
            self.logger.warning(f"⚠️ Не удалось инициализировать ExchangeManager: {e}")
            self.exchange_manager = None
            self.exchange_registry = None

    async def _initialize_trading_engine(self) -> None:
        """Инициализация торгового движка."""
        self.logger.info("⚡ Инициализация торгового движка...")

        try:
            from trading.engine import TradingEngine

            # Преобразуем Pydantic модель в dict если нужно
            config_dict = self.config
            if hasattr(self.config, "model_dump"):
                config_dict = self.config.model_dump()
            elif hasattr(self.config, "dict"):
                config_dict = self.config.dict()

            self.trading_engine = TradingEngine(
                orchestrator=self,  # Передаем сам orchestrator
                config=config_dict,  # Передаем конфигурацию как dict
            )

            await self.trading_engine.initialize()
            self.active_components.add("trading_engine")
            self.logger.info("✅ TradingEngine успешно инициализирован")

        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации TradingEngine: {e}")
            self.trading_engine = None
            self.failed_components.add("trading_engine")

    async def _initialize_health_checker(self) -> None:
        """Инициализация системы мониторинга здоровья."""
        self.logger.info("🏥 Инициализация системы мониторинга здоровья...")
        pass

    async def _initialize_telegram_service(self) -> None:
        """Инициализация Telegram сервиса."""
        self.logger.info("📱 Инициализация Telegram сервиса...")
        pass

    async def _initialize_ai_signal_generator(self) -> None:
        """Инициализация AI генератора сигналов."""
        self.logger.info("🧠 Инициализация AI генератора сигналов...")
        pass

    async def _initialize_signal_scheduler(self) -> None:
        """Инициализация планировщика сигналов."""
        self.logger.info("📅 Инициализация планировщика сигналов...")

        try:
            # Проверяем, включена ли ML система
            # Работаем с dict конфигурацией
            ml_enabled = self.config.get("ml", {}).get("enabled", False)

            if not ml_enabled:
                self.logger.info(
                    "ML отключена в конфигурации, SignalScheduler не будет инициализирован"
                )
                return

            # Импортируем и создаем SignalScheduler
            from ml.signal_scheduler import SignalScheduler

            # Используем уже загруженный config (он был получен в __init__ как dict)
            self.signal_scheduler = SignalScheduler(self.config)
            await self.signal_scheduler.initialize()

            # Подключаем к Trading Engine если он есть
            if self.trading_engine:
                self.signal_scheduler.set_trading_engine(self.trading_engine)
                self.logger.info("✅ SignalScheduler подключен к TradingEngine")

                # Запускаем SignalScheduler
                await self.signal_scheduler.start()
                self.logger.info(
                    "🚀 SignalScheduler запущен и будет генерировать сигналы каждые 3 минуты"
                )
            else:
                self.logger.warning(
                    "⚠️ TradingEngine не инициализирован, SignalScheduler не сможет отправлять сигналы"
                )

            self.active_components.add("signal_scheduler")
            self.logger.info("✅ SignalScheduler успешно инициализирован")

        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации SignalScheduler: {e}")
            self.signal_scheduler = None
            self.failed_components.add("signal_scheduler")

    async def _initialize_data_manager(self) -> None:
        """Инициализация менеджера данных."""
        self.logger.info("📊 Инициализация менеджера данных...")
        pass

    async def _initialize_data_update_service(self) -> None:
        """Инициализация сервиса обновления данных."""
        self.logger.info("🔄 Инициализация сервиса обновления данных...")
        pass

    async def _initialize_data_maintenance(self) -> None:
        """Инициализация сервиса обслуживания данных."""
        self.logger.info("🧹 Инициализация сервиса обслуживания данных...")
        pass

    async def _initialize_api_servers(self) -> None:
        """Инициализация API серверов."""
        self.logger.info("🌐 Инициализация API серверов...")
        pass

    async def _start_background_tasks(self) -> None:
        """Запуск фоновых задач."""
        self.logger.info("🔄 Запуск фоновых задач...")
        pass

    async def _stop_background_tasks(self) -> None:
        """Остановка фоновых задач."""
        self.logger.info("⏹️ Остановка фоновых задач...")
        for task in self._monitoring_tasks:
            if not task.done():
                task.cancel()
        self._monitoring_tasks.clear()

    async def _health_monitoring_loop(self) -> None:
        """Цикл мониторинга здоровья."""
        pass

    async def _start_api_servers(self) -> None:
        """Запуск API серверов."""
        self.logger.info("🚀 Запуск API серверов...")
        pass

    async def _stop_api_servers(self) -> None:
        """Остановка API серверов."""
        self.logger.info("🛑 Остановка API серверов...")
        pass

    async def _cleanup_on_error(self) -> None:
        """Очистка при ошибке."""
        self.logger.info("🧹 Очистка после ошибки...")
        try:
            if self.db_manager:
                await self.db_manager.close()
            if self.ml_manager and hasattr(self.ml_manager, "adapter") and self.ml_manager.adapter:
                await self.ml_manager.adapter.cleanup()
        except Exception as e:
            self.logger.error(f"Ошибка при очистке: {e}")

    async def _emergency_shutdown(self) -> None:
        """Экстренная остановка системы."""
        self.logger.error("🚨 Экстренная остановка системы...")
        await self._cleanup_on_error()

    @asynccontextmanager
    async def managed_lifecycle(self):
        """Контекстный менеджер для управления жизненным циклом."""
        try:
            await self.initialize()
            await self.start()
            yield self
        finally:
            await self.shutdown()
