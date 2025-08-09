#!/usr/bin/env python3
"""
Тест ML сигнала с hedge mode конфигурацией
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
    print("=== Тест ML сигнала с Hedge Mode ===\n")

    try:
        # Импортируем необходимые модули
        from sqlalchemy import select

        # Инициализируем соединение с БД
        from database.connections import get_async_db
        from database.models.base_models import SignalType
        from database.models.signal import Signal
        from trading.engine import TradingEngine

        print("1️⃣ Создаем ML сигнал в БД:")

        # Создаем новый сигнал
        async with get_async_db() as session:
            # Проверяем есть ли уже сигналы
            result = await session.execute(
                select(Signal).order_by(Signal.created_at.desc()).limit(5)
            )
            existing_signals = result.scalars().all()

            print(f"   Найдено существующих сигналов: {len(existing_signals)}")

            # Создаем новый тестовый ML сигнал
            new_signal = Signal(
                symbol="BTCUSDT",
                exchange="bybit",
                signal_type=SignalType.LONG,
                strength=0.7,
                confidence=0.65,
                suggested_price=114000.0,  # Примерная текущая цена
                suggested_quantity=0.001,  # Минимальный размер
                strategy_name="MLSignalStrategy",
                extra_data={
                    "source": "ml_test",
                    "position_size_usd": 114.0,
                    "ml_predictions": {
                        "direction": "up",
                        "confidence": 0.65,
                        "volatility": 0.02,
                    },
                },
            )

            session.add(new_signal)
            await session.commit()
            await session.refresh(new_signal)

            print(f"   ✅ Создан сигнал ID: {new_signal.id}")
            print(f"   Symbol: {new_signal.symbol}")
            print(f"   Type: {new_signal.signal_type.value}")
            print(f"   Strength: {new_signal.strength}")
            print(f"   Confidence: {new_signal.confidence}")

        print("\n2️⃣ Инициализируем Trading Engine:")

        # Создаем конфигурацию
        config = {
            "risk_management": {
                "max_position_size": 1000,
                "max_open_positions": 5,
                "risk_per_trade": 0.02,
            },
            "signal_processing": {
                "confidence_threshold": 0.5,
                "min_signal_strength": 0.3,
            },
        }

        # Создаем Trading Engine
        engine = TradingEngine(config)
        await engine.start()

        print("   ✅ Trading Engine запущен")

        print("\n3️⃣ Обрабатываем ML сигнал:")

        # Даем время на обработку сигнала
        await asyncio.sleep(5)

        print("\n4️⃣ Проверяем созданные ордера:")

        # Проверяем ордера в БД
        from database.models.base_models import Order

        async with get_async_db() as session:
            result = await session.execute(
                select(Order)
                .where(
                    Order.extra_data.op("->>")("signal_id").cast(
                        type_=type(new_signal.id)
                    )
                    == new_signal.id
                )
                .order_by(Order.created_at.desc())
            )
            orders = result.scalars().all()

            if orders:
                print(f"   ✅ Найдено ордеров: {len(orders)}")
                for order in orders:
                    print(f"\n   Ордер ID: {order.order_id}")
                    print(f"   Symbol: {order.symbol}")
                    print(f"   Side: {order.side.value}")
                    print(f"   Quantity: {order.quantity}")
                    print(f"   Price: {order.price}")
                    print(f"   Status: {order.status.value}")
                    print(f"   Exchange ID: {order.exchange_order_id}")

                    # Проверяем leverage из extra_data
                    if order.extra_data and "leverage" in order.extra_data:
                        print(f"   Leverage: {order.extra_data['leverage']}x")
            else:
                print("   ❌ Ордера не найдены")

                # Проверяем был ли сигнал обработан
                async with get_async_db() as session:
                    result = await session.execute(
                        select(Signal).where(Signal.id == new_signal.id)
                    )
                    signal = result.scalar_one()
                    print(f"\n   Статус сигнала: {signal.status}")
                    print(f"   Processed: {signal.processed}")

        print("\n5️⃣ Останавливаем систему:")

        await engine.stop()

        print("   ✅ Система остановлена")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
