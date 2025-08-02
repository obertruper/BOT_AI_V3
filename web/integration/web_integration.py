"""
Web Integration Layer для BOT_Trading v3.0

Главный класс интеграции веб-интерфейса с core системой бота.
Обеспечивает прямое подключение веб-сервера к компонентам торговой системы.

Основные возможности:
- Инициализация и запуск веб-сервера
- Интеграция с SystemOrchestrator
- Управление зависимостями
- Event-driven архитектура
- Lifecycle management
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import uvicorn

from core.logging.logger_factory import get_global_logger_factory
from core.system.orchestrator import SystemOrchestrator

from .data_adapters import DataAdapters
from .dependencies import cleanup_dependencies, initialize_dependencies
from .event_bridge import EventBridge

logger_factory = get_global_logger_factory()
logger = logger_factory.get_logger("web_integration")


class WebIntegration:
    """
    Главный класс интеграции веб-интерфейса с BOT_Trading v3.0

    Обеспечивает связь между веб-сервером и основными компонентами системы:
    - Прямой доступ к TraderManager, ExchangeFactory, ConfigManager
    - Real-time события через EventBridge
    - Преобразование данных через DataAdapters
    - Lifecycle management веб-сервера
    """

    def __init__(self, orchestrator: SystemOrchestrator):
        """
        Инициализация веб-интеграции

        Args:
            orchestrator: Главный оркестратор системы BOT_Trading v3.0
        """
        self.orchestrator = orchestrator
        self.web_server: Optional[uvicorn.Server] = None
        self.event_bridge: Optional[EventBridge] = None
        self.data_adapters: Optional[DataAdapters] = None
        self.is_running = False

        # Конфигурация веб-сервера
        self.host = "0.0.0.0"
        self.port = 8080
        self.reload = False

        logger.info("WebIntegration инициализирован с orchestrator")

    async def initialize(self):
        """Инициализация всех компонентов веб-интеграции"""
        if self.is_running:
            logger.warning("WebIntegration уже инициализирован")
            return

        logger.info("Инициализация веб-интеграции...")

        try:
            # Инициализируем зависимости
            await initialize_dependencies(self.orchestrator)

            # Создаем event bridge для real-time событий
            self.event_bridge = EventBridge(
                trader_manager=self.orchestrator.trader_manager,
                exchange_factory=self.orchestrator.exchange_factory,
                config_manager=self.orchestrator.config_manager,
            )

            # Создаем адаптеры данных
            self.data_adapters = DataAdapters()

            # Получаем конфигурацию веб-сервера
            await self._load_web_config()

            logger.info("Веб-интеграция успешно инициализирована")

        except Exception as e:
            logger.error(f"Ошибка инициализации веб-интеграции: {e}")
            raise

    async def _load_web_config(self):
        """Загрузка конфигурации веб-сервера"""
        try:
            config = self.orchestrator.config_manager.get_config()

            web_config = config.get("web_interface", {})

            self.host = web_config.get("host", self.host)
            self.port = web_config.get("port", self.port)
            self.reload = web_config.get("reload", self.reload)

            logger.info(f"Загружена конфигурация веб-сервера: {self.host}:{self.port}")

        except Exception as e:
            logger.warning(
                f"Не удалось загрузить веб-конфигурацию, используем значения по умолчанию: {e}"
            )

    async def start_web_server(
        self, host: Optional[str] = None, port: Optional[int] = None
    ):
        """
        Запуск веб-сервера

        Args:
            host: Хост для привязки (опционально)
            port: Порт для прослушивания (опционально)
        """
        if self.is_running:
            logger.warning("Веб-сервер уже запущен")
            return

        # Инициализируем если не сделано ранее
        if not self.event_bridge:
            await self.initialize()

        # Используем переданные параметры или значения по умолчанию
        actual_host = host or self.host
        actual_port = port or self.port

        logger.info(f"Запуск веб-сервера на {actual_host}:{actual_port}")

        try:
            # Импортируем FastAPI приложение
            from web.api.main import app, initialize_web_api

            # Инициализируем FastAPI с компонентами системы
            initialize_web_api(
                orchestrator=self.orchestrator,
                trader_manager=self.orchestrator.trader_manager,
                exchange_factory=self.orchestrator.exchange_factory,
                config_manager=self.orchestrator.config_manager,
            )

            # Подключаем endpoints роутеры
            await self._setup_api_routes(app)

            # Настраиваем event bridge
            if self.event_bridge:
                await self.event_bridge.initialize()

            # Конфигурация uvicorn
            config = uvicorn.Config(
                app=app,
                host=actual_host,
                port=actual_port,
                log_level="info",
                access_log=True,
                reload=self.reload,
                loop="asyncio",
            )

            # Создаем и запускаем сервер
            self.web_server = uvicorn.Server(config)
            self.is_running = True

            logger.info(
                f"Веб-сервер готов к запуску на http://{actual_host}:{actual_port}"
            )

            # Запускаем сервер (блокирующий вызов)
            await self.web_server.serve()

        except Exception as e:
            logger.error(f"Ошибка запуска веб-сервера: {e}")
            self.is_running = False
            raise

    async def _setup_api_routes(self, app):
        """Настройка API маршрутов"""
        try:
            # Импортируем роутеры
            from web.api.endpoints.auth import router as auth_router
            from web.api.endpoints.exchanges import router as exchanges_router
            from web.api.endpoints.monitoring import router as monitoring_router
            from web.api.endpoints.strategies import router as strategies_router
            from web.api.endpoints.traders import router as traders_router

            # Подключаем роутеры
            app.include_router(traders_router)
            app.include_router(monitoring_router)
            app.include_router(exchanges_router)
            app.include_router(strategies_router)
            app.include_router(auth_router)

            logger.info("API роутеры успешно подключены")

        except Exception as e:
            logger.error(f"Ошибка настройки API маршрутов: {e}")
            raise

    async def stop_web_server(self):
        """Остановка веб-сервера"""
        if not self.is_running:
            logger.warning("Веб-сервер не запущен")
            return

        logger.info("Остановка веб-сервера...")

        try:
            # Останавливаем event bridge
            if self.event_bridge:
                await self.event_bridge.cleanup()

            # Останавливаем сервер
            if self.web_server:
                self.web_server.should_exit = True
                await self.web_server.shutdown()

            # Очищаем зависимости
            await cleanup_dependencies()

            self.is_running = False
            logger.info("Веб-сервер успешно остановлен")

        except Exception as e:
            logger.error(f"Ошибка остановки веб-сервера: {e}")
            raise

    async def restart_web_server(self):
        """Перезапуск веб-сервера"""
        logger.info("Перезапуск веб-сервера...")

        await self.stop_web_server()
        await asyncio.sleep(1)  # Небольшая пауза
        await self.start_web_server()

    # =================== PROPERTY ACCESSORS ===================

    def get_trader_manager(self):
        """Получить trader_manager"""
        return self.orchestrator.trader_manager

    def get_exchange_factory(self):
        """Получить exchange_factory"""
        return self.orchestrator.exchange_factory

    def get_config_manager(self):
        """Получить config_manager"""
        return self.orchestrator.config_manager

    def get_health_checker(self):
        """Получить health_checker"""
        return self.orchestrator.health_checker

    # =================== STATUS METHODS ===================

    def is_web_server_running(self) -> bool:
        """Проверить запущен ли веб-сервер"""
        return self.is_running

    def get_web_server_info(self) -> Dict[str, Any]:
        """Получить информацию о веб-сервере"""
        return {
            "is_running": self.is_running,
            "host": self.host,
            "port": self.port,
            "reload": self.reload,
            "has_event_bridge": self.event_bridge is not None,
            "has_data_adapters": self.data_adapters is not None,
            "url": f"http://{self.host}:{self.port}" if self.is_running else None,
        }

    def get_integration_status(self) -> Dict[str, Any]:
        """Получить статус интеграции"""
        return {
            "web_integration": {
                "initialized": self.event_bridge is not None,
                "running": self.is_running,
                "server_info": self.get_web_server_info(),
            },
            "orchestrator": {
                "available": self.orchestrator is not None,
                "trader_manager": (
                    self.orchestrator.trader_manager is not None
                    if self.orchestrator
                    else False
                ),
                "exchange_factory": (
                    self.orchestrator.exchange_factory is not None
                    if self.orchestrator
                    else False
                ),
                "config_manager": (
                    self.orchestrator.config_manager is not None
                    if self.orchestrator
                    else False
                ),
            },
            "event_bridge": {
                "initialized": self.event_bridge is not None,
                "active": self.event_bridge.is_active() if self.event_bridge else False,
            },
        }


# =================== CONTEXT MANAGER ===================


@asynccontextmanager
async def web_integration_context(
    orchestrator: SystemOrchestrator, host: str = "0.0.0.0", port: int = 8080
):
    """
    Контекстный менеджер для веб-интеграции

    Использование:
    async with web_integration_context(orchestrator, host="0.0.0.0", port=8080) as web_integration:
        # Веб-сервер запущен и готов к работе
        await web_integration.some_operation()
    """
    web_integration = WebIntegration(orchestrator)

    try:
        await web_integration.initialize()
        # Запуск веб-сервера в отдельной задаче
        server_task = asyncio.create_task(web_integration.start_web_server(host, port))

        # Даем время серверу запуститься
        await asyncio.sleep(1)

        yield web_integration

    finally:
        await web_integration.stop_web_server()

        # Отменяем задачу сервера если она еще выполняется
        if "server_task" in locals() and not server_task.done():
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass


# =================== UTILITY FUNCTIONS ===================


async def create_web_integration(orchestrator: SystemOrchestrator) -> WebIntegration:
    """
    Фабричная функция для создания WebIntegration

    Args:
        orchestrator: Системный оркестратор

    Returns:
        Готовый к использованию экземпляр WebIntegration
    """
    web_integration = WebIntegration(orchestrator)
    await web_integration.initialize()
    return web_integration


def check_web_integration_requirements(
    orchestrator: SystemOrchestrator,
) -> Dict[str, bool]:
    """
    Проверка требований для веб-интеграции

    Args:
        orchestrator: Системный оркестратор

    Returns:
        Словарь с результатами проверки
    """
    requirements = {
        "orchestrator_available": orchestrator is not None,
        "trader_manager_available": False,
        "exchange_factory_available": False,
        "config_manager_available": False,
        "health_checker_available": False,
    }

    if orchestrator:
        requirements.update(
            {
                "trader_manager_available": hasattr(orchestrator, "trader_manager")
                and orchestrator.trader_manager is not None,
                "exchange_factory_available": hasattr(orchestrator, "exchange_factory")
                and orchestrator.exchange_factory is not None,
                "config_manager_available": hasattr(orchestrator, "config_manager")
                and orchestrator.config_manager is not None,
                "health_checker_available": hasattr(orchestrator, "health_checker")
                and orchestrator.health_checker is not None,
            }
        )

    requirements["all_requirements_met"] = all(requirements.values())

    return requirements
