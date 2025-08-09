# \!/usr/bin/env python3
"""
Тестирование полного потока от ML сигнала до ордера на Bybit

Этот скрипт создает тестовый сигнал и прогоняет его через весь пайплайн:
ML Signal → Trading Engine → Signal Processor → Order Manager → Execution Engine → Bybit
"""

import asyncio
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from core.config.config_manager import ConfigManager
from core.system.orchestrator import SystemOrchestrator

# Импортируем необходимые компоненты
from strategies.base.strategy_abc import SignalType as StrategySignalType
from strategies.base.strategy_abc import TradingSignal


async def main():
    """Главная функция теста"""
    print("=" * 80)
    print("🧪 ТЕСТ ПОЛНОГО ПОТОКА: ML СИГНАЛ → ОРДЕР НА BYBIT")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Инициализация конфигурации
    config_manager = ConfigManager()

    # Создаем оркестратор
    orchestrator = SystemOrchestrator(config_manager)

    try:
        # 1. Инициализируем систему
        print("\n1️⃣ Инициализация системы...")
        await orchestrator.initialize()
        print("✅ Система инициализирована")

        # 2. Запускаем торговый движок
        print("\n2️⃣ Запуск торгового движка...")
        await orchestrator.start()
        await asyncio.sleep(3)  # Даем время на запуск
        print("✅ Торговый движок запущен")

        # Получаем ссылку на trading engine
        trading_engine = orchestrator.trading_engine
        if not trading_engine:
            print("❌ Trading Engine не найден в orchestrator!")
            print("Пытаемся создать Trading Engine напрямую...")

            # Создаем Trading Engine напрямую
            from trading.engine import TradingEngine

            trading_engine = TradingEngine(
                orchestrator=orchestrator, config=config_manager.get_config()
            )
            await trading_engine.initialize()
            await trading_engine.start()
            print("✅ Trading Engine создан и запущен напрямую")

        # 3. Создаем тестовый торговый сигнал
        print("\n3️⃣ Создание тестового ML сигнала...")

        # Получаем текущую цену BTC
        from exchanges.factory import ExchangeFactory

        factory = ExchangeFactory()
        exchange = await factory.create_and_connect(
            exchange_type="bybit",
            api_key=os.getenv("BYBIT_API_KEY"),
            api_secret=os.getenv("BYBIT_API_SECRET"),
            sandbox=False,
        )
        await exchange.initialize()

        ticker = await exchange.get_ticker("BTC/USDT")
        current_price = ticker["last"]
        print(f"📊 Текущая цена BTC/USDT: ${current_price:.2f}")

        # Создаем TradingSignal (как от AI Signal Generator)
        test_signal = TradingSignal(
            timestamp=datetime.now(),
            symbol="BTC/USDT",
            signal_type=StrategySignalType.BUY,
            confidence=75.0,  # 75% уверенность
            entry_price=current_price,
            stop_loss=current_price * 0.98,  # SL -2%
            take_profit=current_price * 1.03,  # TP +3%
            position_size=10.0,  # $10 позиция для теста
            strategy_name="ML_TEST_SIGNAL",
            timeframe="15m",
            indicators_used=["ML_Model", "Test"],
        )

        print(f"📋 Создан сигнал: BUY BTC/USDT @ ${current_price:.2f}")
        print(
            f"   SL: ${test_signal.stop_loss:.2f} | TP: ${test_signal.take_profit:.2f}"
        )
        print(f"   Размер: ${test_signal.position_size}")

        # 4. Отправляем сигнал в Trading Engine
        print("\n4️⃣ Отправка сигнала в Trading Engine...")
        await trading_engine.receive_trading_signal(test_signal)
        print("✅ Сигнал отправлен")

        # 5. Ждем обработку
        print("\n5️⃣ Ожидание обработки сигнала...")
        await asyncio.sleep(5)

        # 6. Проверяем статус
        print("\n6️⃣ Проверка статуса:")
        status = trading_engine.get_status()
        print(f"   Обработано сигналов: {status['metrics']['signals_processed']}")
        print(f"   Исполнено ордеров: {status['metrics']['orders_executed']}")
        print(f"   Ошибок: {status['metrics']['errors_count']}")

        # 7. Проверяем ордера в БД
        print("\n7️⃣ Проверка ордеров в БД...")
        from sqlalchemy import text

        from database.connections import get_async_db

        async with get_async_db() as db:
            # Проверяем последние ордера
            result = await db.execute(
                text(
                    """
                    SELECT order_id, symbol, side, quantity, price, status, created_at
                    FROM orders
                    ORDER BY created_at DESC
                    LIMIT 5
                """
                )
            )

            orders = result.fetchall()
            if orders:
                print(f"   Найдено {len(orders)} последних ордеров:")
                for order in orders:
                    print(
                        f"   {order.created_at} | {order.symbol} | {order.side} {order.quantity} @ {order.price} | {order.status}"
                    )
            else:
                print("   ❌ Ордеров не найдено")

        # 8. Проверяем открытые ордера на Bybit
        print("\n8️⃣ Проверка открытых ордеров на Bybit...")
        open_orders = await exchange.fetch_open_orders()

        if open_orders:
            print(f"   Найдено {len(open_orders)} открытых ордеров на бирже:")
            for order in open_orders[:5]:
                print(
                    f"   {order['datetime']} | {order['symbol']} | {order['side']} {order['amount']} @ {order['price']}"
                )
        else:
            print("   Нет открытых ордеров на бирже")

    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Останавливаем систему
        print("\n🛑 Остановка системы...")
        await orchestrator.shutdown()
        if "exchange" in locals():
            await exchange.close()
        print("✅ Система остановлена")

    print("\n" + "=" * 80)
    print("✅ Тест завершен")


if __name__ == "__main__":
    asyncio.run(main())
