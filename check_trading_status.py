# \!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка статуса торговой системы
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from datetime import datetime, timedelta

from sqlalchemy import func, select

from database.connections import get_async_db
from database.models.signals import Signal
from database.models.trading import Order, Position, Trade


async def check_trading_status():
    """Проверяет статус торговой системы"""

    print("🔍 Проверка статуса торговой системы...\n")

    async with get_async_db() as db:
        # 1. Проверяем последние сигналы
        recent_signals_stmt = (
            select(Signal)
            .where(Signal.created_at >= datetime.utcnow() - timedelta(hours=1))
            .order_by(Signal.created_at.desc())
            .limit(10)
        )
        result = await db.execute(recent_signals_stmt)
        recent_signals = result.scalars().all()

        print(f"📊 Последние сигналы (за час): {len(recent_signals)}")
        for signal in recent_signals[:5]:
            print(
                f"   {signal.created_at}: {signal.symbol} - {signal.signal_type} (confidence: {signal.confidence:.2f})"
            )

        # 2. Проверяем последние ордера
        recent_orders_stmt = (
            select(Order)
            .where(Order.created_at >= datetime.utcnow() - timedelta(hours=1))
            .order_by(Order.created_at.desc())
            .limit(10)
        )
        result = await db.execute(recent_orders_stmt)
        recent_orders = result.scalars().all()

        print(f"\n📈 Последние ордера (за час): {len(recent_orders)}")
        for order in recent_orders[:5]:
            print(
                f"   {order.created_at}: {order.symbol} - {order.side} {order.quantity} @ {order.price} (status: {order.status})"
            )

        # 3. Проверяем открытые позиции
        open_positions_stmt = select(Position).where(Position.status == "open")
        result = await db.execute(open_positions_stmt)
        open_positions = result.scalars().all()

        print(f"\n💰 Открытые позиции: {len(open_positions)}")
        for pos in open_positions:
            print(f"   {pos.symbol}: {pos.side} {pos.quantity} @ {pos.entry_price}")

        # 4. Статистика
        total_signals = await db.scalar(select(func.count(Signal.id)))
        total_orders = await db.scalar(select(func.count(Order.id)))
        total_trades = await db.scalar(select(func.count(Trade.id)))

        print("\n📊 Общая статистика:")
        print(f"   Всего сигналов: {total_signals}")
        print(f"   Всего ордеров: {total_orders}")
        print(f"   Всего сделок: {total_trades}")


if __name__ == "__main__":
    asyncio.run(check_trading_status())
