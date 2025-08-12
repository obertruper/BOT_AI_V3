"""
Репозиторий для работы с сигналами в БД
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError
from database.models.signal import Signal


class SignalRepository:
    """Репозиторий для работы с сигналами"""

    def __init__(self, db_session: AsyncSession):
        self.session = db_session

    async def get_active_signals(self, exchange: Optional[str] = None) -> List[Signal]:
        """Получает активные сигналы"""
        try:
            query = select(Signal).where(Signal.status == "active")
            if exchange:
                query = query.where(Signal.exchange == exchange)

            result = await self.session.execute(query)
            return result.scalars().all()
        except Exception as e:
            raise DatabaseError(f"Failed to get active signals: {e}")

    async def create_signal(self, signal_data: Dict[str, Any]) -> Signal:
        """Создает новый сигнал"""
        try:
            # Конвертируем indicators и extra_data в JSON строки
            if "indicators" in signal_data and isinstance(
                signal_data["indicators"], dict
            ):
                signal_data["indicators"] = json.dumps(signal_data["indicators"])
            if "extra_data" in signal_data and isinstance(
                signal_data["extra_data"], dict
            ):
                signal_data["extra_data"] = json.dumps(signal_data["extra_data"])

            signal = Signal(**signal_data)
            self.session.add(signal)
            await self.session.commit()
            await self.session.refresh(signal)
            return signal
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to create signal: {e}")

    async def mark_signal_processed(self, signal_id: int) -> None:
        """Отмечает сигнал как обработанный"""
        try:
            stmt = (
                update(Signal)
                .where(Signal.id == signal_id)
                .values(status="processed", processed_at=datetime.utcnow())
            )
            await self.session.execute(stmt)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to mark signal as processed: {e}")

    async def save_signal(self, signal) -> None:
        """Сохраняет сигнал в БД (совместимость с V2)"""
        try:
            # Если передан объект Signal, преобразуем в словарь
            if hasattr(signal, "__dict__") and not isinstance(signal, dict):
                # Преобразуем объект Signal в словарь
                signal_dict = {}
                for key, value in signal.__dict__.items():
                    if not key.startswith("_"):  # Игнорируем приватные атрибуты
                        # Особая обработка для enum signal_type
                        if key == "signal_type" and hasattr(value, "value"):
                            signal_dict[key] = value.value.upper()
                        else:
                            signal_dict[key] = value
                await self.create_signal(signal_dict)
            else:
                await self.create_signal(signal)
        except Exception as e:
            raise DatabaseError(f"Failed to save signal: {e}")
