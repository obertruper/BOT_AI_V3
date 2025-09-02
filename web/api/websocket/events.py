"""WebSocket events module."""

from enum import Enum
from typing import Any

from pydantic import BaseModel


class EventType(Enum):
    """WebSocket event types."""

    # Connection events
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    ERROR = "error"

    # Trading events
    SIGNAL = "signal"
    ORDER = "order"
    POSITION = "position"
    TRADE = "trade"

    # Market data events
    TICKER = "ticker"
    ORDERBOOK = "orderbook"
    CANDLE = "candle"

    # System events
    STATUS = "status"
    METRICS = "metrics"
    LOG = "log"

    # ML events
    ML_PREDICTION = "ml_prediction"
    ML_SIGNAL = "ml_signal"


class WebSocketEvent(BaseModel):
    """WebSocket event model."""

    type: EventType
    data: dict[str, Any]
    timestamp: str | None = None
    client_id: str | None = None
