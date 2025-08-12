#!/usr/bin/env python3
"""
Проверка открытых позиций и ордеров которые могут блокировать средства
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
    print("=== Проверка позиций и ордеров ===\n")

    try:
        from exchanges.bybit.client import BybitClient

        client = BybitClient(
            api_key=os.getenv("BYBIT_API_KEY"),
            api_secret=os.getenv("BYBIT_API_SECRET"),
            sandbox=False,
        )

        print("1️⃣ Проверка баланса:")

        try:
            usdt_balance = await client.get_balance("USDT")
            if usdt_balance:
                print(
                    f"   USDT: всего={usdt_balance.total:.4f}, свободно={usdt_balance.free:.4f}, заблокировано={usdt_balance.locked:.4f}"
                )
        except Exception as e:
            print(f"   Ошибка: {e}")

        print("\n2️⃣ Проверка открытых позиций:")

        try:
            positions = await client.get_positions()
            if positions:
                print(f"   Найдено позиций: {len(positions)}")
                for pos in positions:
                    if pos.size > 0:
                        print(f"\n   Позиция {pos.symbol}:")
                        print(f"   - Side: {pos.side}")
                        print(f"   - Size: {pos.size}")
                        print(f"   - Entry price: {pos.entry_price}")
                        print(f"   - Mark price: {pos.mark_price}")
                        print(f"   - Unrealized PnL: {pos.unrealized_pnl}")
                        print(f"   - Position value: ${pos.position_value:.2f}")
            else:
                print("   Нет открытых позиций")
        except Exception as e:
            print(f"   Ошибка: {e}")

        print("\n3️⃣ Проверка активных ордеров:")

        try:
            # Проверяем ордера для основных символов
            symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
            total_orders = 0

            for symbol in symbols:
                try:
                    orders = await client.get_open_orders(symbol)
                    if orders:
                        total_orders += len(orders)
                        print(f"\n   {symbol}: {len(orders)} ордеров")
                        for order in orders[:3]:  # Показываем первые 3
                            print(
                                f"   - {order.side} {order.quantity} @ {order.price} (ID: {order.order_id[:8]}...)"
                            )
                except:
                    pass

            if total_orders == 0:
                print("   Нет активных ордеров")
            else:
                print(f"\n   Всего активных ордеров: {total_orders}")

        except Exception as e:
            print(f"   Ошибка: {e}")

        print("\n4️⃣ Проверка через прямой API запрос:")

        try:
            # Получаем информацию о кошельке
            wallet_info = await client._make_request(
                "GET", "/v5/account/wallet-balance", {"accountType": "UNIFIED"}
            )

            if wallet_info and "list" in wallet_info:
                for account in wallet_info["list"]:
                    if "coin" in account:
                        for coin_info in account["coin"]:
                            if coin_info["coin"] == "USDT":
                                print("\n   USDT (Unified account):")
                                print(f"   - Equity: {coin_info.get('equity', 'N/A')}")
                                print(
                                    f"   - Available balance: {coin_info.get('availableBalance', 'N/A')}"
                                )
                                print(
                                    f"   - Wallet balance: {coin_info.get('walletBalance', 'N/A')}"
                                )
                                print(
                                    f"   - Unrealized PnL: {coin_info.get('unrealisedPnl', 'N/A')}"
                                )
                                print(
                                    f"   - Used margin: {coin_info.get('usedMargin', 'N/A')}"
                                )

        except Exception as e:
            print(f"   Ошибка API: {e}")

    except Exception as e:
        print(f"\n❌ Общая ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
