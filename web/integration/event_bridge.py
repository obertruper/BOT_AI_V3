"""
Event Bridge для BOT_Trading v3.0

Мост событий между основной системой бота и веб-интерфейсом.
Обеспечивает real-time синхронизацию данных через WebSocket.

Основные возможности:
- Подключение событий трейдеров к WebSocket
- Трансляция событий бирж в веб-интерфейс
- Системные события и метрики
- Event filtering и routing
- Асинхронная обработка событий
"""

import asyncio
import json
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from core.logging.logger_factory import get_global_logger_factory

logger_factory = get_global_logger_factory()
logger = logger_factory.get_logger("event_bridge")


class EventType(Enum):
    """Типы событий для веб-интерфейса"""

    # Трейдер события
    TRADER_STARTED = "trader_started"
    TRADER_STOPPED = "trader_stopped"
    TRADER_PAUSED = "trader_paused"
    TRADER_RESUMED = "trader_resumed"
    TRADER_ERROR = "trader_error"
    TRADER_STATUS_CHANGED = "trader_status_changed"

    # Торговые события
    TRADE_OPENED = "trade_opened"
    TRADE_CLOSED = "trade_closed"
    TRADE_UPDATED = "trade_updated"
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"

    # Позиции
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    POSITION_UPDATED = "position_updated"

    # Биржи
    EXCHANGE_CONNECTED = "exchange_connected"
    EXCHANGE_DISCONNECTED = "exchange_disconnected"
    EXCHANGE_ERROR = "exchange_error"
    EXCHANGE_LATENCY_UPDATE = "exchange_latency_update"

    # Системные события
    SYSTEM_STATUS_UPDATE = "system_status_update"
    SYSTEM_METRICS_UPDATE = "system_metrics_update"
    SYSTEM_ALERT = "system_alert"
    SYSTEM_ERROR = "system_error"

    # ML события
    ML_PREDICTION = "ml_prediction"
    ML_MODEL_LOADED = "ml_model_loaded"
    ML_MODEL_ERROR = "ml_model_error"

    # Стратегии
    STRATEGY_SIGNAL = "strategy_signal"
    STRATEGY_ACTIVATED = "strategy_activated"
    STRATEGY_DEACTIVATED = "strategy_deactivated"


