"""
Базовые интерфейсы для мульти-биржевой системы BOT_Trading v3.0

Содержит унифицированные интерфейсы для работы с различными криптовалютными биржами.
"""

from .exceptions import (
    APIError,
    AuthenticationError,
    ConnectionError,
    ExchangeError,
    InsufficientBalanceError,
    RateLimitError,
)
from .exchange_interface import BaseExchangeInterface, ExchangeCapabilities
from .models import (
    AccountInfo,
    Balance,
    ExchangeInfo,
    Instrument,
    Kline,
    Order,
    OrderBook,
    Position,
    Ticker,
)
from .order_types import (
    OrderRequest,
    OrderResponse,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionSide,
    TimeInForce,
)
from .websocket_base import BaseWebSocketClient, WebSocketMessage

__all__ = [
    # Interfaces
    "BaseExchangeInterface",
    "ExchangeCapabilities",
    # Models
    "Position",
    "Order",
    "Balance",
    "Instrument",
    "Ticker",
    "OrderBook",
    "Kline",
    "AccountInfo",
    "ExchangeInfo",
    # Order Types
    "OrderType",
    "OrderSide",
    "OrderStatus",
    "TimeInForce",
    "PositionSide",
    "OrderRequest",
    "OrderResponse",
    # Exceptions
    "ExchangeError",
    "ConnectionError",
    "AuthenticationError",
    "APIError",
    "RateLimitError",
    "InsufficientBalanceError",
    # WebSocket
    "BaseWebSocketClient",
    "WebSocketMessage",
]
