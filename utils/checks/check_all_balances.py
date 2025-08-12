#!/usr/bin/env python3
"""
Проверка всех балансов на Bybit
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
    print("=== Проверка всех балансов Bybit ===\n")

    try:
        # Создаем подключение к Bybit
        from exchanges.factory import ExchangeFactory

        factory = ExchangeFactory()
        exchange = await factory.create_and_connect(
            exchange_type="bybit",
            api_key=os.getenv("BYBIT_API_KEY"),
            api_secret=os.getenv("BYBIT_API_SECRET"),
            sandbox=False,
        )
        await exchange.initialize()

        # Используем client напрямую
        client = exchange.client if hasattr(exchange, "client") else exchange

        # Проверяем все типы аккаунтов
        print("🔍 Проверка балансов по типам аккаунтов:\n")

        # 1. Unified Trading Account (основной)
        print("1️⃣ Unified Trading Account:")
        try:
            # Получаем баланс напрямую через API
            response = await client._make_request(
                "GET", "/v5/account/wallet-balance", {"accountType": "UNIFIED"}
            )

            if response and "list" in response:
                for wallet in response["list"]:
                    print(f"\n   Тип счета: {wallet.get('accountType')}")

                    coins = wallet.get("coin", [])
                    for coin in coins:
                        if float(coin.get("walletBalance", 0)) > 0:
                            name = coin.get("coin")
                            total = float(coin.get("walletBalance", 0))
                            available = float(coin.get("availableToWithdraw", 0))
                            locked = total - available

                            print(f"   {name}:")
                            print(f"      Всего: {total:.4f}")
                            print(f"      Доступно: {available:.4f}")
                            print(f"      Заблокировано: {locked:.4f}")

                            if locked > 0:
                                print(f"      ⚠️ В ордерах/позициях: {locked:.4f}")
        except Exception as e:
            print(f"   Ошибка: {e}")

        # 2. Spot Account
        print("\n2️⃣ Spot Account:")
        try:
            response = await client._make_request(
                "GET", "/v5/account/wallet-balance", {"accountType": "SPOT"}
            )

            if response and "list" in response:
                for wallet in response["list"]:
                    coins = wallet.get("coin", [])
                    for coin in coins:
                        if float(coin.get("walletBalance", 0)) > 0:
                            name = coin.get("coin")
                            total = float(coin.get("walletBalance", 0))
                            free = float(coin.get("free", 0))
                            locked = float(coin.get("locked", 0))

                            print(
                                f"   {name}: {total:.4f} (свободно: {free:.4f}, заблокировано: {locked:.4f})"
                            )
        except Exception:
            print("   Ошибка или нет средств")

        # 3. Проверяем активные позиции детально
        print("\n3️⃣ Детальная проверка позиций:")
        try:
            response = await client._make_request(
                "GET", "/v5/position/list", {"category": "linear", "settleCoin": "USDT"}
            )

            if response and "list" in response:
                positions = response["list"]
                if positions:
                    print(f"   Найдено {len(positions)} позиций:")
                    for pos in positions:
                        if float(pos.get("size", 0)) > 0:
                            print(
                                f"   {pos.get('symbol')}: размер={pos.get('size')}, PnL={pos.get('unrealisedPnl')}"
                            )
                else:
                    print("   Нет активных позиций")
        except Exception as e:
            print(f"   Ошибка: {e}")

        # 4. Все открытые ордера
        print("\n4️⃣ Все открытые ордера:")
        try:
            response = await client._make_request(
                "GET",
                "/v5/order/realtime",
                {"category": "linear", "settleCoin": "USDT"},
            )

            if response and "list" in response:
                orders = response["list"]
                if orders:
                    print(f"   Найдено {len(orders)} ордеров:")
                    for order in orders[:5]:
                        print(
                            f"   {order.get('symbol')}: {order.get('side')} {order.get('qty')} @ {order.get('price')} (статус: {order.get('orderStatus')})"
                        )
                else:
                    print("   Нет открытых ордеров")
        except Exception as e:
            print(f"   Ошибка: {e}")

    except Exception as e:
        print(f"\n❌ Общая ошибка: {e}")
        import traceback

        traceback.print_exc()

    finally:
        if "exchange" in locals():
            # BybitExchange не имеет метода close
            pass


if __name__ == "__main__":
    asyncio.run(main())
