#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Менеджер позиций

Управляет открытыми позициями, расчетом PnL и риск-метрик.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from database.models import OrderSide, Trade


@dataclass
class Position:
    """Открытая позиция"""

    symbol: str
    exchange: str
    side: str  # 'long' или 'short'
    quantity: Decimal = Decimal("0")
    entry_price: Decimal = Decimal("0")
    current_price: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    fees_paid: Decimal = Decimal("0")
    opened_at: datetime = field(default_factory=datetime.utcnow)
    trades: List[Trade] = field(default_factory=list)

    @property
    def total_pnl(self) -> Decimal:
        """Общий PnL (реализованный + нереализованный)"""
        return self.realized_pnl + self.unrealized_pnl

    @property
    def pnl_percentage(self) -> Decimal:
        """PnL в процентах"""
        if self.entry_price == 0:
            return Decimal("0")
        return ((self.current_price - self.entry_price) / self.entry_price) * 100

    @property
    def value(self) -> Decimal:
        """Текущая стоимость позиции"""
        return self.quantity * self.current_price


class PositionManager:
    """
    Менеджер управления позициями

    Обеспечивает:
    - Отслеживание открытых позиций
    - Расчет PnL в реальном времени
    - Управление частичным закрытием
    - Расчет риск-метрик
    """

    def __init__(self, exchange_registry, logger: Optional[logging.Logger] = None):
        self.exchange_registry = exchange_registry
        self.logger = logger or logging.getLogger(__name__)
        self._positions: Dict[str, Position] = {}  # key: f"{exchange}_{symbol}"
        self._position_locks: Dict[str, asyncio.Lock] = {}

    async def open_position(self, trade: Trade) -> Position:
        """
        Открытие или добавление к позиции

        Args:
            trade: Исполненная сделка

        Returns:
            Position: Обновленная позиция
        """
        position_key = f"{trade.exchange}_{trade.symbol}"

        # Получаем или создаем lock
        if position_key not in self._position_locks:
            self._position_locks[position_key] = asyncio.Lock()

        async with self._position_locks[position_key]:
            if position_key in self._positions:
                # Обновляем существующую позицию
                position = self._positions[position_key]
                await self._update_position(position, trade)
            else:
                # Создаем новую позицию
                position = await self._create_position(trade)
                self._positions[position_key] = position

            self.logger.info(
                f"Позиция обновлена: {position.symbol} на {position.exchange}, "
                f"количество: {position.quantity}, средняя цена: {position.entry_price}"
            )

            return position

    async def close_position(
        self, exchange: str, symbol: str, quantity: Optional[Decimal] = None
    ) -> Optional[Position]:
        """
        Закрытие позиции (полное или частичное)

        Args:
            exchange: Биржа
            symbol: Символ
            quantity: Количество для закрытия (None = полное закрытие)

        Returns:
            Position или None если позиция не найдена
        """
        position_key = f"{exchange}_{symbol}"
        position = self._positions.get(position_key)

        if not position:
            self.logger.warning(f"Позиция {symbol} на {exchange} не найдена")
            return None

        async with self._position_locks[position_key]:
            if quantity is None or quantity >= position.quantity:
                # Полное закрытие
                final_position = self._positions.pop(position_key)
                self._position_locks.pop(position_key, None)

                self.logger.info(
                    f"Позиция закрыта: {symbol} на {exchange}, "
                    f"итоговый PnL: {final_position.total_pnl}"
                )

                return final_position
            else:
                # Частичное закрытие
                position.quantity -= quantity

                # Пересчитываем PnL
                await self._recalculate_position(position)

                self.logger.info(
                    f"Частичное закрытие позиции: {symbol} на {exchange}, "
                    f"закрыто: {quantity}, осталось: {position.quantity}"
                )

                return position

    async def update_prices(self):
        """Обновление текущих цен для всех позиций"""
        tasks = []

        for position_key, position in self._positions.items():
            task = self._update_position_price(position)
            tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def get_position(self, exchange: str, symbol: str) -> Optional[Position]:
        """Получить позицию"""
        position_key = f"{exchange}_{symbol}"
        return self._positions.get(position_key)

    async def get_all_positions(self, exchange: Optional[str] = None) -> List[Position]:
        """Получить все открытые позиции"""
        positions = list(self._positions.values())

        if exchange:
            positions = [p for p in positions if p.exchange == exchange]

        return positions

    async def get_total_exposure(
        self, exchange: Optional[str] = None
    ) -> Dict[str, Decimal]:
        """Получить общую экспозицию"""
        long_exposure = Decimal("0")
        short_exposure = Decimal("0")

        positions = await self.get_all_positions(exchange)

        for position in positions:
            if position.side == "long":
                long_exposure += position.value
            else:
                short_exposure += position.value

        return {
            "long": long_exposure,
            "short": short_exposure,
            "net": long_exposure - short_exposure,
            "total": long_exposure + short_exposure,
        }

    async def get_portfolio_pnl(
        self, exchange: Optional[str] = None
    ) -> Dict[str, Decimal]:
        """Получить общий PnL портфеля"""
        realized = Decimal("0")
        unrealized = Decimal("0")

        positions = await self.get_all_positions(exchange)

        for position in positions:
            realized += position.realized_pnl
            unrealized += position.unrealized_pnl

        return {
            "realized": realized,
            "unrealized": unrealized,
            "total": realized + unrealized,
        }

    async def _create_position(self, trade: Trade) -> Position:
        """Создание новой позиции из сделки"""
        side = "long" if trade.side == OrderSide.BUY else "short"

        position = Position(
            symbol=trade.symbol,
            exchange=trade.exchange,
            side=side,
            quantity=Decimal(str(trade.quantity)),
            entry_price=Decimal(str(trade.price)),
            current_price=Decimal(str(trade.price)),
            fees_paid=Decimal(str(trade.commission or 0)),
            trades=[trade],
        )

        return position

    async def _update_position(self, position: Position, trade: Trade):
        """Обновление существующей позиции"""
        trade_quantity = Decimal(str(trade.quantity))
        trade_price = Decimal(str(trade.price))
        trade_fee = Decimal(str(trade.commission or 0))

        # Определяем направление сделки
        is_opening = (position.side == "long" and trade.side == OrderSide.BUY) or (
            position.side == "short" and trade.side == OrderSide.SELL
        )

        if is_opening:
            # Добавление к позиции
            total_value = (
                position.quantity * position.entry_price + trade_quantity * trade_price
            )
            position.quantity += trade_quantity
            position.entry_price = (
                total_value / position.quantity
                if position.quantity > 0
                else Decimal("0")
            )
        else:
            # Частичное закрытие
            close_quantity = min(trade_quantity, position.quantity)

            # Расчет реализованного PnL
            if position.side == "long":
                pnl = (trade_price - position.entry_price) * close_quantity
            else:
                pnl = (position.entry_price - trade_price) * close_quantity

            position.realized_pnl += pnl
            position.quantity -= close_quantity

        # Обновляем комиссии и добавляем сделку
        position.fees_paid += trade_fee
        position.trades.append(trade)

        # Обновляем нереализованный PnL
        await self._recalculate_position(position)

    async def _update_position_price(self, position: Position):
        """Обновление текущей цены позиции"""
        try:
            exchange = await self.exchange_registry.get_exchange(position.exchange)
            if not exchange:
                return

            ticker = await exchange.get_ticker(position.symbol)
            if ticker and "last" in ticker:
                position.current_price = Decimal(str(ticker["last"]))

                # Пересчитываем нереализованный PnL
                if position.side == "long":
                    position.unrealized_pnl = (
                        position.current_price - position.entry_price
                    ) * position.quantity
                else:
                    position.unrealized_pnl = (
                        position.entry_price - position.current_price
                    ) * position.quantity

        except Exception as e:
            self.logger.error(f"Ошибка обновления цены для {position.symbol}: {e}")

    async def _recalculate_position(self, position: Position):
        """Пересчет метрик позиции"""
        # Обновляем текущую цену
        await self._update_position_price(position)

        # Пересчитываем средние цены если нужно
        if position.trades:
            total_quantity = Decimal("0")
            total_value = Decimal("0")

            for trade in position.trades:
                if (position.side == "long" and trade.side == OrderSide.BUY) or (
                    position.side == "short" and trade.side == OrderSide.SELL
                ):
                    total_quantity += Decimal(str(trade.quantity))
                    total_value += Decimal(str(trade.quantity)) * Decimal(
                        str(trade.price)
                    )

            if total_quantity > 0:
                position.entry_price = total_value / total_quantity

    async def sync_with_exchange(self, exchange_name: str):
        """Синхронизация позиций с биржей"""
        try:
            exchange = await self.exchange_registry.get_exchange(exchange_name)
            if not exchange:
                return

            # Получаем позиции с биржи
            exchange_positions = await exchange.get_positions()

            # Обновляем наши позиции
            for ex_pos in exchange_positions:
                position_key = f"{exchange_name}_{ex_pos['symbol']}"

                if position_key in self._positions:
                    # Обновляем существующую
                    position = self._positions[position_key]
                    position.quantity = Decimal(str(ex_pos["contracts"]))
                    position.current_price = Decimal(str(ex_pos["markPrice"]))
                    position.unrealized_pnl = Decimal(
                        str(ex_pos.get("unrealizedPnl", 0))
                    )

                else:
                    # Создаем новую позицию из данных биржи
                    position = Position(
                        symbol=ex_pos["symbol"],
                        exchange=exchange_name,
                        side=ex_pos["side"],
                        quantity=Decimal(str(ex_pos["contracts"])),
                        entry_price=Decimal(str(ex_pos["avgPrice"])),
                        current_price=Decimal(str(ex_pos["markPrice"])),
                        unrealized_pnl=Decimal(str(ex_pos.get("unrealizedPnl", 0))),
                    )
                    self._positions[position_key] = position
                    self._position_locks[position_key] = asyncio.Lock()

        except Exception as e:
            self.logger.error(f"Ошибка синхронизации позиций с {exchange_name}: {e}")

    async def sync_positions(self):
        """Синхронизация позиций со всеми подключенными биржами"""
        if not self.exchange_registry:
            self.logger.warning(
                "Exchange registry не доступен для синхронизации позиций"
            )
            return

        try:
            # Получаем список активных бирж
            active_exchanges = await self.exchange_registry.get_active_exchanges()

            for exchange_name in active_exchanges:
                await self.sync_with_exchange(exchange_name)

        except Exception as e:
            self.logger.error(f"Ошибка синхронизации позиций: {e}")

    async def calculate_total_pnl(self) -> Decimal:
        """Расчет общего PnL всех позиций"""
        try:
            total_pnl = Decimal("0")

            for position in self._positions.values():
                total_pnl += position.total_pnl

            return total_pnl

        except Exception as e:
            self.logger.error(f"Ошибка расчета общего PnL: {e}")
            return Decimal("0")

    async def health_check(self) -> bool:
        """Проверка здоровья компонента"""
        return True

    async def start(self):
        """Запуск компонента"""
        self.logger.info("Position Manager запущен")

    async def stop(self):
        """Остановка компонента"""
        self.logger.info("Position Manager остановлен")

    def is_running(self) -> bool:
        """Проверка работы компонента"""
        return True
