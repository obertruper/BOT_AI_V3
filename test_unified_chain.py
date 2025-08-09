#!/usr/bin/env python3
"""
Тест полной цепочки: ML сигнал → UnifiedSignalProcessor → Order → Exchange
"""

import asyncio
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

# Устанавливаем переменные окружения
os.environ["PGPORT"] = "5555"
os.environ["PGUSER"] = "obertruper"
os.environ["PGDATABASE"] = "bot_trading_v3"


async def test_unified_chain():
    """Тестирование унифицированной цепочки обработки сигналов"""

    print(f"\n🔧 ТЕСТ УНИФИЦИРОВАННОЙ ЦЕПОЧКИ - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 70)

    try:
        # 1. Инициализация компонентов
        print("\n1️⃣ ИНИЦИАЛИЗАЦИЯ КОМПОНЕНТОВ:")

        from core.signals.unified_signal_processor import UnifiedSignalProcessor
        from database.connections.postgres import AsyncPGPool
        from ml.ml_manager import MLManager
        from trading.order_executor import OrderExecutor

        # Инициализируем ML менеджер
        ml_config = {"model_path": "models/saved", "device": "cpu"}
        ml_manager = MLManager(ml_config)
        await ml_manager.initialize()
        print("   ✅ ML Manager инициализирован")

        # Инициализируем OrderExecutor
        order_executor = OrderExecutor()
        await order_executor.initialize()
        print("   ✅ OrderExecutor инициализирован")

        # Создаем UnifiedSignalProcessor
        processor_config = {
            "min_confidence_threshold": 0.3,
            "max_daily_trades": 100,
            "position_size": 0.0001,  # Минимальный размер для BTC
            "exchange": "bybit",
        }

        signal_processor = UnifiedSignalProcessor(
            ml_manager=ml_manager,
            trading_engine=None,  # Пока без trading engine
            config=processor_config,
        )
        print("   ✅ UnifiedSignalProcessor создан")

        # 2. Получаем рыночные данные
        print("\n2️⃣ ПОЛУЧЕНИЕ РЫНОЧНЫХ ДАННЫХ:")

        pool = await AsyncPGPool.get_pool()

        # Получаем последние данные по BTCUSDT
        market_data_query = """
        SELECT * FROM raw_market_data
        WHERE symbol = 'BTCUSDT'
        AND interval_minutes = 15
        ORDER BY datetime DESC
        LIMIT 100
        """

        candles = await pool.fetch(market_data_query)

        if not candles:
            print("   ❌ Нет рыночных данных!")
            return

        current_price = float(candles[0]["close"])
        print(f"   ✅ Загружено {len(candles)} свечей")
        print(f"   💰 Текущая цена BTCUSDT: ${current_price:,.2f}")

        # Подготавливаем данные для ML
        market_data = {
            "symbol": "BTCUSDT",
            "current_price": current_price,
            "candles": candles,
        }

        # 3. Генерируем ML сигнал
        print("\n3️⃣ ГЕНЕРАЦИЯ ML СИГНАЛА:")

        # Обрабатываем через UnifiedSignalProcessor
        order = await signal_processor.process_ml_prediction("BTCUSDT", market_data)

        if order:
            print("   ✅ Создан ордер:")
            print(f"      Символ: {order.symbol}")
            print(f"      Сторона: {order.side}")
            print(f"      Количество: {order.quantity}")
            print(f"      Цена: ${order.price:,.2f}")
            print(f"      ID: {order.id}")

            # 4. Исполняем ордер
            print("\n4️⃣ ИСПОЛНЕНИЕ ОРДЕРА:")

            success = await order_executor.execute_order(order)

            if success:
                print("   ✅ Ордер успешно исполнен!")
            else:
                print("   ❌ Ордер отклонен")

                # Проверяем причину
                rejected_info = await pool.fetchrow(
                    """
                    SELECT status, metadata
                    FROM orders
                    WHERE id = $1
                """,
                    order.id,
                )

                if rejected_info:
                    print(f"   📋 Статус: {rejected_info['status']}")
                    print(
                        f"   📋 Причина: {rejected_info['metadata'].get('error_message', 'Не указана')}"
                    )

        else:
            print("   ⚠️ Сигнал не сгенерирован (возможно NEUTRAL)")

        # 5. Показываем статистику
        print("\n5️⃣ СТАТИСТИКА:")

        processor_stats = await signal_processor.get_stats()
        print("   📊 SignalProcessor:")
        print(f"      Обработано сигналов: {processor_stats['signals_processed']}")
        print(f"      Создано ордеров: {processor_stats['orders_created']}")
        print(f"      Ошибок: {processor_stats['errors_count']}")

        executor_stats = await order_executor.get_stats()
        print("   📊 OrderExecutor:")
        print(f"      Исполнено: {executor_stats['executed_count']}")
        print(f"      Отклонено: {executor_stats['rejected_count']}")
        print(f"      Подключенные биржи: {executor_stats['connected_exchanges']}")

        # 6. Проверяем последние ордера
        print("\n6️⃣ ПОСЛЕДНИЕ ОРДЕРА:")

        recent_orders = await pool.fetch(
            """
            SELECT id, symbol, side, quantity, price, status, created_at
            FROM orders
            WHERE created_at > NOW() - INTERVAL '1 hour'
            ORDER BY created_at DESC
            LIMIT 5
        """
        )

        for order in recent_orders:
            icon = (
                "✅"
                if order["status"] == "OPEN"
                else "❌"
                if order["status"] == "REJECTED"
                else "⏳"
            )
            print(
                f"   {icon} #{order['id']}: {order['symbol']} {order['side']} "
                f"{order['quantity']} @ ${order['price']:,.2f} - {order['status']}"
            )

        await AsyncPGPool.close_pool()

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_unified_chain())
