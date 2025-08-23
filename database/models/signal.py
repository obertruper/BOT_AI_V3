"""
Модель сигналов для базы данных
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

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
    signal_type: Mapped[SignalType] = mapped_column(Enum(SignalType), nullable=False, index=True)

    # Параметры сигнала
    strength: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Предлагаемые уровни
    suggested_price: Mapped[Decimal | None] = mapped_column(Float, nullable=True)
    suggested_stop_loss: Mapped[Decimal | None] = mapped_column(Float, nullable=True)
    suggested_take_profit: Mapped[Decimal | None] = mapped_column(Float, nullable=True)
    suggested_quantity: Mapped[Decimal | None] = mapped_column(Float, nullable=True)

    @property
    def suggested_position_size(self):
        """Alias для обратной совместимости"""
        return self.suggested_quantity

    @suggested_position_size.setter
    def suggested_position_size(self, value):
        """Сеттер для suggested_position_size"""
        self.suggested_quantity = value

    # Источник сигнала
    strategy_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timeframe: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Временные метки истечения
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Дополнительные данные
    indicators: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    signal_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, name="metadata"
    )

    # Статус и обработка
    status: Mapped[str | None] = mapped_column(String(20), nullable=True, default="active")
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Временные метки - created_at и updated_at наследуются от BaseModel

    def __repr__(self) -> str:
        return (
            f"<Signal(id={self.id}, symbol={self.symbol}, "
            f"type={self.signal_type.value}, strength={self.strength})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Преобразование в словарь"""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "signal_type": self.signal_type.value,
            "strength": float(self.strength) if self.strength else None,
            "confidence": float(self.confidence) if self.confidence else None,
            "suggested_price": float(self.suggested_price) if self.suggested_price else None,
            "suggested_stop_loss": (
                float(self.suggested_stop_loss) if self.suggested_stop_loss else None
            ),
            "suggested_take_profit": (
                float(self.suggested_take_profit) if self.suggested_take_profit else None
            ),
            "suggested_quantity": (
                float(self.suggested_quantity) if self.suggested_quantity else None
            ),
            "strategy_name": self.strategy_name,
            "timeframe": self.timeframe,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "indicators": self.indicators,
            "extra_data": self.extra_data,
            "metadata": self.signal_metadata,
            "status": self.status,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
