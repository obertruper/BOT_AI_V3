#!/usr/bin/env python3
"""
Прямой тест потока сигнал -> ордер без запуска всей системы
"""

import asyncio
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# Устанавливаем переменные окружения
os.environ["PGPORT"] = "5555"
os.environ["PGUSER"] = "obertruper"
os.environ["PGDATABASE"] = "bot_trading_v3"

from core.config.config_manager import ConfigManager
from database.models.base_models import SignalType

# Импортируем компоненты
from database.models.signal import Signal
from exchanges.registry import ExchangeRegistry
from trading.execution.executor import ExecutionEngine
from trading.orders.order_manager import OrderManager
from trading.signals.signal_processor import SignalProcessor


async def main():
    """Главная функция теста"""
    print("=" * 80)
    print("🧪 ПРЯМОЙ ТЕСТ: СИГНАЛ → ОРДЕР")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    config_manager = ConfigManager()
    config = config_manager.get_config()

    try:
        # 1. Инициализируем компоненты
        print("\n1️⃣ Инициализация компонентов...")

        # Exchange Registry
        exchange_registry = ExchangeRegistry()
        await exchange_registry.initialize()
        print("✅ Exchange Registry инициализирован")

        # Order Manager
        order_manager = OrderManager(exchange_registry)
        await order_manager.start()
        print("✅ Order Manager запущен")

        # Signal Processor
        signal_processor = SignalProcessor(
            config=config.get("signal_processing", {}),
            exchange_registry=exchange_registry,
            order_manager=order_manager,
        )
        await signal_processor.start()
        print("✅ Signal Processor запущен")

        # Execution Engine
        execution_engine = ExecutionEngine(
            order_manager=order_manager, exchange_registry=exchange_registry
        )
        await execution_engine.start()
        print("✅ Execution Engine запущен")

        # 2. Получаем текущую цену BTC
        print("\n2️⃣ Получение текущей цены BTC...")
        from exchanges.factory import ExchangeFactory

        factory = ExchangeFactory()
        exchange = await factory.create_and_connect(
            exchange_type="bybit",
            api_key=os.getenv("BYBIT_API_KEY"),
            api_secret=os.getenv("BYBIT_API_SECRET"),
            sandbox=False,
        )
        await exchange.initialize()

        # Bybit требует символ без слэша
        bybit_symbol = "BTCUSDT"
        ticker = await exchange.get_ticker(bybit_symbol)
        # ticker - это объект, а не словарь
        current_price = ticker.last if hasattr(ticker, "last") else ticker.price
        print(f"📊 Текущая цена BTC/USDT: ${current_price:.2f}")

        # 3. Создаем тестовый сигнал
        print("\n3️⃣ Создание тестового сигнала...")
        test_signal = Signal(
            symbol="BTCUSDT",  # Используем формат Bybit без слэша
            exchange="bybit",
            signal_type=SignalType.LONG,
            strength=0.75,
            confidence=0.75,
            suggested_price=current_price,
            suggested_stop_loss=current_price * 0.98,
            suggested_take_profit=current_price * 1.03,
            # Минимальный размер для Bybit - 0.001 BTC или примерно $115
            suggested_position_size=120.0,  # $120 для теста (чуть больше минимума)
            suggested_quantity=120.0 / current_price,  # Количество BTC
            strategy_name="TEST_DIRECT",
            signal_metadata={"test": True},
        )

        print(f"📋 Создан сигнал LONG BTC/USDT @ ${current_price:.2f}")
        print(f"   SL: ${test_signal.suggested_stop_loss:.2f}")
        print(f"   TP: ${test_signal.suggested_take_profit:.2f}")
        print(f"   Размер: ${test_signal.suggested_position_size}")
        print(f"   Количество BTC: {test_signal.suggested_quantity:.6f}")

        # 4. Обрабатываем сигнал
        print("\n4️⃣ Обработка сигнала через SignalProcessor...")
        orders = await signal_processor.process_signal(test_signal)

        if orders:
            print(f"✅ Создано {len(orders)} ордеров")

            # 5. Исполняем ордера
            print("\n5️⃣ Исполнение ордеров...")
            for i, order in enumerate(orders):
                print(f"\nОрдер {i + 1}:")
                print(f"  Символ: {order.symbol}")
                print(f"  Сторона: {order.side.value}")
                print(f"  Количество: {order.quantity}")
                print(f"  Цена: ${order.price:.2f}")

                # Передаем ордер в OrderManager для отправки на биржу
                success = await order_manager.submit_order(order)

                if success:
                    print("  ✅ Ордер отправлен на биржу")
                else:
                    print("  ❌ Ошибка отправки ордера")
        else:
            print("❌ Ордера не были созданы")

        # 6. Проверяем статус на бирже
        print("\n6️⃣ Проверка ордеров на Bybit...")
        await asyncio.sleep(2)  # Даем время на обработку

        # Используем правильный метод для получения открытых ордеров

        bybit_client = exchange.client if hasattr(exchange, "client") else exchange

        try:
            # Получаем открытые ордера напрямую через клиент
            open_orders = await bybit_client.get_open_orders("BTCUSDT")
            if open_orders:
                print(f"✅ Найдено {len(open_orders)} открытых ордеров:")
                for order in open_orders[:5]:
                    print(
                        f"   {order.get('createdTime', 'N/A')} | {order.get('symbol')} | "
                        f"{order.get('side')} {order.get('qty')} @ {order.get('price')}"
                    )
            else:
                print("❌ Нет открытых ордеров на бирже")
        except Exception as e:
            print(f"⚠️ Ошибка получения открытых ордеров: {e}")

    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Закрываем соединения
        print("\n🛑 Закрытие соединений...")
        if "exchange" in locals():
            # BybitExchange не имеет метода close, но это не критично
            pass
        print("✅ Тест завершен")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
