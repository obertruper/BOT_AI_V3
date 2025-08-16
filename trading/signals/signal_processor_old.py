#!/usr/bin/env python3
"""
Обработчик торговых сигналов

Принимает сигналы от стратегий, валидирует их и передает на исполнение.
"""

import asyncio
import logging
from datetime import datetime

from sqlalchemy import select

from database.connections import get_async_db
from database.models import Signal, SignalType


class SignalProcessor:
    """
    Процессор торговых сигналов

    Обеспечивает:
    - Валидацию сигналов
    - Проверку дубликатов
    - Приоритизацию сигналов
    - Передачу на исполнение
    """

    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger(__name__)
        self._active_signals: set[str] = set()
        self._signal_queue: asyncio.Queue = asyncio.Queue()
        self._processing = False

    async def process_signal(self, signal: Signal) -> bool:
        """
        Обработка торгового сигнала

        Args:
            signal: Торговый сигнал для обработки

        Returns:
            bool: True если сигнал принят к обработке
        """
        try:
            # Валидация сигнала
            if not self._validate_signal(signal):
                self.logger.warning(f"Невалидный сигнал: {signal}")
                return False

            # Проверка на дубликат
            signal_key = f"{signal.symbol}_{signal.exchange}_{signal.signal_type.value}"
            if signal_key in self._active_signals:
                self.logger.debug(f"Дубликат сигнала игнорирован: {signal_key}")
                return False

            # Добавляем в активные
            self._active_signals.add(signal_key)

            # Сохраняем в БД
            async with get_async_db() as db:
                db.add(signal)
                await db.commit()

            # Добавляем в очередь обработки
            await self._signal_queue.put(signal)

            self.logger.info(
                f"Сигнал принят: {signal.signal_type.value} для {signal.symbol} "
                f"на {signal.exchange} от {signal.strategy_name}"
            )

            return True

        except Exception as e:
            self.logger.error(f"Ошибка обработки сигнала: {e}")
            return False

    def _validate_signal(self, signal: Signal) -> bool:
        """Валидация торгового сигнала"""
        if not signal.symbol or not signal.exchange:
            return False

        if signal.signal_type == SignalType.NEUTRAL:
            return True  # Нейтральные сигналы всегда валидны

        # Проверка рекомендуемых параметров для торговых сигналов
        if signal.signal_type in [SignalType.LONG, SignalType.SHORT]:
            if not signal.suggested_quantity or signal.suggested_quantity <= 0:
                return False

        # Проверка силы и уверенности сигнала
        if signal.strength is not None:
            if not 0 <= signal.strength <= 1:
                return False

        if signal.confidence is not None:
            if not 0 <= signal.confidence <= 1:
                return False

        return True

    async def get_pending_signals(self) -> list[Signal]:
        """Получить необработанные сигналы из очереди"""
        signals = []

        # Извлекаем все сигналы из очереди
        while not self._signal_queue.empty():
            try:
                signal = self._signal_queue.get_nowait()
                signals.append(signal)
            except asyncio.QueueEmpty:
                break

        return signals

    async def mark_signal_processed(self, signal: Signal):
        """Отметить сигнал как обработанный"""
        signal_key = f"{signal.symbol}_{signal.exchange}_{signal.signal_type.value}"
        self._active_signals.discard(signal_key)

    async def get_active_signals_count(self) -> int:
        """Получить количество активных сигналов"""
        return len(self._active_signals)

    async def cleanup_expired_signals(self):
        """Очистка истекших сигналов"""
        current_time = datetime.utcnow()

        async with get_async_db() as db:
            # Находим истекшие сигналы
            result = await db.execute(select(Signal).where(Signal.expires_at < current_time))
            expired_signals = result.scalars().all()

            # Удаляем из активных
            for signal in expired_signals:
                signal_key = f"{signal.symbol}_{signal.exchange}_{signal.signal_type.value}"
                self._active_signals.discard(signal_key)

            self.logger.info(f"Очищено {len(expired_signals)} истекших сигналов")
