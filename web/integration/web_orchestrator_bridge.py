"""
Мост между веб-интерфейсом и core системой BOT_Trading v3.0

Этот модуль обеспечивает интеграцию FastAPI веб-сервера с главным оркестратором
торговой системы, предоставляя унифицированный доступ к данным и функциям.
"""

from datetime import datetime
from typing import Any

from core.logging.logger_factory import get_global_logger_factory

from .data_adapters import DataAdapters
from .event_bridge import EventBridge, EventType
from .mock_services import MockSessionManager, MockStatsService, MockUserManager


class WebOrchestratorBridge:
    """
    Мост между веб-интерфейсом и core системой оркестратора

    Обеспечивает:
    - Доступ к данным трейдеров, позиций, ордеров
    - Управление состоянием системы
    - Real-time обновления через WebSocket
    - Адаптацию данных между форматами
    """

    def __init__(self, orchestrator=None):
        """
        Инициализация моста

        Args:
            orchestrator: Экземпляр SystemOrchestrator или None для mock режима
        """
        # Логирование
        logger_factory = get_global_logger_factory()
        self.logger = logger_factory.get_logger("web_bridge")

        # Core компоненты
        self.orchestrator = orchestrator
        self.trader_manager = (
            getattr(orchestrator, "trader_manager", None) if orchestrator else None
        )
        self.exchange_factory = (
            getattr(orchestrator, "exchange_factory", None) if orchestrator else None
        )
        self.config_manager = (
            getattr(orchestrator, "config_manager", None) if orchestrator else None
        )

        # Веб компоненты
        self.event_bridge = EventBridge()
        self.data_adapter = DataAdapters()

        # Mock сервисы для разработки
        self.use_mock = orchestrator is None
        if self.use_mock:
            self.logger.warning("WebOrchestratorBridge работает в mock режиме")
            self._init_mock_services()

        # Флаг инициализации
        self._initialized = False

    def _init_mock_services(self):
        """Инициализация mock сервисов для разработки"""
        self.mock_user_manager = MockUserManager()
        self.mock_session_manager = MockSessionManager()
        self.mock_stats_service = MockStatsService()

    async def initialize(self):
        """Асинхронная инициализация моста"""
        if self._initialized:
            return

        try:
            # Инициализация event bridge
            await self.event_bridge.initialize()

            # Подписка на события core системы (если доступна)
            if not self.use_mock and self.orchestrator:
                await self._setup_core_event_listeners()

            self._initialized = True
            self.logger.info("WebOrchestratorBridge успешно инициализирован")

        except Exception as e:
            self.logger.error(f"Ошибка инициализации WebOrchestratorBridge: {e}")
            raise

    async def _setup_core_event_listeners(self):
        """Настройка слушателей событий от core системы"""
        # TODO: Подключить реальные события от orchestrator
        pass

    # =================== TRADERS ===================

    async def get_traders(self) -> list[dict[str, Any]]:
        """Получение списка всех трейдеров"""
        try:
            if self.use_mock:
                # Mock данные для разработки
                return [
                    {
                        "id": "trader_1",
                        "name": "Main Trader",
                        "status": "active",
                        "exchange": "bybit",
                        "symbol": "BTCUSDT",
                        "balance": 1000.0,
                        "equity": 1050.0,
                        "pnl": 50.0,
                        "pnl_percentage": 5.0,
                        "strategy": "ml_strategy",
                        "created_at": "2025-01-01T00:00:00Z",
                        "last_activity": datetime.now().isoformat(),
                        "config": {
                            "max_position_size": 100.0,
                            "leverage": 10.0,
                            "risk_percentage": 2.0,
                        },
                    },
                    {
                        "id": "trader_2",
                        "name": "Conservative Trader",
                        "status": "paused",
                        "exchange": "bybit",
                        "symbol": "ETHUSDT",
                        "balance": 500.0,
                        "equity": 480.0,
                        "pnl": -20.0,
                        "pnl_percentage": -4.0,
                        "strategy": "trend_following",
                        "created_at": "2025-01-02T00:00:00Z",
                        "last_activity": datetime.now().isoformat(),
                        "config": {
                            "max_position_size": 50.0,
                            "leverage": 5.0,
                            "risk_percentage": 1.0,
                        },
                    },
                ]

            # Реальная интеграция с trader_manager
            if self.trader_manager:
                traders = self.trader_manager.get_all_traders()
                return [self.data_adapter.trader_to_response(trader) for trader in traders.values()]

            return []

        except Exception as e:
            self.logger.error(f"Ошибка получения трейдеров: {e}")
            raise

    async def get_trader(self, trader_id: str) -> dict[str, Any] | None:
        """Получение данных конкретного трейдера"""
        try:
            if self.use_mock:
                traders = await self.get_traders()
                return next((t for t in traders if t["id"] == trader_id), None)

            if self.trader_manager:
                trader = self.trader_manager.get_trader(trader_id)
                return self.data_adapter.trader_to_response(trader) if trader else None

            return None

        except Exception as e:
            self.logger.error(f"Ошибка получения трейдера {trader_id}: {e}")
            raise

    async def start_trader(self, trader_id: str) -> bool:
        """Запуск трейдера"""
        try:
            if self.use_mock:
                await self.event_bridge.emit_event(
                    EventType.TRADER_STATUS_CHANGED,
                    {
                        "trader_id": trader_id,
                        "status": "active",
                        "message": "Трейдер запущен",
                    },
                )
                return True

            if self.trader_manager:
                result = await self.trader_manager.start_trader(trader_id)
                if result:
                    await self.event_bridge.emit_event(
                        EventType.TRADER_STATUS_CHANGED,
                        {"trader_id": trader_id, "status": "active"},
                    )
                return result

            return False

        except Exception as e:
            self.logger.error(f"Ошибка запуска трейдера {trader_id}: {e}")
            raise

    async def stop_trader(self, trader_id: str) -> bool:
        """Остановка трейдера"""
        try:
            if self.use_mock:
                await self.event_bridge.emit_event(
                    EventType.TRADER_STATUS_CHANGED,
                    {
                        "trader_id": trader_id,
                        "status": "stopped",
                        "message": "Трейдер остановлен",
                    },
                )
                return True

            if self.trader_manager:
                result = await self.trader_manager.stop_trader(trader_id)
                if result:
                    await self.event_bridge.emit_event(
                        EventType.TRADER_STATUS_CHANGED,
                        {"trader_id": trader_id, "status": "stopped"},
                    )
                return result

            return False

        except Exception as e:
            self.logger.error(f"Ошибка остановки трейдера {trader_id}: {e}")
            raise

    # =================== POSITIONS ===================

    async def get_positions(self, trader_id: Union[str, None] = None) -> list[dict[str, Any]]:
        """Получение списка позиций"""
        try:
            if self.use_mock:
                mock_positions = [
                    {
                        "id": "pos_1",
                        "trader_id": "trader_1",
                        "symbol": "BTCUSDT",
                        "side": "long",
                        "size": 0.5,
                        "entry_price": 45000.0,
                        "current_price": 46000.0,
                        "unrealized_pnl": 500.0,
                        "realized_pnl": 0.0,
                        "leverage": 10.0,
                        "margin": 2250.0,
                        "stop_loss": 44000.0,
                        "take_profit": 47000.0,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                    }
                ]

                if trader_id:
                    return [p for p in mock_positions if p["trader_id"] == trader_id]
                return mock_positions

            # Реальная интеграция через trader_manager или position_manager
            # TODO: Реализовать при готовности core компонентов
            return []

        except Exception as e:
            self.logger.error(f"Ошибка получения позиций: {e}")
            raise

    # =================== SYSTEM STATUS ===================

    async def get_system_status(self) -> dict[str, Any]:
        """Получение статуса системы"""
        try:
            if self.use_mock:
                return {
                    "status": "running",
                    "uptime": 3600,  # 1 час
                    "traders_count": 2,
                    "active_positions": 1,
                    "total_pnl": 50.0,
                    "system_metrics": {
                        "memory_usage": 65.5,
                        "cpu_usage": 15.2,
                        "open_connections": 5,
                        "api_calls_per_minute": 120,
                    },
                }

            if self.orchestrator:
                # TODO: Получить реальные метрики от orchestrator
                pass

            return {"status": "unknown"}

        except Exception as e:
            self.logger.error(f"Ошибка получения статуса системы: {e}")
            raise

    # =================== EVENTS ===================

    async def subscribe_to_events(self, event_types: list[str], callback):
        """Подписка на события системы"""
        for event_type in event_types:
            await self.event_bridge.subscribe(EventType(event_type), callback)

    async def emit_system_event(self, event_type: str, data: dict[str, Any]):
        """Отправка системного события"""
        await self.event_bridge.emit_event(EventType(event_type), data)

    # =================== LIFECYCLE ===================

    async def shutdown(self):
        """Корректное завершение работы моста"""
        try:
            if self.event_bridge:
                await self.event_bridge.shutdown()

            self._initialized = False
            self.logger.info("WebOrchestratorBridge завершен")

        except Exception as e:
            self.logger.error(f"Ошибка при завершении WebOrchestratorBridge: {e}")


# Глобальный экземпляр моста
_bridge_instance: Union[WebOrchestratorBridge, None] = None


def get_web_orchestrator_bridge() -> WebOrchestratorBridge:
    """Получение глобального экземпляра моста"""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = WebOrchestratorBridge()
    return _bridge_instance


async def initialize_web_bridge(orchestrator=None) -> WebOrchestratorBridge:
    """
    Инициализация веб-моста с оркестратором

    Args:
        orchestrator: Экземпляр SystemOrchestrator или None для mock режима
    """
    global _bridge_instance
    _bridge_instance = WebOrchestratorBridge(orchestrator)
    await _bridge_instance.initialize()
    return _bridge_instance
