"""
Базовые интерфейсы для мульти-биржевой системы BOT_Trading v3.0

Содержит унифицированные интерфейсы для работы с различными криптовалютными биржами.
"""

from .exchange_interface import BaseExchangeInterface, ExchangeCapabilities
from .models import (
    Position, Order, Balance, Instrument, Ticker, OrderBook, 
    Kline, AccountInfo, ExchangeInfo
)
from .order_types import (
    OrderType, OrderSide, OrderStatus, TimeInForce, 
    PositionSide, OrderRequest, OrderResponse
)
from .exceptions import (
    ExchangeError, ConnectionError, AuthenticationError, 
    APIError, RateLimitError, InsufficientBalanceError
)
from .websocket_base import BaseWebSocketClient, WebSocketMessage

__all__ = [
    # Interfaces
    'BaseExchangeInterface',
    'ExchangeCapabilities',
    
    # Models
    'Position',
    'Order', 
    'Balance',
    'Instrument',
    'Ticker',
    'OrderBook',
    'Kline',
    'AccountInfo',
    'ExchangeInfo',
    
    # Order Types
    'OrderType',
    'OrderSide', 
    'OrderStatus',
    'TimeInForce',
    'PositionSide',
    'OrderRequest',
    'OrderResponse',
    
    # Exceptions
    'ExchangeError',
    'ConnectionError',
    'AuthenticationError',
    'APIError', 
    'RateLimitError',
    'InsufficientBalanceError',
    
    # WebSocket
    'BaseWebSocketClient',
    'WebSocketMessage'
]