class EventBridge:
    """
    Мост событий между системой бота и веб-интерфейсом

    Обеспечивает двустороннюю связь:
    - События от компонентов бота → WebSocket → Frontend
    - Команды от Frontend → WebSocket → компоненты бота
    """

    def __init__(self, trader_manager=None, exchange_factory=None, config_manager=None):
        """
        Инициализация моста событий

        Args:
            trader_manager: Менеджер трейдеров
            exchange_factory: Фабрика бирж
            config_manager: Менеджер конфигурации
        """
        self.trader_manager = trader_manager
        self.exchange_factory = exchange_factory
        self.config_manager = config_manager

        # WebSocket менеджер (будет инициализирован позже)
        self.websocket_manager: Optional[Any] = None

        # Подписчики на события
        self.event_handlers: dict[EventType, list[Callable]] = {}
        self.websocket_connections: set = set()

        # Фильтры событий
        self.event_filters: dict[str, Callable] = {}

        # Состояние
        self._active = False
        self._last_heartbeat = datetime.now()

        logger.info("EventBridge инициализирован")

    async def initialize(self):
        """Инициализация моста событий"""
        if self._active:
            logger.warning("EventBridge уже активен")
            return

        logger.info("Инициализация EventBridge...")

        try:
            # Подключаем события трейдеров
            if self.trader_manager:
                await self._connect_trader_events()

            # Подключаем события бирж
            if self.exchange_factory:
                await self._connect_exchange_events()

            # Запускаем периодические задачи
            await self._start_periodic_tasks()

            self._active = True
            logger.info("EventBridge успешно инициализирован")

        except Exception as e:
            logger.error(f"Ошибка инициализации EventBridge: {e}")
            raise

    async def _connect_trader_events(self):
        """Подключение событий трейдеров"""
        try:
            # Пример подключения событий (будет адаптировано под реальную API трейдеров)

            # Событие запуска трейдера
            # self.trader_manager.on_trader_started += self._on_trader_started

            # Событие остановки трейдера
            # self.trader_manager.on_trader_stopped += self._on_trader_stopped

            # Событие торговой сделки
            # self.trader_manager.on_trade_executed += self._on_trade_executed

            # Событие изменения позиции
            # self.trader_manager.on_position_changed += self._on_position_changed

            # Пока используем mock подключение
            logger.info("Подключены события трейдеров (mock)")

        except Exception as e:
            logger.error(f"Ошибка подключения событий трейдеров: {e}")
            raise

    async def _connect_exchange_events(self):
        """Подключение событий бирж"""
        try:
            # Пример подключения событий бирж

            # Событие подключения к бирже
            # self.exchange_factory.on_exchange_connected += self._on_exchange_connected

            # Событие отключения от биржи
            # self.exchange_factory.on_exchange_disconnected += self._on_exchange_disconnected

            # Событие обновления latency
            # self.exchange_factory.on_latency_update += self._on_latency_update

            # Пока используем mock подключение
            logger.info("Подключены события бирж (mock)")

        except Exception as e:
            logger.error(f"Ошибка подключения событий бирж: {e}")
            raise

    async def _start_periodic_tasks(self):
        """Запуск периодических задач"""
        try:
            # Задача отправки системных метрик каждые 5 секунд
            asyncio.create_task(self._periodic_system_metrics())

            # Задача heartbeat каждые 30 секунд
            asyncio.create_task(self._periodic_heartbeat())

            logger.info("Запущены периодические задачи EventBridge")

        except Exception as e:
            logger.error(f"Ошибка запуска периодических задач: {e}")
            raise

    # =================== EVENT HANDLERS ===================

    async def _on_trader_started(self, trader_id: str, trader_info: dict[str, Any]):
        """Обработчик события запуска трейдера"""
        await self.emit_event(
            EventType.TRADER_STARTED,
            {
                "trader_id": trader_id,
                "trader_info": trader_info,
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def _on_trader_stopped(self, trader_id: str, reason: str = ""):
        """Обработчик события остановки трейдера"""
        await self.emit_event(
            EventType.TRADER_STOPPED,
            {
                "trader_id": trader_id,
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def _on_trade_executed(self, trade_data: dict[str, Any]):
        """Обработчик события выполнения сделки"""
        await self.emit_event(
            EventType.TRADE_OPENED,
            {
                "trade_id": trade_data.get("trade_id"),
                "trader_id": trade_data.get("trader_id"),
                "symbol": trade_data.get("symbol"),
                "side": trade_data.get("side"),
                "quantity": trade_data.get("quantity"),
                "price": trade_data.get("price"),
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def _on_position_changed(self, position_data: dict[str, Any]):
        """Обработчик события изменения позиции"""
        await self.emit_event(
            EventType.POSITION_UPDATED,
            {
                "trader_id": position_data.get("trader_id"),
                "symbol": position_data.get("symbol"),
                "size": position_data.get("size"),
                "unrealized_pnl": position_data.get("unrealized_pnl"),
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def _on_exchange_connected(self, exchange_name: str):
        """Обработчик события подключения к бирже"""
        await self.emit_event(
            EventType.EXCHANGE_CONNECTED,
            {"exchange": exchange_name, "timestamp": datetime.now().isoformat()},
        )

    async def _on_exchange_disconnected(self, exchange_name: str, reason: str = ""):
        """Обработчик события отключения от биржи"""
        await self.emit_event(
            EventType.EXCHANGE_DISCONNECTED,
            {
                "exchange": exchange_name,
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
            },
        )

    # =================== PERIODIC TASKS ===================

    async def _periodic_system_metrics(self):
        """Периодическая отправка системных метрик"""
        while self._active:
            try:
                metrics = await self._collect_system_metrics()
                await self.emit_event(EventType.SYSTEM_METRICS_UPDATE, metrics)

                await asyncio.sleep(5)  # Каждые 5 секунд

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в periodic_system_metrics: {e}")
                await asyncio.sleep(5)

    async def _periodic_heartbeat(self):
        """Периодический heartbeat"""
        while self._active:
            try:
                self._last_heartbeat = datetime.now()

                await self.emit_event(
                    EventType.SYSTEM_STATUS_UPDATE,
                    {
                        "status": "running",
                        "heartbeat": self._last_heartbeat.isoformat(),
                        "active_connections": len(self.websocket_connections),
                    },
                )

                await asyncio.sleep(30)  # Каждые 30 секунд

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в periodic_heartbeat: {e}")
                await asyncio.sleep(30)

    async def _collect_system_metrics(self) -> dict[str, Any]:
        """Сбор системных метрик"""
        try:
            import psutil

            metrics = {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": psutil.cpu_percent(interval=None),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent,
                "network_connections": len(psutil.net_connections()),
                "active_traders": 0,  # Будет получено от trader_manager
                "active_positions": 0,  # Будет получено от exchanges
                "websocket_connections": len(self.websocket_connections),
            }

            # Добавляем метрики трейдеров если доступны
            if self.trader_manager:
                try:
                    # metrics["active_traders"] = len(self.trader_manager.get_active_traders())
                    pass
                except:
                    pass

            return metrics

        except Exception as e:
            logger.error(f"Ошибка сбора системных метрик: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": "Failed to collect metrics",
            }

    # =================== EVENT EMISSION ===================

    async def emit_event(self, event_type: EventType, data: dict[str, Any]):
        """
        Отправка события всем подписчикам

        Args:
            event_type: Тип события
            data: Данные события
        """
        try:
            event_message = {
                "type": event_type.value,
                "data": data,
                "timestamp": datetime.now().isoformat(),
            }

            # Применяем фильтры
            if await self._should_emit_event(event_type, data):
                # Отправляем через WebSocket
                await self._broadcast_to_websockets(event_message)

                # Вызываем локальные обработчики
                await self._call_local_handlers(event_type, data)

        except Exception as e:
            logger.error(f"Ошибка отправки события {event_type.value}: {e}")

    async def _should_emit_event(self, event_type: EventType, data: dict[str, Any]) -> bool:
        """Проверка нужно ли отправлять событие"""
        try:
            # Проверяем фильтры
            filter_key = event_type.value
            if filter_key in self.event_filters:
                return await self.event_filters[filter_key](data)

            return True

        except Exception as e:
            logger.error(f"Ошибка проверки фильтра события {event_type.value}: {e}")
            return True

    async def _broadcast_to_websockets(self, message: dict[str, Any]):
        """Отправка сообщения всем WebSocket подключениям"""
        if not self.websocket_connections:
            return

        message_json = json.dumps(message, ensure_ascii=False)

        # Создаем копию множества для итерации
        connections_copy = self.websocket_connections.copy()

        for websocket in connections_copy:
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.warning(f"Ошибка отправки сообщения через WebSocket: {e}")
                # Удаляем неработающее соединение
                self.websocket_connections.discard(websocket)

    async def _call_local_handlers(self, event_type: EventType, data: dict[str, Any]):
        """Вызов локальных обработчиков события"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    await handler(data)
                except Exception as e:
                    logger.error(f"Ошибка в обработчике события {event_type.value}: {e}")

    # =================== WEBSOCKET MANAGEMENT ===================

    def add_websocket_connection(self, websocket):
        """Добавить WebSocket соединение"""
        self.websocket_connections.add(websocket)
        logger.info(f"Добавлено WebSocket соединение. Всего: {len(self.websocket_connections)}")

    def remove_websocket_connection(self, websocket):
        """Удалить WebSocket соединение"""
        self.websocket_connections.discard(websocket)
        logger.info(f"Удалено WebSocket соединение. Осталось: {len(self.websocket_connections)}")

    # =================== EVENT SUBSCRIPTION ===================

    def subscribe_to_event(self, event_type: EventType, handler: Callable):
        """Подписаться на событие"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []

        self.event_handlers[event_type].append(handler)
        logger.info(f"Добавлен обработчик для события {event_type.value}")

    def unsubscribe_from_event(self, event_type: EventType, handler: Callable):
        """Отписаться от события"""
        if event_type in self.event_handlers:
            try:
                self.event_handlers[event_type].remove(handler)
                logger.info(f"Удален обработчик для события {event_type.value}")
            except ValueError:
                pass

    def add_event_filter(self, event_type: EventType, filter_func: Callable):
        """Добавить фильтр для события"""
        self.event_filters[event_type.value] = filter_func
        logger.info(f"Добавлен фильтр для события {event_type.value}")

    # =================== MANUAL EVENT TRIGGERS ===================

    async def trigger_trader_event(
        self, trader_id: str, event_type: str, data: dict[str, Any] = None
    ):
        """Ручная отправка события трейдера"""
        event_data = {"trader_id": trader_id, "event_type": event_type, **(data or {})}

        if event_type == "started":
            await self.emit_event(EventType.TRADER_STARTED, event_data)
        elif event_type == "stopped":
            await self.emit_event(EventType.TRADER_STOPPED, event_data)
        elif event_type == "error":
            await self.emit_event(EventType.TRADER_ERROR, event_data)

    async def trigger_system_alert(self, level: str, message: str, component: str = "system"):
        """Ручная отправка системного алерта"""
        await self.emit_event(
            EventType.SYSTEM_ALERT,
            {
                "level": level,
                "message": message,
                "component": component,
                "timestamp": datetime.now().isoformat(),
            },
        )

    # =================== STATUS METHODS ===================

    def is_active(self) -> bool:
        """Проверить активен ли мост событий"""
        return self._active

    def get_status(self) -> dict[str, Any]:
        """Получить статус моста событий"""
        return {
            "active": self._active,
            "websocket_connections": len(self.websocket_connections),
            "event_handlers_count": sum(len(handlers) for handlers in self.event_handlers.values()),
            "event_filters_count": len(self.event_filters),
            "last_heartbeat": self._last_heartbeat.isoformat(),
            "components": {
                "trader_manager": self.trader_manager is not None,
                "exchange_factory": self.exchange_factory is not None,
                "config_manager": self.config_manager is not None,
            },
        }

    # =================== CLEANUP ===================

    async def cleanup(self):
        """Очистка ресурсов"""
        logger.info("Очистка EventBridge...")

        self._active = False

        # Закрываем все WebSocket соединения
        for websocket in self.websocket_connections.copy():
            try:
                await websocket.close()
            except:
                pass

        self.websocket_connections.clear()

        # Очищаем обработчики
        self.event_handlers.clear()
        self.event_filters.clear()

        logger.info("EventBridge очищен")

    async def shutdown(self):
        """Корректное завершение работы EventBridge"""
        await self.cleanup()
