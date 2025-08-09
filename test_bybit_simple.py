#!/usr/bin/env python3
"""
Простой тест Bybit API - проверка баланса и создание тестового ордера
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
    print("=== Простой тест Bybit API ===\n")

    try:
        # Создаем клиент Bybit напрямую
        from exchanges.bybit.client import BybitClient

        client = BybitClient(
            api_key=os.getenv("BYBIT_API_KEY"),
            api_secret=os.getenv("BYBIT_API_SECRET"),
            sandbox=False,
        )

        print("1️⃣ Проверка баланса через client.get_wallet_balance():")

        try:
            balance = await client.get_wallet_balance()
            print(f"   Баланс получен: {balance}")

            if hasattr(balance, "balances"):
                for asset, info in balance.balances.items():
                    if info.total > 0:
                        print(
                            f"   {asset}: всего={info.total:.4f}, свободно={info.free:.4f}"
                        )

        except Exception as e:
            print(f"   Ошибка: {e}")

        print("\n2️⃣ Проверка текущей цены BTC:")

        ticker = await client.get_ticker("BTCUSDT")
        current_price = ticker.price
        print(f"   BTC/USDT: ${current_price:.2f}")

        print("\n3️⃣ Проверка режима позиций:")

        # Проверяем режим позиций
        try:
            # Получаем информацию о счете
            account_info = await client._make_request("GET", "/v5/account/info", {})

            if account_info and "unifiedMarginStatus" in account_info:
                print(
                    f"   Unified Margin Status: {account_info['unifiedMarginStatus']}"
                )

        except Exception as e:
            print(f"   Не удалось получить информацию о счете: {e}")

        print("\n4️⃣ Попытка создать минимальный ордер:")

        # Рассчитываем минимальный размер
        min_btc = 0.001
        min_usd = min_btc * current_price

        print(f"   Минимальный размер: {min_btc} BTC (${min_usd:.2f})")

        # Создаем OrderRequest
        from exchanges.base.order_types import OrderRequest, OrderSide, OrderType

        # Добавляем специфичные параметры для Bybit
        order_request = OrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=min_btc,
            price=current_price * 0.99,  # На 1% ниже рынка
            # Добавляем exchange-специфичные параметры
            exchange_params={
                "category": "linear",  # Для futures
                "positionIdx": 0,  # 0 для one-way mode
            },
        )

        print(
            f"   Создаем ордер: BUY {order_request.quantity} BTC @ ${order_request.price:.2f}"
        )

        try:
            response = await client.place_order(order_request)

            if response and response.success:
                print(f"   ✅ Ордер создан! ID: {response.order_id}")

                # Отменяем ордер
                await asyncio.sleep(2)
                print("\n5️⃣ Отменяем тестовый ордер:")

                cancel_response = await client.cancel_order(
                    "BTCUSDT", response.order_id
                )
                if cancel_response:
                    print("   ✅ Ордер отменен")
            else:
                print(
                    f"   ❌ Ошибка создания ордера: {response.error if response else 'Нет ответа'}"
                )

        except Exception as e:
            print(f"   ❌ Ошибка: {e}")

            # Проверяем детали ошибки
            if "exceeds minimum limit" in str(e):
                print("\n   ⚠️ Размер ордера слишком мал!")
                print("   Попробуем увеличить до 0.01 BTC")

                order_request.quantity = 0.01
                try:
                    response = await client.place_order(order_request)
                    if response and response.success:
                        print(
                            f"   ✅ Ордер создан с увеличенным размером! ID: {response.order_id}"
                        )
                        await asyncio.sleep(2)
                        await client.cancel_order("BTCUSDT", response.order_id)
                        print("   ✅ Ордер отменен")
                except Exception as e2:
                    print(f"   ❌ Все еще ошибка: {e2}")

    except Exception as e:
        print(f"\n❌ Общая ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
