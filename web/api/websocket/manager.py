"""
WebSocket Manager для BOT_Trading v3.0

Управление WebSocket подключениями для real-time торгового интерфейса.

Основные возможности:
- Управление WebSocket соединениями
- Аутентификация пользователей
- Подписки на потоки данных
- Broadcast сообщений
- Heartbeat и keepalive
- Обработка отключений
"""

import asyncio
import json
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, Union

from fastapi import WebSocket, WebSocketDisconnect

from core.logging.logger_factory import get_global_logger_factory

logger_factory = get_global_logger_factory()
logger = logger_factory.get_logger("websocket_manager")


class WebSocketConnection:
    """Класс для управления отдельным WebSocket соединением"""

    def __init__(self, websocket: WebSocket, connection_id: str, user_id: str | None = None):
        self.websocket = websocket
        self.connection_id = connection_id
        self.user_id = user_id
        self.connected_at = datetime.now()
        self.last_ping = datetime.now()
        self.subscriptions: set[str] = set()
        self.is_authenticated = user_id is not None
        self.metadata: dict[str, Any] = {}

    async def send_message(self, message: dict[str, Any]):
        """Отправка сообщения через WebSocket"""
        try:
            await self.websocket.send_text(json.dumps(message, ensure_ascii=False))
            self.last_ping = datetime.now()
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения через WebSocket {self.connection_id}: {e}")
            raise

    async def send_text(self, text: str):
        """Отправка текстового сообщения"""
        try:
            await self.websocket.send_text(text)
            self.last_ping = datetime.now()
        except Exception as e:
            logger.error(f"Ошибка отправки текста через WebSocket {self.connection_id}: {e}")
            raise

    async def close(self, code: int = 1000, reason: str = ""):
        """Закрытие соединения"""
        try:
            await self.websocket.close(code=code, reason=reason)
        except Exception as e:
            logger.warning(f"Ошибка закрытия WebSocket {self.connection_id}: {e}")

    def add_subscription(self, stream: str):
        """Добавить подписку на поток"""
        self.subscriptions.add(stream)
        logger.debug(f"WebSocket {self.connection_id} подписался на поток {stream}")

    def remove_subscription(self, stream: str):
        """Удалить подписку на поток"""
        self.subscriptions.discard(stream)
        logger.debug(f"WebSocket {self.connection_id} отписался от потока {stream}")

    def is_subscribed_to(self, stream: str) -> bool:
        """Проверить подписку на поток"""
        return stream in self.subscriptions

    def get_connection_info(self) -> dict[str, Any]:
        """Получить информацию о соединении"""
        return {
            "connection_id": self.connection_id,
            "user_id": self.user_id,
            "connected_at": self.connected_at.isoformat(),
            "last_ping": self.last_ping.isoformat(),
            "is_authenticated": self.is_authenticated,
            "subscriptions": list(self.subscriptions),
            "uptime_seconds": (datetime.now() - self.connected_at).total_seconds(),
        }


