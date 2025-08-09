#!/usr/bin/env python3
"""
Принудительный тест создания ордера с hedge mode
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
    print("=== Принудительный тест создания ордера ===\n")

    try:
        from exchanges.base.order_types import OrderRequest, OrderSide, OrderType
        from exchanges.bybit.client import BybitClient

        client = BybitClient(
            api_key=os.getenv("BYBIT_API_KEY"),
            api_secret=os.getenv("BYBIT_API_SECRET"),
            sandbox=False,
        )

        print("1️⃣ Конфигурация:")
        print(f"   Hedge mode: {client.hedge_mode}")
        print(f"   Default leverage: {client.default_leverage}x")
        print(f"   Trading category: {client.trading_category}")

        print("\n2️⃣ Получение текущей цены BTC:")

        ticker = await client.get_ticker("BTCUSDT")
        current_price = ticker.price
        print(f"   BTC/USDT: ${current_price:.2f}")

        print("\n3️⃣ Создание минимального ордера (игнорируем баланс):")

        # Создаем минимальный ордер
        order_request = OrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.001,  # Минимальный размер
            price=current_price * 0.98,  # На 2% ниже рынка
            leverage=client.default_leverage,
        )

        print("\n   Параметры ордера:")
        print(f"   - Symbol: {order_request.symbol}")
        print(f"   - Side: {order_request.side.value}")
        print(f"   - Quantity: {order_request.quantity} BTC")
        print(f"   - Price: ${order_request.price:.2f}")
        print(f"   - Notional: ${order_request.quantity * order_request.price:.2f}")
        print(
            f"   - Position idx: {client._get_position_idx(order_request.side.value)}"
        )
        print(f"   - Category: {client.trading_category}")
        print(f"   - Leverage: {order_request.leverage}x")

        print("\n4️⃣ Отправка ордера:")

        try:
            response = await client.place_order(order_request)

            if response and response.success:
                print("   ✅ Ордер создан!")
                print(f"   Order ID: {response.order_id}")
                if hasattr(response, "exchange_order_id"):
                    print(f"   Exchange ID: {response.exchange_order_id}")
                print(f"   Status: {response.status}")

                # Ждем 3 секунды
                await asyncio.sleep(3)

                print("\n5️⃣ Отмена ордера:")

                try:
                    cancel_result = await client.cancel_order(
                        "BTCUSDT", response.order_id
                    )
                    if cancel_result:
                        print("   ✅ Ордер отменен")
                except Exception as e:
                    print(f"   ⚠️ Ошибка отмены: {e}")

            else:
                print(f"   ❌ Ошибка: {response.error if response else 'Нет ответа'}")

                # Если ошибка о недостатке средств, покажем детали
                if response and "Insufficient" in str(response.error):
                    print(
                        "\n   💡 Подсказка: Все средства заблокированы или недостаточно маржи"
                    )
                    print("   Проверьте:")
                    print("   - Нет ли открытых позиций")
                    print("   - Нет ли активных ордеров")
                    print("   - Достаточно ли свободной маржи для минимального ордера")

        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            import traceback

            traceback.print_exc()

    except Exception as e:
        print(f"\n❌ Общая ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
