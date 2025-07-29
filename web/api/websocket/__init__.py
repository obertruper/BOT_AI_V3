"""
WebSocket модуль для BOT_Trading v3.0

Real-time WebSocket соединения для торгового интерфейса:
- manager: WebSocket менеджер подключений
- streams: Потоки данных (трейдеры, сделки, метрики)
- events: Типы и обработка событий
"""

from .manager import WebSocketManager
from .streams import StreamManager
from .events import WebSocketEvent, EventType

__all__ = [
    'WebSocketManager',
    'StreamManager',
    'WebSocketEvent',
    'EventType'
]