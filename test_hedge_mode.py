#!/usr/bin/env python3
"""
Тест hedge mode и futures торговли с новой конфигурацией
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
    print("=== Тест Hedge Mode и Futures торговли ===\n")

    try:
        # Создаем клиент Bybit
        from exchanges.bybit.client import BybitClient

        client = BybitClient(
            api_key=os.getenv("BYBIT_API_KEY"),
            api_secret=os.getenv("BYBIT_API_SECRET"),
            sandbox=False,
        )

        print("1️⃣ Проверка загруженной конфигурации:")
        print(f"   Hedge mode: {client.hedge_mode}")
        print(f"   Default leverage: {client.default_leverage}x")
        print(f"   Trading category: {client.trading_category}")

        print("\n2️⃣ Проверка баланса:")

        # Получаем баланс USDT (основная валюта для futures)
        try:
            usdt_balance = await client.get_balance("USDT")
            if usdt_balance:
                print(
                    f"   USDT: всего={usdt_balance.total:.4f}, свободно={usdt_balance.free:.4f}"
                )
        except Exception as e:
            print(f"   Ошибка получения баланса: {e}")

        print("\n3️⃣ Получение текущей цены BTC:")

        ticker = await client.get_ticker("BTCUSDT")
        current_price = ticker.price
        print(f"   BTC/USDT: ${current_price:.2f}")

        print("\n4️⃣ Тест определения position_idx:")

        # Тестируем для BUY
        buy_idx = client._get_position_idx("BUY")
        print(f"   BUY position_idx: {buy_idx} (ожидается 1 для hedge mode)")

        # Тестируем для SELL
        sell_idx = client._get_position_idx("SELL")
        print(f"   SELL position_idx: {sell_idx} (ожидается 2 для hedge mode)")

        print("\n5️⃣ Проверка текущего режима позиций на счете:")

        try:
            # Получаем информацию о счете
            account_info = await client._make_request("GET", "/v5/account/info", {})

            if account_info:
                print(
                    f"   Account info: {account_info.get('unifiedMarginStatus', 'N/A')}"
                )

            # Проверяем режим позиций
            position_info = await client._make_request(
                "GET", "/v5/position/list", {"category": "linear", "symbol": "BTCUSDT"}
            )

            if position_info and "list" in position_info:
                positions = position_info["list"]
                if positions:
                    for pos in positions:
                        print(
                            f"   Позиция {pos['symbol']}: positionIdx={pos.get('positionIdx', 'N/A')}"
                        )
                else:
                    print("   Нет открытых позиций")

        except Exception as e:
            print(f"   Ошибка получения информации о позициях: {e}")

        print("\n6️⃣ Создание тестового ордера с правильными параметрами:")

        # Создаем OrderRequest с минимальным размером
        from exchanges.base.order_types import OrderRequest, OrderSide, OrderType

        min_btc = 0.001  # Минимальный размер для BTC

        order_request = OrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=min_btc,
            price=current_price * 0.99,  # На 1% ниже рынка
            leverage=client.default_leverage,  # Используем leverage из конфигурации
        )

        print("   Создаем ордер:")
        print(f"   - Symbol: {order_request.symbol}")
        print(f"   - Side: {order_request.side.value}")
        print(f"   - Quantity: {order_request.quantity} BTC")
        print(f"   - Price: ${order_request.price:.2f}")
        print(
            f"   - Position idx: {client._get_position_idx(order_request.side.value)}"
        )
        print(f"   - Category: {client.trading_category}")
        print(f"   - Leverage: {order_request.leverage}x")

        try:
            response = await client.place_order(order_request)

            if response and response.success:
                print("\n   ✅ Ордер создан успешно!")
                print(f"   Order ID: {response.order_id}")
                print(f"   Status: {response.status}")

                # Ждем немного и отменяем
                await asyncio.sleep(2)

                print("\n7️⃣ Отменяем тестовый ордер:")
                cancel_response = await client.cancel_order(
                    "BTCUSDT", response.order_id
                )
                if cancel_response:
                    print("   ✅ Ордер отменен")
            else:
                print(
                    f"\n   ❌ Ошибка создания ордера: {response.error if response else 'Нет ответа'}"
                )

        except Exception as e:
            print(f"\n   ❌ Ошибка: {e}")

    except Exception as e:
        print(f"\n❌ Общая ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
