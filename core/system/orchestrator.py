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
from typing import Dict, List, Optional, Set

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
from utils.helpers import get_system_resources


@dataclass
class HealthStatus:
    """Статус здоровья системы"""

    is_healthy: bool
    timestamp: datetime
    issues: List[str]
    warnings: List[str]
    system_resources: Dict[str, float]
    active_traders: int
    total_trades: int


class SystemOrchestrator:
    """
    Главный оркестратор системы BOT_Trading v3.0

    Отвечает за:
    - Инициализацию и конфигурацию всех компонентов
    - Управление жизненным циклом трейдеров
    - Мониторинг здоровья системы
    - Координацию между сервисами
    - Graceful shutdown
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or get_global_config_manager()
        self.logger_factory = get_global_logger_factory()
        self.logger = self.logger_factory.get_logger("system_orchestrator")

        # Основные компоненты
        self.trader_manager: Optional[TraderManager] = None
        self.trader_factory: Optional[TraderFactory] = None
        self.health_checker = None  # Будет инициализирован позже
        self.exchange_registry = None  # Для проверки бирж
        self.trading_engine = None  # Торговый движок
        self.telegram_service = None  # Telegram уведомления
        self.ai_signal_generator = None  # AI генератор сигналов
        self.signal_scheduler = None  # ML Signal Scheduler для real-time генерации
        self.data_update_service = None  # Служба автообновления данных

        # TODO: Эти компоненты будут добавлены в следующих этапах
        self.system_monitor = None  # Инициализируем как None
        self.db_manager = (
            None  # Инициализируем как None, будет заполнено позже если нужно
        )
        # self.api_server: Optional[APIServer] = None

        # Статус системы
        self.is_initialized = False
        self.is_running = False
        self.startup_time: Optional[datetime] = None

        # Трекинг компонентов
        self.active_components: Set[str] = set()
        self.failed_components: Set[str] = set()

        # Настройки из конфигурации
        self.system_config = config_manager.get_system_config()
        self.health_check_interval = self.system_config.get("monitoring", {}).get(
            "health_check_interval", 30
        )

        # Задачи мониторинга
        self._monitoring_tasks: List[asyncio.Task] = []

    async def get_status(self) -> Dict:
        """Получение статуса системы"""
        status = {
            "components": {
                "trader_manager": self.trader_manager is not None,
                "trader_factory": self.trader_factory is not None,
                "health_checker": self.health_checker is not None,
                "exchange_registry": self.exchange_registry is not None,
            },
            "exchanges": [],
            "strategies": [],
            "database": {"connected": True},  # TODO: реальная проверка
        }

        # Получаем список бирж если доступен exchange_registry
        if self.exchange_registry:
            try:
                status[
                    "exchanges"
                ] = await self.exchange_registry.get_available_exchanges()
            except Exception:
                pass

        # Получаем список стратегий если доступен trader_manager
        if self.trader_manager:
            try:
                active_traders = await self.trader_manager.get_active_traders()
                for trader in active_traders:
                    if hasattr(trader, "strategy_name"):
                        status["strategies"].append(trader.strategy_name)
            except Exception:
                pass

        return status

    async def stop(self) -> None:
        """Остановка всех компонентов системы"""
        self.logger.info("🛑 Начинаем остановку системы...")

        # Отменяем задачи мониторинга
        for task in self._monitoring_tasks:
            if not task.done():
                task.cancel()

        # Ждем завершения задач
        if self._monitoring_tasks:
            await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)

        # Останавливаем трейдеры
        if self.trader_manager:
            try:
                await self.trader_manager._stop_all_traders()
            except Exception as e:
                self.logger.error(f"Ошибка при остановке трейдеров: {e}")

        self.is_running = False
        self.logger.info("✅ Система остановлена")

    async def initialize(self) -> None:
        """Инициализация всех компонентов системы"""
        try:
            self.logger.info("🚀 Начинаем инициализацию системы BOT_Trading v3.0...")

            # Проверка системных требований
            await self._check_system_requirements()

            # Инициализация фабрики трейдеров
            await self._initialize_trader_factory()

            # Инициализация менеджера трейдеров
            await self._initialize_trader_manager()

            # Инициализация Exchange Registry
            await self._initialize_exchange_registry()

            # Инициализация Trading Engine
            await self._initialize_trading_engine()

            # Инициализация HealthChecker
            await self._initialize_health_checker()

            # Инициализация Telegram сервиса
            await self._initialize_telegram_service()

            # Инициализация AI Signal Generator
            await self._initialize_ai_signal_generator()

            # Инициализация Data Update Service
            await self._initialize_data_update_service()

            # Инициализация Data Maintenance Service (legacy)
            await self._initialize_data_maintenance()

            # Инициализация ML Signal Scheduler
            await self._initialize_signal_scheduler()

            # Инициализация API серверов
            # НЕ инициализируем API серверы если запущены через unified launcher
            # так как API будет запущен отдельным процессом
            unified_mode = os.getenv("UNIFIED_MODE")
            self.logger.info(f"🔍 UNIFIED_MODE = {unified_mode}")
            if unified_mode != "true":
                await self._initialize_api_servers()
            else:
                self.logger.info(
                    "⏭️ API серверы будут запущены отдельным процессом (UNIFIED_MODE=true)"
                )

            # TODO: Эти компоненты будут добавлены в следующих этапах
            # await self._initialize_database()
            # await self._initialize_monitoring()

            # Запуск фоновых задач
            await self._start_background_tasks()

            self.is_initialized = True
            self.startup_time = datetime.now()

            self.logger.info("✅ Система успешно инициализирована")

        except Exception as e:
            self.logger.error(f"❌ Ошибка при инициализации системы: {e}")
            await self._cleanup_on_error()
            raise SystemInitializationError(
                f"Не удалось инициализировать систему: {e}"
            ) from e

    async def start(self) -> None:
        """Запуск всей системы"""
        try:
            if not self.is_initialized:
                raise SystemInitializationError("Система не инициализирована")

            self.logger.info("🎯 Запуск системы BOT_Trading v3.0...")

            # Запуск менеджера трейдеров
            await self.trader_manager.start()
            self.active_components.add("trader_manager")

            # Запуск Trading Engine если инициализирован
            if self.trading_engine:
                await self.trading_engine.start()
                self.logger.info("📈 Trading Engine запущен")
                self.active_components.add("trading_engine")

            # Запуск AI Signal Generator если инициализирован
            if self.ai_signal_generator:
                await self.ai_signal_generator.start()
                self.logger.info("🤖 AI Signal Generator запущен")

            # Запуск ML Signal Scheduler если инициализирован
            if self.signal_scheduler:
                await self.signal_scheduler.start()
                self.logger.info(
                    "🤖 ML Signal Scheduler запущен - генерация сигналов каждую минуту"
                )

            # Запуск Data Update Service
            if self.data_update_service:
                await self.data_update_service.start()
                self.logger.info(
                    "🔄 Data Update Service запущен - автоматическое обновление данных"
                )

            # Запуск Data Maintenance Service если инициализирован (legacy)
            if hasattr(self, "data_maintenance") and self.data_maintenance:
                await self.data_maintenance.start()
                self.logger.info(
                    "🔄 Data Maintenance Service запущен - автоматическое обновление данных"
                )

            # Запуск API серверов
            # НЕ запускаем API серверы если запущены через unified launcher
            if os.getenv("UNIFIED_MODE") != "true":
                await self._start_api_servers()
            else:
                self.logger.info("⏭️ API серверы запускаются отдельным процессом")

            # TODO: Эти компоненты будут добавлены в следующих этапах
            # await self.system_monitor.start()
            # self.active_components.add("system_monitor")

            self.is_running = True
            self.logger.info("🟢 Система запущена и работает")

        except Exception as e:
            self.logger.error(f"❌ Ошибка при запуске системы: {e}")
            await self._emergency_shutdown()
            raise

    async def shutdown(self) -> None:
        """Graceful shutdown всей системы"""
        try:
            self.logger.info("🛑 Начинаем остановку системы...")
            self.is_running = False

            # Остановка фоновых задач
            await self._stop_background_tasks()

            # Остановка трейдеров
            if self.trader_manager:
                await self.trader_manager.stop()
                self.active_components.discard("trader_manager")

            # Остановка Trading Engine
            if self.trading_engine:
                await self.trading_engine.stop()
                self.active_components.discard("trading_engine")

            # Остановка Telegram сервиса
            if self.telegram_service:
                await self.telegram_service.stop()
                self.active_components.discard("telegram_service")

            # Остановка ML Signal Scheduler
            if self.signal_scheduler:
                await self.signal_scheduler.stop()
                self.active_components.discard("signal_scheduler")

            # Остановка Data Update Service
            if self.data_update_service:
                await self.data_update_service.stop()
                self.active_components.discard("data_update_service")

            # Остановка Data Maintenance Service
            if hasattr(self, "data_maintenance") and self.data_maintenance:
                await self.data_maintenance.stop()
                self.active_components.discard("data_maintenance")

            # TODO: Остановка мониторинга будет добавлена позже
            # if self.system_monitor:
            #     await self.system_monitor.stop()
            #     self.active_components.discard("system_monitor")

            # Остановка API серверов
            await self._stop_api_servers()

            # Закрытие соединений с базой данных
            if self.db_manager:
                await self.db_manager.close_all()
                self.active_components.discard("database")

            self.logger.info("✅ Система успешно остановлена")

        except Exception as e:
            self.logger.error(f"❌ Ошибка при остановке системы: {e}")
            raise SystemShutdownError(
                f"Не удалось корректно остановить систему: {e}"
            ) from e

    async def health_check(self) -> HealthStatus:
        """Проверка здоровья всей системы"""
        try:
            issues = []
            warnings = []

            # Проверка компонентов
            if not self.is_running:
                issues.append("Система не запущена")

            if self.failed_components:
                issues.append(
                    f"Сбойные компоненты: {', '.join(self.failed_components)}"
                )

            # Проверка трейдеров
            if self.trader_manager:
                trader_health = await self.trader_manager.get_health_status()
                if trader_health.failed_traders:
                    issues.append(
                        f"Сбойные трейдеры: {', '.join(trader_health.failed_traders)}"
                    )
                if trader_health.warnings:
                    warnings.extend(trader_health.warnings)

            # Проверка системных ресурсов
            resources = get_system_resources()
            limits = self.system_config.get("limits", {})

            if resources["memory_percent"] > limits.get("max_memory_usage_mb", 80):
                warnings.append(
                    f"Высокое использование памяти: {resources['memory_percent']}%"
                )

            if resources["cpu_percent"] > limits.get("max_cpu_usage_percent", 80):
                warnings.append(
                    f"Высокое использование CPU: {resources['cpu_percent']}%"
                )

            # Проверка базы данных
            if self.db_manager:
                db_health = await self.db_manager.health_check()
                if not db_health.is_healthy:
                    issues.append("Проблемы с базой данных")

            # Статистика трейдеров
            active_traders = 0
            total_trades = 0

            if self.trader_manager:
                stats = await self.trader_manager.get_statistics()
                active_traders = stats.active_traders
                total_trades = stats.total_trades

            return HealthStatus(
                is_healthy=len(issues) == 0,
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

    async def get_system_status(self) -> Dict:
        """Получение полного статуса системы"""
        uptime = None
        if self.startup_time:
            uptime = (datetime.now() - self.startup_time).total_seconds()

        health = await self.health_check()

        return {
            "system": {
                "version": "3.0.0",
                "is_running": self.is_running,
                "uptime_seconds": uptime,
                "startup_time": self.startup_time.isoformat()
                if self.startup_time
                else None,
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
            },
            "components": {
                "active": list(self.active_components),
                "failed": list(self.failed_components),
            },
        }

    # Приватные методы инициализации

    async def _check_system_requirements(self) -> None:
        """Проверка системных требований"""
        resources = get_system_resources()

        # Проверка памяти
        if resources["memory_available_mb"] < 512:
            raise SystemInitializationError(
                "Недостаточно доступной памяти (требуется минимум 512MB)"
            )

        # Проверка места на диске
        if resources["disk_free_gb"] < 1:
            raise SystemInitializationError(
                "Недостаточно места на диске (требуется минимум 1GB)"
            )

        self.logger.info("✅ Системные требования проверены")

    async def _initialize_database(self) -> None:
        """Инициализация подключения к базе данных"""
        try:
            # TODO: Имплементация ConnectionManager будет добавлена позже
            # self.db_manager = ConnectionManager(
            #     self.config_manager.get_database_config()
            # )
            # await self.db_manager.initialize()
            # self.active_components.add("database")
            # self.logger.info("✅ База данных инициализирована")
            self.logger.info("⏭️ Инициализация базы данных отложена")
        except Exception as e:
            self.failed_components.add("database")
            raise SystemInitializationError(
                f"Не удалось инициализировать базу данных: {e}"
            ) from e

    async def _initialize_monitoring(self) -> None:
        """Инициализация системы мониторинга"""
        try:
            # TODO: Имплементация SystemMonitor будет добавлена позже
            # self.system_monitor = SystemMonitor(self.config_manager)
            # await self.system_monitor.initialize()
            # self.active_components.add("system_monitor")
            # self.logger.info("✅ Система мониторинга инициализирована")
            self.logger.info("⏭️ Инициализация мониторинга отложена")
        except Exception as e:
            self.failed_components.add("system_monitor")
            self.logger.warning(f"⚠️ Не удалось инициализировать мониторинг: {e}")

    async def _initialize_trader_factory(self) -> None:
        """Инициализация фабрики трейдеров"""
        try:
            self.trader_factory = get_global_trader_factory()
            self.active_components.add("trader_factory")
            self.logger.info("✅ Фабрика трейдеров инициализирована")
        except Exception as e:
            self.failed_components.add("trader_factory")
            raise ComponentInitializationError("trader_factory", str(e)) from e

    async def _initialize_trader_manager(self) -> None:
        """Инициализация менеджера трейдеров"""
        try:
            self.trader_manager = get_global_trader_manager()
            await self.trader_manager.initialize()
            self.active_components.add("trader_manager")
            self.logger.info("✅ Менеджер трейдеров инициализирован")
        except Exception as e:
            self.failed_components.add("trader_manager")
            raise ComponentInitializationError("trader_manager", str(e)) from e

    async def _initialize_exchange_registry(self) -> None:
        """Инициализация менеджера бирж"""
        try:
            from exchanges.exchange_manager import ExchangeManager

            # Получаем конфигурацию системы
            system_config = self.config_manager.get_config()

            # Создаем ExchangeManager с правильной конфигурацией
            self.exchange_registry = ExchangeManager(system_config)
            await self.exchange_registry.initialize()
            self.active_components.add("exchange_registry")
            self.logger.info("✅ Exchange Manager инициализирован")
        except Exception as e:
            self.failed_components.add("exchange_registry")
            self.logger.warning(f"⚠️ Exchange Manager не инициализирован: {e}")

    async def _initialize_trading_engine(self) -> None:
        """Инициализация торгового движка"""
        self.logger.info("🔧 Начинаем инициализацию Trading Engine...")
        try:
            # Проверяем зависимости
            if not self.exchange_registry:
                self.logger.warning("⚠️ Trading Engine требует Exchange Registry")
                self.logger.info(
                    f"   Exchange Registry статус: {self.exchange_registry}"
                )
                self.logger.info(f"   Active components: {self.active_components}")
                return

            from trading.engine import TradingEngine

            self.logger.info("📦 Импортирован модуль TradingEngine")

            # Передаем config вместо несуществующих параметров
            config = self.config_manager.get_config()
            self.logger.info("⚙️ Создаем экземпляр TradingEngine...")

            self.trading_engine = TradingEngine(orchestrator=self, config=config)
            self.logger.info("🔄 Инициализируем TradingEngine...")

            await self.trading_engine.initialize()
            self.active_components.add("trading_engine")
            self.logger.info("✅ Trading Engine инициализирован")
        except Exception as e:
            self.failed_components.add("trading_engine")
            self.logger.error(f"❌ Trading Engine не инициализирован: {e}")
            import traceback

            self.logger.error(traceback.format_exc())

    async def _initialize_health_checker(self) -> None:
        """Инициализация компонента проверки здоровья системы"""
        try:
            from core.system.health_checker import HealthChecker

            self.health_checker = HealthChecker(self.config_manager)

            # Устанавливаем компоненты для проверки
            self.health_checker.set_components(
                exchange_registry=self.exchange_registry,
                trader_manager=self.trader_manager,
                strategy_manager=None,  # Будет добавлен позже
            )

            self.active_components.add("health_checker")
            self.logger.info("✅ Health Checker инициализирован")
        except Exception as e:
            self.failed_components.add("health_checker")
            self.logger.warning(f"⚠️ Health Checker не инициализирован: {e}")
            # Не прерываем инициализацию, так как это не критичный компонент

    async def _initialize_telegram_service(self) -> None:
        """Инициализация Telegram сервиса для уведомлений"""
        try:
            telegram_config = (
                self.config_manager.get_system_config()
                .get("notifications", {})
                .get("telegram", {})
            )

            if not telegram_config.get("enabled", False):
                self.logger.info("⏭️ Telegram сервис отключен в конфигурации")
                return

            from notifications.telegram import TelegramNotificationService

            self.telegram_service = TelegramNotificationService(self.config_manager)

            # Устанавливаем ссылки на компоненты
            self.telegram_service.set_orchestrator(self)
            self.telegram_service.set_trader_manager(self.trader_manager)

            # Инициализируем сервис
            await self.telegram_service.initialize()

            self.active_components.add("telegram_service")
            self.logger.info("✅ Telegram сервис инициализирован")

        except Exception as e:
            self.failed_components.add("telegram_service")
            self.logger.warning(f"⚠️ Telegram сервис не инициализирован: {e}")
            # Не прерываем инициализацию, так как это не критичный компонент

    async def _initialize_ai_signal_generator(self) -> None:
        """Инициализация AI генератора сигналов"""
        try:
            # Проверяем, есть ли включенные multi-crypto трейдеры
            full_config = self.config_manager.get_config()
            traders = full_config.get("traders", [])

            multi_crypto_enabled = any(
                trader.get("id") == "multi_crypto_10" and trader.get("enabled")
                for trader in traders
            )

            if not multi_crypto_enabled:
                self.logger.info(
                    "⏭️ AI Signal Generator отключен (нет активных multi-crypto трейдеров)"
                )
                return

            # Попробуем сначала загрузить полную версию с ML
            try:
                from trading.signals.ai_signal_generator import AISignalGenerator

                self.ai_signal_generator = AISignalGenerator(self.config_manager)
                await self.ai_signal_generator.initialize()
                self.logger.info("🤖 AI Signal Generator с ML инициализирован")
            except Exception as ml_error:
                # Если не получилось - используем упрощенную версию
                self.logger.warning(f"⚠️ ML версия недоступна: {ml_error}")
                from trading.signals.simple_ai_signal_generator import (
                    SimpleAISignalGenerator,
                )

                self.ai_signal_generator = SimpleAISignalGenerator(self.config_manager)
                await self.ai_signal_generator.initialize()
                self.logger.info("🤖 Simple AI Signal Generator инициализирован")

            self.active_components.add("ai_signal_generator")
            self.logger.info("✅ AI Signal Generator инициализирован")

            # Связываем AI Signal Generator с Trading Engine
            if self.trading_engine and hasattr(
                self.ai_signal_generator, "set_trading_engine"
            ):
                self.ai_signal_generator.set_trading_engine(self.trading_engine)
                self.logger.info("🔗 AI Signal Generator связан с Trading Engine")

        except Exception as e:
            self.failed_components.add("ai_signal_generator")
            self.logger.warning(f"⚠️ AI Signal Generator не инициализирован: {e}")
            # Не прерываем инициализацию, так как это не критичный компонент

    async def _initialize_signal_scheduler(self) -> None:
        """Инициализация ML Signal Scheduler для real-time генерации сигналов"""
        try:
            # Проверяем ML конфигурацию
            ml_config = self.config_manager.get_ml_config()

            # Проверяем включен ли ML
            if not ml_config.get("model", {}).get("enabled", True):
                self.logger.info("⏭️ ML Signal Scheduler отключен в конфигурации")
                return

            # Проверяем переменную окружения ML_DISABLED
            if os.getenv("ML_DISABLED", "").lower() == "true":
                self.logger.info("⏭️ ML Signal Scheduler отключен через ML_DISABLED")
                return

            # Проверяем есть ли модель - сначала пробуем в стандартном месте
            from pathlib import Path

            base_dir = Path(__file__).parent.parent.parent  # Корень проекта
            default_model_path = (
                base_dir / "models/saved/best_model_20250728_215703.pth"
            )

            model_path = ml_config.get("model", {}).get("model_path") or ml_config.get(
                "model", {}
            ).get("path")

            # Если путь не указан в конфигурации, используем стандартный
            if not model_path:
                model_path = default_model_path
            else:
                # Если путь относительный, делаем его относительно проекта
                if not Path(model_path).is_absolute():
                    model_path = base_dir / model_path

            # Проверяем физическое наличие файла модели
            if not Path(model_path).exists():
                self.logger.warning(f"⚠️ ML модель не найдена: {model_path}")
                return

            from ml.signal_scheduler import SignalScheduler

            self.signal_scheduler = SignalScheduler(self.config_manager)
            await self.signal_scheduler.initialize()

            self.active_components.add("signal_scheduler")
            self.logger.info("✅ ML Signal Scheduler инициализирован")
            self.logger.info(
                f"📊 Будет генерировать сигналы для {len(ml_config.get('data', {}).get('symbols', []))} символов"
            )

            # Связываем Signal Scheduler с Trading Engine
            if self.trading_engine and hasattr(
                self.signal_scheduler, "set_trading_engine"
            ):
                self.signal_scheduler.set_trading_engine(self.trading_engine)
                self.logger.info("🔗 Signal Scheduler связан с Trading Engine")

        except Exception as e:
            self.failed_components.add("signal_scheduler")
            self.logger.warning(f"⚠️ ML Signal Scheduler не инициализирован: {e}")
            # Не прерываем инициализацию, так как это не критичный компонент

    async def _initialize_data_update_service(self) -> None:
        """Инициализация службы автообновления данных"""
        try:
            from data.data_update_service import DataUpdateService

            self.data_update_service = DataUpdateService(self.config_manager)

            self.active_components.add("data_update_service")
            self.logger.info("✅ Data Update Service инициализирован")

        except Exception as e:
            self.failed_components.add("data_update_service")
            self.logger.warning(f"⚠️ Data Update Service не инициализирован: {e}")
            # Не прерываем инициализацию, продолжаем с legacy service

    async def _initialize_data_maintenance(self) -> None:
        """Инициализация сервиса поддержания данных"""
        try:
            from data.maintenance_service import DataMaintenanceService

            self.data_maintenance = DataMaintenanceService(self.config_manager)
            await self.data_maintenance.initialize()

            self.active_components.add("data_maintenance")
            self.logger.info("✅ Data Maintenance Service инициализирован")

        except Exception as e:
            self.failed_components.add("data_maintenance")
            self.logger.warning(f"⚠️ Data Maintenance Service не инициализирован: {e}")
            # Не прерываем инициализацию

    async def _initialize_api_servers(self) -> None:
        """Инициализация API серверов"""
        try:
            # Проверяем конфигурацию API
            api_config = self.system_config.get("api", {})
            rest_config = api_config.get("rest", {})

            if not rest_config.get("enabled", True):
                self.logger.info("⏭️ Web API отключен в конфигурации")
                return

            # Создаем задачу для запуска API сервера
            self.api_task = None
            self.api_host = rest_config.get("host", "0.0.0.0")
            self.api_port = rest_config.get("port", 8080)

            self.active_components.add("api_server")
            self.logger.info(
                f"✅ Web API сервер будет запущен на http://{self.api_host}:{self.api_port}"
            )

        except Exception as e:
            self.failed_components.add("api_server")
            self.logger.warning(f"⚠️ Web API сервер не инициализирован: {e}")
            # Не прерываем инициализацию

    async def _start_background_tasks(self) -> None:
        """Запуск фоновых задач"""
        # Задача мониторинга здоровья
        health_task = asyncio.create_task(self._health_monitoring_loop())
        self._monitoring_tasks.append(health_task)

        self.logger.info("✅ Фоновые задачи запущены")

    async def _stop_background_tasks(self) -> None:
        """Остановка фоновых задач"""
        for task in self._monitoring_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._monitoring_tasks.clear()
        self.logger.info("✅ Фоновые задачи остановлены")

    async def _health_monitoring_loop(self) -> None:
        """Цикл мониторинга здоровья системы"""
        while self.is_running:
            try:
                health = await self.health_check()

                if not health.is_healthy:
                    self.logger.warning(f"⚠️ Проблемы в системе: {health.issues}")

                if health.warnings:
                    self.logger.warning(f"⚠️ Предупреждения: {health.warnings}")

                await asyncio.sleep(self.health_check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"❌ Ошибка в мониторинге здоровья: {e}")
                await asyncio.sleep(self.health_check_interval)

    async def _start_api_servers(self) -> None:
        """Запуск API серверов"""
        try:
            if "api_server" in self.active_components:
                # Запускаем сервер в отдельной задаче
                self.api_task = asyncio.create_task(self._run_api_server())
                self.logger.info("🌐 Запускаем Web API сервер...")
        except Exception as e:
            self.logger.error(f"Ошибка запуска API сервера: {e}")

    async def _run_api_server(self) -> None:
        """Запуск Web API сервера"""
        try:
            from web.api.main import start_web_server

            self.logger.info(
                f"🌐 Web API сервер запускается на http://{self.api_host}:{self.api_port}"
            )
            await start_web_server(host=self.api_host, port=self.api_port)

        except Exception as e:
            self.logger.error(f"❌ Ошибка в Web API сервере: {e}")

    async def _stop_api_servers(self) -> None:
        """Остановка API серверов"""
        # Реализация будет добавлена позже
        pass

    async def _cleanup_on_error(self) -> None:
        """Очистка при ошибке инициализации"""
        try:
            if self.db_manager:
                await self.db_manager.close_all()
            if self.system_monitor:
                await self.system_monitor.stop()
        except Exception as e:
            self.logger.error(f"❌ Ошибка при очистке: {e}")

    async def _emergency_shutdown(self) -> None:
        """Экстренная остановка системы"""
        self.logger.error("🚨 Экстренная остановка системы")
        self.is_running = False

        # Принудительная остановка всех компонентов
        for task in self._monitoring_tasks:
            task.cancel()

        if self.trader_manager:
            await self.trader_manager.emergency_stop()

        if self.db_manager:
            await self.db_manager.close_all()

    @asynccontextmanager
    async def managed_lifecycle(self):
        """Context manager для управления жизненным циклом"""
        try:
            await self.initialize()
            await self.start()
            yield self
        finally:
            await self.shutdown()
