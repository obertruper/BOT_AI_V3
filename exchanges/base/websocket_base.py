"""
Базовый WebSocket клиент для мульти-биржевой системы BOT_Trading v3.0

Предоставляет унифицированный интерфейс для WebSocket подключений ко всем биржам:
- Автоматическое переподключение
- Управление подписками
- Обработка heartbeat/ping-pong
- Мониторинг состояния соединения
"""

import asyncio
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from enum import Enum

import websockets
from websockets.exceptions import ConnectionClosed, InvalidURI, InvalidHandshake

from .exceptions import WebSocketError, SubscriptionError, ConnectionError


class WebSocketState(Enum):
    """Состояние WebSocket соединения"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    CLOSING = "closing"
    CLOSED = "closed"
    ERROR = "error"


class MessageType(Enum):
    """Типы WebSocket сообщений"""
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    HEARTBEAT = "heartbeat"
    PONG = "pong"
    DATA = "data"
    ERROR = "error"
    AUTH = "auth"


@dataclass
class WebSocketMessage:
    """Структура WebSocket сообщения"""
    message_type: MessageType
    channel: str
    symbol: Optional[str] = None
    data: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    raw_data: Optional[Dict[str, Any]] = None
    exchange_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        return {
            'type': self.message_type.value,
            'channel': self.channel,
            'symbol': self.symbol,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
            'exchange': self.exchange_name
        }


@dataclass
class Subscription:
    """Подписка WebSocket"""
    channel: str
    symbol: Optional[str]
    callback: Callable[[WebSocketMessage], None]
    params: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = False
    subscription_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    last_message_at: Optional[datetime] = None
    message_count: int = 0


class BaseWebSocketClient(ABC):
    """
    Базовый WebSocket клиент для всех бирж
    
    Предоставляет общую функциональность для WebSocket подключений:
    - Управление соединением и переподключениями
    - Подписки на каналы
    - Обработка сообщений
    - Ping/pong механизм
    """
    
    def __init__(self,
                 exchange_name: str,
                 base_url: str,
                 api_key: Optional[str] = None,
                 api_secret: Optional[str] = None,
                 timeout: int = 30,
                 ping_interval: int = 20,
                 max_reconnect_attempts: int = 10,
                 reconnect_delay: int = 5):
        
        self.exchange_name = exchange_name
        self.base_url = base_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = timeout
        self.ping_interval = ping_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        
        # Состояние соединения
        self.state = WebSocketState.DISCONNECTED
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.connection_url: Optional[str] = None
        
        # Подписки
        self.subscriptions: Dict[str, Subscription] = {}
        self.pending_subscriptions: List[Subscription] = []
        
        # Задачи и управление
        self.listen_task: Optional[asyncio.Task] = None
        self.ping_task: Optional[asyncio.Task] = None
        self.reconnect_task: Optional[asyncio.Task] = None
        
        # Метрики
        self.connection_attempts = 0
        self.reconnect_attempts = 0
        self.last_ping_time: Optional[datetime] = None
        self.last_pong_time: Optional[datetime] = None
        self.messages_received = 0
        self.messages_sent = 0
        
        # Логирование
        self.logger = logging.getLogger(f'websocket.{exchange_name}')
        
        # События
        self.on_connect_callback: Optional[Callable] = None
        self.on_disconnect_callback: Optional[Callable] = None
        self.on_error_callback: Optional[Callable] = None
        
    # =================== АБСТРАКТНЫЕ МЕТОДЫ ===================
    
    @abstractmethod
    def build_connection_url(self) -> str:
        """Построение URL для подключения"""
        pass
    
    @abstractmethod
    def build_auth_message(self) -> Optional[Dict[str, Any]]:
        """Построение сообщения аутентификации"""
        pass
    
    @abstractmethod  
    def build_subscribe_message(self, subscription: Subscription) -> Dict[str, Any]:
        """Построение сообщения подписки"""
        pass
    
    @abstractmethod
    def build_unsubscribe_message(self, subscription: Subscription) -> Dict[str, Any]:
        """Построение сообщения отписки"""
        pass
    
    @abstractmethod
    def build_ping_message(self) -> Dict[str, Any]:
        """Построение ping сообщения"""
        pass
    
    @abstractmethod
    def parse_message(self, raw_message: str) -> Optional[WebSocketMessage]:
        """Парсинг входящего сообщения"""
        pass
    
    @abstractmethod
    def is_pong_message(self, message: Dict[str, Any]) -> bool:
        """Проверка, является ли сообщение pong"""
        pass
    
    # =================== ОСНОВНЫЕ МЕТОДЫ ===================
    
    async def connect(self) -> bool:
        """Установка WebSocket соединения"""
        if self.state in [WebSocketState.CONNECTED, WebSocketState.CONNECTING]:
            return True
        
        try:
            self.state = WebSocketState.CONNECTING
            self.connection_attempts += 1
            
            self.connection_url = self.build_connection_url()
            self.logger.info(f"Connecting to {self.connection_url}")
            
            # Установка соединения
            self.websocket = await websockets.connect(
                self.connection_url,
                timeout=self.timeout,
                ping_interval=None,  # Управляем ping сами
                ping_timeout=None
            )
            
            self.state = WebSocketState.CONNECTED
            self.reconnect_attempts = 0
            
            # Аутентификация если требуется
            if self.api_key and self.api_secret:
                await self._authenticate()
            
            # Запуск задач
            await self._start_tasks()
            
            # Восстановление подписок
            await self._restore_subscriptions()
            
            # Вызов callback
            if self.on_connect_callback:
                await self._safe_callback(self.on_connect_callback)
            
            self.logger.info("WebSocket connected successfully")
            return True
            
        except Exception as e:
            self.state = WebSocketState.ERROR
            error_msg = f"Failed to connect: {e}"
            self.logger.error(error_msg)
            
            if self.on_error_callback:
                await self._safe_callback(self.on_error_callback, e)
            
            raise WebSocketError(
                self.exchange_name,
                "connection",
                ws_url=self.connection_url,
                reason=str(e)
            )
    
    async def disconnect(self) -> None:
        """Отключение WebSocket"""
        if self.state == WebSocketState.DISCONNECTED:
            return
        
        self.logger.info("Disconnecting WebSocket")
        self.state = WebSocketState.CLOSING
        
        # Остановка задач
        await self._stop_tasks()
        
        # Закрытие соединения
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                self.logger.warning(f"Error closing websocket: {e}")
        
        self.websocket = None
        self.state = WebSocketState.DISCONNECTED
        
        # Callback отключения
        if self.on_disconnect_callback:
            await self._safe_callback(self.on_disconnect_callback)
        
        self.logger.info("WebSocket disconnected")
    
    async def subscribe(self,
                       channel: str,
                       callback: Callable[[WebSocketMessage], None],
                       symbol: Optional[str] = None,
                       **params) -> str:
        """Подписка на канал"""
        subscription = Subscription(
            channel=channel,
            symbol=symbol,
            callback=callback,
            params=params
        )
        
        subscription_id = subscription.subscription_id
        self.subscriptions[subscription_id] = subscription
        
        # Если подключены, отправляем подписку сразу
        if self.state == WebSocketState.CONNECTED:
            await self._send_subscription(subscription)
        else:
            # Иначе добавляем в очередь
            self.pending_subscriptions.append(subscription)
        
        self.logger.info(f"Subscribed to {channel}" + (f" for {symbol}" if symbol else ""))
        return subscription_id
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Отписка от канала"""
        if subscription_id not in self.subscriptions:
            return False
        
        subscription = self.subscriptions[subscription_id]
        
        # Отправляем сообщение отписки если подключены
        if self.state == WebSocketState.CONNECTED:
            try:
                unsubscribe_msg = self.build_unsubscribe_message(subscription)
                await self._send_message(unsubscribe_msg)
            except Exception as e:
                self.logger.warning(f"Failed to send unsubscribe message: {e}")
        
        # Удаляем подписку
        del self.subscriptions[subscription_id]
        subscription.is_active = False
        
        self.logger.info(f"Unsubscribed from {subscription.channel}")
        return True
    
    async def unsubscribe_all(self) -> None:
        """Отписка от всех каналов"""
        subscription_ids = list(self.subscriptions.keys())
        for subscription_id in subscription_ids:
            await self.unsubscribe(subscription_id)
    
    # =================== ВНУТРЕННИЕ МЕТОДЫ ===================
    
    async def _authenticate(self) -> None:
        """Аутентификация в WebSocket"""
        auth_message = self.build_auth_message()
        if auth_message:
            await self._send_message(auth_message)
            self.logger.info("Authentication message sent")
    
    async def _start_tasks(self) -> None:
        """Запуск фоновых задач"""
        # Задача прослушивания сообщений
        self.listen_task = asyncio.create_task(self._listen_loop())
        
        # Задача ping
        self.ping_task = asyncio.create_task(self._ping_loop())
    
    async def _stop_tasks(self) -> None:
        """Остановка фоновых задач"""
        tasks = [self.listen_task, self.ping_task, self.reconnect_task]
        
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.listen_task = None
        self.ping_task = None
        self.reconnect_task = None
    
    async def _listen_loop(self) -> None:
        """Основной цикл прослушивания сообщений"""
        try:
            while self.state == WebSocketState.CONNECTED:
                if not self.websocket:
                    break
                
                try:
                    # Получение сообщения
                    raw_message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=self.timeout
                    )
                    
                    self.messages_received += 1
                    
                    # Парсинг и обработка
                    await self._handle_raw_message(raw_message)
                    
                except asyncio.TimeoutError:
                    self.logger.warning("No message received within timeout")
                    continue
                
                except ConnectionClosed:
                    self.logger.warning("WebSocket connection closed")
                    break
                
        except Exception as e:
            self.logger.error(f"Error in listen loop: {e}")
            
        finally:
            if self.state == WebSocketState.CONNECTED:
                await self._handle_disconnection()
    
    async def _ping_loop(self) -> None:
        """Цикл отправки ping сообщений"""
        try:
            while self.state == WebSocketState.CONNECTED:
                await asyncio.sleep(self.ping_interval)
                
                if self.state != WebSocketState.CONNECTED:
                    break
                
                try:
                    ping_message = self.build_ping_message()
                    if ping_message:
                        await self._send_message(ping_message)
                        self.last_ping_time = datetime.now()
                        
                except Exception as e:
                    self.logger.warning(f"Failed to send ping: {e}")
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Error in ping loop: {e}")
    
    async def _handle_raw_message(self, raw_message: str) -> None:
        """Обработка сырого сообщения"""
        try:
            # Парсинг сообщения
            parsed_message = self.parse_message(raw_message)
            if not parsed_message:
                return
            
            # Проверка на pong
            if parsed_message.message_type == MessageType.PONG:
                self.last_pong_time = datetime.now()
                return
            
            # Обработка сообщений подписок
            if parsed_message.message_type == MessageType.DATA:
                await self._handle_subscription_message(parsed_message)
            
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            self.logger.debug(f"Raw message: {raw_message}")
    
    async def _handle_subscription_message(self, message: WebSocketMessage) -> None:
        """Обработка сообщения подписки"""
        # Поиск соответствующих подписок
        matching_subscriptions = []
        
        for subscription in self.subscriptions.values():
            if subscription.channel == message.channel:
                if not message.symbol or not subscription.symbol or subscription.symbol == message.symbol:
                    matching_subscriptions.append(subscription)
        
        # Вызов callbacks
        for subscription in matching_subscriptions:
            subscription.last_message_at = datetime.now()
            subscription.message_count += 1
            
            try:
                await self._safe_callback(subscription.callback, message)
            except Exception as e:
                self.logger.error(f"Error in subscription callback: {e}")
    
    async def _handle_disconnection(self) -> None:
        """Обработка отключения"""
        if self.state == WebSocketState.CLOSING:
            return
        
        self.state = WebSocketState.RECONNECTING
        
        # Callback отключения
        if self.on_disconnect_callback:
            await self._safe_callback(self.on_disconnect_callback)
        
        # Запуск переподключения
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_task = asyncio.create_task(self._reconnect_loop())
        else:
            self.logger.error("Max reconnection attempts reached")
            self.state = WebSocketState.ERROR
    
    async def _reconnect_loop(self) -> None:
        """Цикл переподключения"""
        while (self.state == WebSocketState.RECONNECTING and 
               self.reconnect_attempts < self.max_reconnect_attempts):
            
            self.reconnect_attempts += 1
            delay = self.reconnect_delay * (2 ** (self.reconnect_attempts - 1))  # Exponential backoff
            
            self.logger.info(f"Reconnecting in {delay} seconds (attempt {self.reconnect_attempts})")
            await asyncio.sleep(delay)
            
            try:
                await self.connect()
                return  # Успешное переподключение
                
            except Exception as e:
                self.logger.warning(f"Reconnection attempt {self.reconnect_attempts} failed: {e}")
        
        # Превышено максимальное количество попыток
        self.state = WebSocketState.ERROR
        self.logger.error("Failed to reconnect after maximum attempts")
    
    async def _restore_subscriptions(self) -> None:
        """Восстановление подписок после переподключения"""
        # Активные подписки
        for subscription in self.subscriptions.values():
            if not subscription.is_active:
                await self._send_subscription(subscription)
        
        # Ожидающие подписки
        for subscription in self.pending_subscriptions:
            await self._send_subscription(subscription)
        
        self.pending_subscriptions.clear()
    
    async def _send_subscription(self, subscription: Subscription) -> None:
        """Отправка подписки"""
        try:
            subscribe_msg = self.build_subscribe_message(subscription)
            await self._send_message(subscribe_msg)
            subscription.is_active = True
            
        except Exception as e:
            self.logger.error(f"Failed to send subscription for {subscription.channel}: {e}")
            raise SubscriptionError(
                self.exchange_name,
                subscription.channel,
                subscription.symbol,
                str(e)
            )
    
    async def _send_message(self, message: Dict[str, Any]) -> None:
        """Отправка сообщения"""
        if not self.websocket or self.state != WebSocketState.CONNECTED:
            raise WebSocketError(
                self.exchange_name,
                "send_message",
                reason="Not connected"
            )
        
        try:
            message_str = json.dumps(message)
            await self.websocket.send(message_str)
            self.messages_sent += 1
            
        except Exception as e:
            raise WebSocketError(
                self.exchange_name,
                "send_message",
                reason=str(e)
            )
    
    async def _safe_callback(self, callback: Callable, *args) -> None:
        """Безопасный вызов callback"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            self.logger.error(f"Error in callback: {e}")
    
    # =================== СВОЙСТВА И МЕТОДЫ СОСТОЯНИЯ ===================
    
    @property
    def is_connected(self) -> bool:
        """Подключен ли WebSocket"""
        return self.state == WebSocketState.CONNECTED
    
    @property
    def is_reconnecting(self) -> bool:
        """Происходит ли переподключение"""
        return self.state == WebSocketState.RECONNECTING
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики WebSocket"""
        return {
            'state': self.state.value,
            'connection_attempts': self.connection_attempts,
            'reconnect_attempts': self.reconnect_attempts,
            'messages_received': self.messages_received,
            'messages_sent': self.messages_sent,
            'active_subscriptions': len([s for s in self.subscriptions.values() if s.is_active]),
            'total_subscriptions': len(self.subscriptions),
            'last_ping': self.last_ping_time.isoformat() if self.last_ping_time else None,
            'last_pong': self.last_pong_time.isoformat() if self.last_pong_time else None,
            'connection_url': self.connection_url
        }
    
    def set_callbacks(self,
                     on_connect: Optional[Callable] = None,
                     on_disconnect: Optional[Callable] = None,
                     on_error: Optional[Callable] = None):
        """Установка callback функций"""
        if on_connect:
            self.on_connect_callback = on_connect
        if on_disconnect:
            self.on_disconnect_callback = on_disconnect
        if on_error:
            self.on_error_callback = on_error
    
    # =================== CONTEXT MANAGER ===================
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()


# =================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===================

def create_subscription_id(channel: str, symbol: Optional[str] = None) -> str:
    """Создание ID подписки"""
    parts = [channel]
    if symbol:
        parts.append(symbol)
    return "_".join(parts) + "_" + str(uuid.uuid4())[:8]


async def test_websocket_connection(ws_client: BaseWebSocketClient) -> Dict[str, Any]:
    """Тестирование WebSocket соединения"""
    test_result = {
        'exchange': ws_client.exchange_name,
        'connected': False,
        'connection_time_ms': 0,
        'error': None,
        'stats': None
    }
    
    try:
        start_time = time.time()
        
        # Попытка подключения
        success = await ws_client.connect()
        test_result['connected'] = success
        
        if success:
            connection_time = (time.time() - start_time) * 1000
            test_result['connection_time_ms'] = round(connection_time, 2)
            test_result['stats'] = ws_client.get_stats()
            
            # Отключение после теста
            await ws_client.disconnect()
        
    except Exception as e:
        test_result['error'] = str(e)
    
    return test_result