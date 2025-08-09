#!/usr/bin/env python3
"""
Прямой тест создания ордера с hedge mode конфигурацией
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# Устанавливаем переменные окружения
os.environ["PGPORT"] = "5555"
os.environ["PGUSER"] = "obertruper"
os.environ["PGDATABASE"] = "bot_trading_v3"


async def main():
    """Главная функция"""
    print("=== Прямой тест создания ордера с Hedge Mode ===\n")

    try:
        # Импортируем необходимые модули
        from database.connections import get_async_db
        from database.models.base_models import Order, SignalType
        from database.models.signal import Signal
        from trading.execution.executor import ExecutionEngine
        from trading.orders.order_manager import OrderManager
        from trading.positions.position_manager import PositionManager
        from trading.signals.signal_processor import SignalProcessor

        print("1️⃣ Создаем компоненты системы:")

        # Создаем менеджеры
        position_manager = PositionManager()
        execution_engine = ExecutionEngine()
        order_manager = OrderManager(execution_engine)
        signal_processor = SignalProcessor(order_manager)

        # Запускаем компоненты
        await position_manager.start()
        await execution_engine.start()
        await order_manager.start()
        await signal_processor.start()

        print("   ✅ Компоненты созданы и запущены")

        print("\n2️⃣ Создаем тестовый сигнал:")

        # Создаем сигнал
        async with get_async_db() as session:
            signal = Signal(
                symbol="BTCUSDT",
                exchange="bybit",
                signal_type=SignalType.LONG,
                strength=0.7,
                confidence=0.65,
                suggested_price=114000.0,
                suggested_quantity=0.001,
                strategy_name="DirectTest",
                extra_data={
                    "source": "direct_test",
                    "position_size_usd": 114.0,
                    "leverage": 5,
                },
            )

            session.add(signal)
            await session.commit()
            await session.refresh(signal)

            print(f"   ✅ Создан сигнал ID: {signal.id}")

        print("\n3️⃣ Обрабатываем сигнал:")

        # Обрабатываем сигнал напрямую
        orders = await signal_processor.process_signal(signal)

        if orders:
            print(f"   ✅ Создано ордеров: {len(orders)}")

            for order in orders:
                print("\n   Ордер:")
                print(f"   - ID: {order.order_id}")
                print(f"   - Symbol: {order.symbol}")
                print(f"   - Side: {order.side.value}")
                print(f"   - Quantity: {order.quantity}")
                print(f"   - Price: {order.price}")

                # Отправляем ордер на биржу
                print("\n4️⃣ Отправляем ордер на биржу:")

                try:
                    result = await order_manager.submit_order(order)
                    if result:
                        print("   ✅ Ордер успешно отправлен на биржу!")

                        # Проверяем статус в БД
                        async with get_async_db() as session:
                            db_order = await session.get(Order, order.id)
                            if db_order:
                                print(f"   Status: {db_order.status.value}")
                                print(f"   Exchange ID: {db_order.exchange_order_id}")

                                # Если ордер создан, отменяем его
                                if db_order.exchange_order_id:
                                    print("\n5️⃣ Отменяем тестовый ордер:")
                                    await asyncio.sleep(2)

                                    try:
                                        cancel_result = (
                                            await order_manager.cancel_order(db_order)
                                        )
                                        if cancel_result:
                                            print("   ✅ Ордер отменен")
                                    except Exception as e:
                                        print(f"   ⚠️ Ошибка отмены: {e}")
                    else:
                        print("   ❌ Ошибка отправки ордера")
                except Exception as e:
                    print(f"   ❌ Ошибка: {e}")
        else:
            print("   ❌ Ордера не созданы")

        print("\n6️⃣ Останавливаем компоненты:")

        await signal_processor.stop()
        await order_manager.stop()
        await execution_engine.stop()
        await position_manager.stop()

        print("   ✅ Все компоненты остановлены")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
