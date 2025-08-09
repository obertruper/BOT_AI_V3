"""
Модель сигналов для базы данных
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import JSON, DateTime, Enum, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base_models import BaseModel, SignalType


class Signal(BaseModel):
    """Модель торгового сигнала"""

    __tablename__ = "signals"
    __table_args__ = {"extend_existing": True}

    # ID автоматически наследуется от BaseModel

    # Основные поля
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(50), nullable=False)
    signal_type: Mapped[SignalType] = mapped_column(
        Enum(SignalType), nullable=False, index=True
    )

    # Параметры сигнала
    strength: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Предлагаемые уровни
    suggested_price: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)
    suggested_stop_loss: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)
    suggested_take_profit: Mapped[Optional[Decimal]] = mapped_column(
        Float, nullable=True
    )
    suggested_quantity: Mapped[Optional[Decimal]] = mapped_column(Float, nullable=True)

    @property
    def suggested_position_size(self):
        """Alias для обратной совместимости"""
        return self.suggested_quantity

    # Источник сигнала
    strategy_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    timeframe: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Временные метки истечения
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Дополнительные данные
    indicators: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    extra_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    signal_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True, name="metadata"
    )

    # Временные метки - created_at и updated_at наследуются от BaseModel

    def __repr__(self) -> str:
        return (
            f"<Signal(id={self.id}, symbol={self.symbol}, "
            f"type={self.signal_type.value}, strength={self.strength})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "signal_type": self.signal_type.value,
            "strength": float(self.strength) if self.strength else None,
            "confidence": float(self.confidence) if self.confidence else None,
            "suggested_price": float(self.suggested_price)
            if self.suggested_price
            else None,
            "suggested_stop_loss": (
                float(self.suggested_stop_loss) if self.suggested_stop_loss else None
            ),
            "suggested_take_profit": (
                float(self.suggested_take_profit)
                if self.suggested_take_profit
                else None
            ),
            "suggested_quantity": (
                float(self.suggested_quantity) if self.suggested_quantity else None
            ),
            "strategy_name": self.strategy_name,
            "metadata": self.signal_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