class WebSocketManager:
    """
    Менеджер WebSocket соединений

    Обеспечивает:
    - Управление активными соединениями
    - Аутентификация и авторизация
    - Подписки на потоки данных
    - Broadcast сообщений
    - Heartbeat механизм
    """

    def __init__(self):
        self.connections: dict[str, WebSocketConnection] = {}
        self.user_connections: dict[str, set[str]] = {}  # user_id -> set of connection_ids
        self.stream_subscribers: dict[str, set[str]] = {}  # stream -> set of connection_ids

        # Настройки
        self.heartbeat_interval = 30  # секунд
        self.connection_timeout = 300  # секунд
        self.max_connections_per_user = 5

        # Состояние
        self._running = False
        self._heartbeat_task: asyncio.Optional[Task] = None

        # Обработчики событий
        self.event_handlers: dict[str, list[Callable]] = {}

        logger.info("WebSocketManager инициализирован")

    async def start(self):
        """Запуск менеджера WebSocket"""
        if self._running:
            logger.warning("WebSocketManager уже запущен")
            return

        self._running = True

        # Запускаем задачу heartbeat
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        logger.info("WebSocketManager запущен")

    async def stop(self):
        """Остановка менеджера WebSocket"""
        if not self._running:
            return

        self._running = False

        # Останавливаем heartbeat
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # Закрываем все соединения
        await self._close_all_connections()

        logger.info("WebSocketManager остановлен")

    async def connect(self, websocket: WebSocket, user_id: str | None = None) -> str:
        """
        Подключение нового WebSocket

        Args:
            websocket: WebSocket соединение
            user_id: ID пользователя (если аутентифицирован)

        Returns:
            connection_id: ID созданного соединения
        """
        connection_id = str(uuid.uuid4())

        # Проверяем лимит соединений для пользователя
        if user_id and self._check_user_connection_limit(user_id):
            await websocket.close(code=1008, reason="Too many connections")
            raise Exception(f"Превышен лимит соединений для пользователя {user_id}")

        try:
            await websocket.accept()

            # Создаем объект соединения
            connection = WebSocketConnection(websocket, connection_id, user_id)

            # Сохраняем соединение
            self.connections[connection_id] = connection

            # Добавляем в пользовательские соединения
            if user_id:
                if user_id not in self.user_connections:
                    self.user_connections[user_id] = set()
                self.user_connections[user_id].add(connection_id)

            # Отправляем приветственное сообщение
            await connection.send_message(
                {
                    "type": "connection_established",
                    "connection_id": connection_id,
                    "authenticated": user_id is not None,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            logger.info(f"Новое WebSocket соединение: {connection_id} (пользователь: {user_id})")

            # Вызываем обработчики события подключения
            await self._trigger_event(
                "connection_established",
                {"connection_id": connection_id, "user_id": user_id},
            )

            return connection_id

        except Exception as e:
            logger.error(f"Ошибка подключения WebSocket: {e}")
            try:
                await websocket.close(code=1011, reason="Internal error")
            except:
                pass
            raise

    async def disconnect(self, connection_id: str, code: int = 1000, reason: str = ""):
        """
        Отключение WebSocket

        Args:
            connection_id: ID соединения
            code: Код закрытия
            reason: Причина закрытия
        """
        if connection_id not in self.connections:
            return

        connection = self.connections[connection_id]

        try:
            # Закрываем соединение
            await connection.close(code=code, reason=reason)
        except:
            pass

        # Удаляем из всех подписок
        for stream in list(connection.subscriptions):
            self._remove_from_stream(connection_id, stream)

        # Удаляем из пользовательских соединений
        if connection.user_id and connection.user_id in self.user_connections:
            self.user_connections[connection.user_id].discard(connection_id)
            if not self.user_connections[connection.user_id]:
                del self.user_connections[connection.user_id]

        # Удаляем соединение
        del self.connections[connection_id]

        logger.info(
            f"WebSocket соединение отключено: {connection_id} (код: {code}, причина: {reason})"
        )

        # Вызываем обработчики события отключения
        await self._trigger_event(
            "connection_closed",
            {
                "connection_id": connection_id,
                "user_id": connection.user_id,
                "code": code,
                "reason": reason,
            },
        )

    async def handle_websocket(self, websocket: WebSocket, user_id: str | None = None):
        """
        Обработка WebSocket соединения

        Args:
            websocket: WebSocket соединение
            user_id: ID пользователя
        """
        connection_id = None

        try:
            # Подключаем WebSocket
            connection_id = await self.connect(websocket, user_id)

            # Слушаем сообщения
            while True:
                try:
                    data = await websocket.receive_text()
                    await self._handle_message(connection_id, data)
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"Ошибка обработки сообщения WebSocket {connection_id}: {e}")
                    break

        except Exception as e:
            logger.error(f"Ошибка обработки WebSocket: {e}")

        finally:
            # Отключаем при выходе
            if connection_id:
                await self.disconnect(connection_id, reason="Connection closed")

    async def _handle_message(self, connection_id: str, message: str):
        """Обработка входящего сообщения"""
        try:
            data = json.loads(message)
            message_type = data.get("type")

            if message_type == "subscribe":
                await self._handle_subscribe(connection_id, data)
            elif message_type == "unsubscribe":
                await self._handle_unsubscribe(connection_id, data)
            elif message_type == "ping":
                await self._handle_ping(connection_id)
            elif message_type == "auth":
                await self._handle_auth(connection_id, data)
            else:
                logger.warning(f"Неизвестный тип сообщения: {message_type}")

        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON сообщения: {e}")
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")

    async def _handle_subscribe(self, connection_id: str, data: dict[str, Any]):
        """Обработка подписки на поток"""
        stream = data.get("stream")
        if not stream:
            return

        if connection_id in self.connections:
            connection = self.connections[connection_id]
            connection.add_subscription(stream)
            self._add_to_stream(connection_id, stream)

            await connection.send_message(
                {
                    "type": "subscribed",
                    "stream": stream,
                    "timestamp": datetime.now().isoformat(),
                }
            )

    async def _handle_unsubscribe(self, connection_id: str, data: dict[str, Any]):
        """Обработка отписки от потока"""
        stream = data.get("stream")
        if not stream:
            return

        if connection_id in self.connections:
            connection = self.connections[connection_id]
            connection.remove_subscription(stream)
            self._remove_from_stream(connection_id, stream)

            await connection.send_message(
                {
                    "type": "unsubscribed",
                    "stream": stream,
                    "timestamp": datetime.now().isoformat(),
                }
            )

    async def _handle_ping(self, connection_id: str):
        """Обработка ping сообщения"""
        if connection_id in self.connections:
            connection = self.connections[connection_id]
            connection.last_ping = datetime.now()

            await connection.send_message({"type": "pong", "timestamp": datetime.now().isoformat()})

    async def _handle_auth(self, connection_id: str, data: dict[str, Any]):
        """Обработка аутентификации"""
        # TODO: Реализовать аутентификацию по токену
        token = data.get("token")

        if connection_id in self.connections:
            connection = self.connections[connection_id]

            # Заглушка аутентификации
            if token:
                connection.is_authenticated = True
                connection.user_id = "authenticated_user"

                await connection.send_message(
                    {
                        "type": "auth_success",
                        "user_id": connection.user_id,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            else:
                await connection.send_message(
                    {
                        "type": "auth_failed",
                        "error": "Invalid token",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

    # =================== BROADCAST METHODS ===================

    async def broadcast_to_stream(self, stream: str, message: dict[str, Any]):
        """Отправка сообщения всем подписчикам потока"""
        if stream not in self.stream_subscribers:
            return

        # Создаем копию для безопасной итерации
        subscribers = self.stream_subscribers[stream].copy()

        for connection_id in subscribers:
            if connection_id in self.connections:
                try:
                    await self.connections[connection_id].send_message(message)
                except Exception as e:
                    logger.warning(
                        f"Ошибка отправки сообщения в поток {stream} для соединения {connection_id}: {e}"
                    )
                    # Удаляем неработающее соединение
                    await self.disconnect(connection_id, code=1011, reason="Send error")

    async def broadcast_to_user(self, user_id: str, message: dict[str, Any]):
        """Отправка сообщения всем соединениям пользователя"""
        if user_id not in self.user_connections:
            return

        # Создаем копию для безопасной итерации
        connection_ids = self.user_connections[user_id].copy()

        for connection_id in connection_ids:
            if connection_id in self.connections:
                try:
                    await self.connections[connection_id].send_message(message)
                except Exception as e:
                    logger.warning(
                        f"Ошибка отправки сообщения пользователю {user_id} для соединения {connection_id}: {e}"
                    )
                    # Удаляем неработающее соединение
                    await self.disconnect(connection_id, code=1011, reason="Send error")

    async def broadcast_to_all(self, message: dict[str, Any]):
        """Отправка сообщения всем подключенным клиентам"""
        # Создаем копию для безопасной итерации
        connection_ids = list(self.connections.keys())

        for connection_id in connection_ids:
            if connection_id in self.connections:
                try:
                    await self.connections[connection_id].send_message(message)
                except Exception as e:
                    logger.warning(
                        f"Ошибка broadcast сообщения для соединения {connection_id}: {e}"
                    )
                    # Удаляем неработающее соединение
                    await self.disconnect(connection_id, code=1011, reason="Send error")

    # =================== UTILITY METHODS ===================

    def _add_to_stream(self, connection_id: str, stream: str):
        """Добавить соединение к потоку"""
        if stream not in self.stream_subscribers:
            self.stream_subscribers[stream] = set()
        self.stream_subscribers[stream].add(connection_id)

    def _remove_from_stream(self, connection_id: str, stream: str):
        """Удалить соединение из потока"""
        if stream in self.stream_subscribers:
            self.stream_subscribers[stream].discard(connection_id)
            if not self.stream_subscribers[stream]:
                del self.stream_subscribers[stream]

    def _check_user_connection_limit(self, user_id: str) -> bool:
        """Проверить лимит соединений для пользователя"""
        if user_id in self.user_connections:
            return len(self.user_connections[user_id]) >= self.max_connections_per_user
        return False

    async def _heartbeat_loop(self):
        """Цикл heartbeat для проверки соединений"""
        while self._running:
            try:
                await self._check_connections()
                await asyncio.sleep(self.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в heartbeat loop: {e}")
                await asyncio.sleep(self.heartbeat_interval)

    async def _check_connections(self):
        """Проверка активности соединений"""
        now = datetime.now()
        timeout_threshold = now - timedelta(seconds=self.connection_timeout)

        # Найдем соединения с таймаутом
        timeout_connections = []
        for connection_id, connection in self.connections.items():
            if connection.last_ping < timeout_threshold:
                timeout_connections.append(connection_id)

        # Отключаем соединения с таймаутом
        for connection_id in timeout_connections:
            await self.disconnect(connection_id, code=1001, reason="Connection timeout")

    async def _close_all_connections(self):
        """Закрыть все соединения"""
        connection_ids = list(self.connections.keys())
        for connection_id in connection_ids:
            await self.disconnect(connection_id, code=1001, reason="Server shutdown")

    # =================== EVENT HANDLERS ===================

    def add_event_handler(self, event_type: str, handler: Callable):
        """Добавить обработчик события"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)

    async def _trigger_event(self, event_type: str, data: dict[str, Any]):
        """Вызвать обработчики события"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Ошибка в обработчике события {event_type}: {e}")

    # =================== STATUS METHODS ===================

    def get_status(self) -> dict[str, Any]:
        """Получить статус менеджера"""
        return {
            "running": self._running,
            "total_connections": len(self.connections),
            "authenticated_connections": sum(
                1 for conn in self.connections.values() if conn.is_authenticated
            ),
            "total_users": len(self.user_connections),
            "total_streams": len(self.stream_subscribers),
            "heartbeat_interval": self.heartbeat_interval,
            "connection_timeout": self.connection_timeout,
            "max_connections_per_user": self.max_connections_per_user,
        }

    def get_connections_info(self) -> list[dict[str, Any]]:
        """Получить информацию о всех соединениях"""
        return [conn.get_connection_info() for conn in self.connections.values()]

    def get_stream_info(self) -> dict[str, dict[str, Any]]:
        """Получить информацию о потоках"""
        return {
            stream: {
                "subscribers_count": len(subscribers),
                "subscribers": list(subscribers),
            }
            for stream, subscribers in self.stream_subscribers.items()
        }
