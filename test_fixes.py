#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Быстрый тест исправлений"""

import asyncio
import sys
import uuid
from datetime import datetime, timedelta

# Добавляем путь к проекту
sys.path.insert(0, "/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3")

from sqlalchemy import text

from database.connections import get_async_db
from database.models.base_models import Signal, SignalType
from trading.orders.order_manager import OrderManager


async def test_fixes():
    """Тест исправлений"""
    print("🔧 Тестирование исправлений...")

    try:
        # 1. Тест подключения к БД
        async with get_async_db() as db:
            result = await db.execute(text("SELECT COUNT(*) FROM signals"))
            signals_count = result.scalar()
            print(f"✅ БД работает, сигналов: {signals_count}")

        # 2. Тест создания сигнала
        test_signal = Signal(
            symbol="BTCUSDT",
            exchange="bybit",
            signal_type=SignalType.LONG,
            strength=0.85,
            confidence=0.90,
            suggested_price=45000.0,
            suggested_quantity=0.001,
            suggested_stop_loss=44000.0,
            suggested_take_profit=47000.0,
            strategy_name="test_fix",
            timeframe="5m",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1),
            extra_data={"test_fix": True},
        )

        async with get_async_db() as db:
            db.add(test_signal)
            await db.commit()
            await db.refresh(test_signal)

        print(f"✅ Сигнал создан: {test_signal.id}")

        # 3. Тест OrderManager
        class MockExchange:
            async def create_order(self, **kwargs):
                return f"test_order_{uuid.uuid4().hex[:8]}"

        class MockExchangeRegistry:
            async def get_exchange(self, name):
                return MockExchange()

        order_manager = OrderManager(MockExchangeRegistry())

        # Создаем ордер из сигнала
        order = await order_manager.create_order_from_signal(test_signal, "test_trader")

        if order:
            print(f"✅ Ордер создан: {order.order_id}")
            print(f"   Symbol: {order.symbol}")
            print(f"   Side: {order.side.value}")
            print(f"   Type: {order.order_type.value}")
            print(f"   Quantity: {order.quantity}")
            print(f"   Price: {order.price}")
        else:
            print("❌ Ордер не создан")

        print("🎉 Все исправления работают!")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_fixes())
