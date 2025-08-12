"""
Исправленный репозиторий для работы с сигналами в БД
Решает проблему дублирования сигналов
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError
from core.logger import setup_logger
from database.models.signal import Signal

logger = setup_logger(__name__)


class SignalRepositoryFixed:
    """Репозиторий для работы с сигналами с защитой от дублирования"""

    def __init__(self, db_session: AsyncSession):
        self.session = db_session

        # Время жизни хеша сигнала (для предотвращения дублирования)
        self.signal_hash_ttl = timedelta(minutes=5)

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

    def _generate_signal_hash(self, signal_data: Dict[str, Any]) -> str:
        """
        Генерирует уникальный хеш для сигнала
        Основан на symbol, signal_type, timeframe и временном окне
        """
        # Ключевые поля для идентификации уникальности
        hash_data = {
            "symbol": signal_data.get("symbol"),
            "signal_type": str(signal_data.get("signal_type")),
            "strategy_name": signal_data.get("strategy_name"),
            "timeframe": signal_data.get("timeframe", "15m"),
            # Округляем время до 5-минутного интервала для группировки
            "time_window": int(datetime.now(timezone.utc).timestamp() // 300),
        }

        # Создаем хеш
        hash_string = json.dumps(hash_data, sort_keys=True)
        return hashlib.md5(hash_string.encode()).hexdigest()

    async def create_signal(self, signal_data: Dict[str, Any]) -> Optional[Signal]:
        """
        Создает новый сигнал с проверкой на дублирование
        """
        try:
            # Генерируем хеш для проверки дублирования
            signal_hash = self._generate_signal_hash(signal_data)

            # Проверяем, существует ли уже такой сигнал
            existing = await self._check_existing_signal(
                signal_data.get("symbol"), signal_hash
            )

            if existing:
                logger.debug(
                    f"🔄 Сигнал для {signal_data.get('symbol')} уже существует, пропускаем"
                )
                return None

            # Конвертируем indicators и extra_data в JSON строки
            if "indicators" in signal_data and isinstance(
                signal_data["indicators"], dict
            ):
                signal_data["indicators"] = json.dumps(signal_data["indicators"])
            if "extra_data" in signal_data and isinstance(
                signal_data["extra_data"], dict
            ):
                signal_data["extra_data"] = json.dumps(signal_data["extra_data"])

            # Добавляем хеш в метаданные
            if "signal_metadata" in signal_data:
                if isinstance(signal_data["signal_metadata"], dict):
                    signal_data["signal_metadata"]["hash"] = signal_hash
                    signal_data["signal_metadata"] = json.dumps(
                        signal_data["signal_metadata"]
                    )
            else:
                signal_data["signal_metadata"] = json.dumps({"hash": signal_hash})

            # Создаем новый сигнал простым INSERT
            signal = Signal(**signal_data)
            self.session.add(signal)

            # Коммитим изменения
            await self.session.commit()
            await self.session.refresh(signal)

            logger.info(
                f"✅ Сигнал для {signal.symbol} (тип: {signal.signal_type}) создан или обновлен"
            )
            return signal

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка создания сигнала: {e}")
            # Не поднимаем исключение, возвращаем None для совместимости
            return None

    async def _check_existing_signal(self, symbol: str, signal_hash: str) -> bool:
        """
        Проверяет, существует ли уже такой сигнал
        """
        try:
            # Время окна для проверки дублирования
            time_window = datetime.now(timezone.utc) - self.signal_hash_ttl

            # Ищем сигналы с таким же хешем за последние 5 минут
            query = select(Signal).where(
                and_(
                    Signal.symbol == symbol,
                    Signal.created_at >= time_window,
                    Signal.signal_metadata.op("->>")("hash") == signal_hash,
                )
            )

            result = await self.session.execute(query)
            existing = result.scalar_one_or_none()

            return existing is not None

        except Exception as e:
            # Если произошла ошибка, считаем что сигнала нет
            logger.debug(f"Ошибка проверки существующего сигнала: {e}")
            return False

    async def create_signal_safe(self, signal_data: Dict[str, Any]) -> Optional[Signal]:
        """
        Безопасное создание сигнала с использованием upsert
        """
        try:
            # Генерируем хеш
            signal_hash = self._generate_signal_hash(signal_data)

            # Подготавливаем данные
            if "indicators" in signal_data and isinstance(
                signal_data["indicators"], dict
            ):
                signal_data["indicators"] = json.dumps(signal_data["indicators"])
            if "extra_data" in signal_data and isinstance(
                signal_data["extra_data"], dict
            ):
                signal_data["extra_data"] = json.dumps(signal_data["extra_data"])

            # Добавляем хеш
            metadata = signal_data.get("signal_metadata", {})
            if isinstance(metadata, dict):
                metadata["hash"] = signal_hash
                signal_data["signal_metadata"] = json.dumps(metadata)

            # Используем INSERT ON CONFLICT DO NOTHING
            stmt = insert(Signal).values(**signal_data)

            # Если есть конфликт по (symbol, created_at), не делаем ничего
            stmt = stmt.on_conflict_do_nothing(index_elements=["symbol", "created_at"])

            result = await self.session.execute(stmt)
            await self.session.commit()

            if result.rowcount > 0:
                # Сигнал был создан
                logger.info(f"✅ Создан новый сигнал для {signal_data.get('symbol')}")

                # Получаем созданный сигнал
                query = (
                    select(Signal)
                    .where(
                        and_(
                            Signal.symbol == signal_data.get("symbol"),
                            Signal.signal_metadata.op("->>")("hash") == signal_hash,
                        )
                    )
                    .order_by(Signal.created_at.desc())
                    .limit(1)
                )

                result = await self.session.execute(query)
                return result.scalar_one_or_none()
            else:
                # Сигнал уже существовал
                logger.debug(
                    f"🔄 Сигнал для {signal_data.get('symbol')} уже существует"
                )
                return None

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка безопасного создания сигнала: {e}")
            return None

    async def mark_signal_processed(self, signal_id: int) -> None:
        """Отмечает сигнал как обработанный"""
        try:
            stmt = (
                update(Signal)
                .where(Signal.id == signal_id)
                .values(status="processed", processed_at=datetime.now(timezone.utc))
            )
            await self.session.execute(stmt)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to mark signal as processed: {e}")

    async def save_signal(self, signal) -> Optional[Signal]:
        """
        Сохраняет сигнал в БД с проверкой на дублирование
        """
        try:
            # Если передан объект Signal, преобразуем в словарь
            if hasattr(signal, "__dict__") and not isinstance(signal, dict):
                signal_dict = {}
                for key, value in signal.__dict__.items():
                    if not key.startswith("_"):  # Игнорируем приватные атрибуты
                        # Особая обработка для enum signal_type
                        if key == "signal_type" and hasattr(value, "value"):
                            signal_dict[key] = value.value.upper()
                        else:
                            signal_dict[key] = value
                return await self.create_signal(signal_dict)
            else:
                return await self.create_signal(signal)
        except Exception as e:
            logger.error(f"Ошибка сохранения сигнала: {e}")
            return None

    async def cleanup_old_signals(self, hours: int = 24) -> int:
        """
        Удаляет старые обработанные сигналы

        Args:
            hours: Количество часов для хранения сигналов

        Returns:
            Количество удаленных сигналов
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            # Удаляем старые обработанные сигналы
            query = select(Signal).where(
                and_(Signal.status == "processed", Signal.created_at < cutoff_time)
            )

            result = await self.session.execute(query)
            old_signals = result.scalars().all()

            for signal in old_signals:
                await self.session.delete(signal)

            await self.session.commit()

            if len(old_signals) > 0:
                logger.info(f"🗑️ Удалено {len(old_signals)} старых сигналов")

            return len(old_signals)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка очистки старых сигналов: {e}")
            return 0
