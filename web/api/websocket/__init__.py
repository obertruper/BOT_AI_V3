"""
WebSocket модуль для BOT_Trading v3.0

Real-time WebSocket соединения для торгового интерфейса:
- manager: WebSocket менеджер подключений
- streams: Потоки данных (трейдеры, сделки, метрики)
- events: Типы и обработка событий
"""

from .events import EventType, WebSocketEvent
from .manager import WebSocketManager
from .streams import StreamManager

__all__ = ["WebSocketManager", "StreamManager", "WebSocketEvent", "EventType"]
