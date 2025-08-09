#!/usr/bin/env python3
"""
Проверка статуса аккаунта
"""

import asyncio
import os

from dotenv import load_dotenv

load_dotenv()


async def check_account():
    from exchanges.bybit.bybit_exchange import BybitExchange

    exchange = BybitExchange(
        api_key=os.getenv("BYBIT_API_KEY"),
        api_secret=os.getenv("BYBIT_API_SECRET"),
        sandbox=False,
    )

    try:
        await exchange.connect()

        print("🔍 ПРОВЕРКА СТАТУСА АККАУНТА")
        print("=" * 60)

        # 1. Балансы
        print("\n💰 БАЛАНСЫ:")
        balances = await exchange.get_balances()
        for balance in balances:
            if balance.total > 0:
                available_pct = (
                    (balance.available / balance.total * 100)
                    if balance.total > 0
                    else 0
                )
                print(
                    f"   {balance.currency}: ${balance.total:.2f} "
                    f"(доступно: ${balance.available:.2f} = {available_pct:.0f}%)"
                )

        # 2. Позиции
        print("\n📊 ПОЗИЦИИ:")
        positions = await exchange.get_positions()
        position_count = 0
        for pos in positions:
            if pos.size > 0:
                position_count += 1
                print(f"   {pos.symbol}: {pos.side} {pos.size} @ ${pos.entry_price}")
                print(f"      Текущая цена: ${pos.mark_price}")
                print(f"      PnL: ${pos.unrealized_pnl}")

        if position_count == 0:
            print("   Нет открытых позиций")

        # 3. Проверяем конкретные символы для ордеров
        print("\n💱 ОТКРЫТЫЕ ОРДЕРА:")
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        order_count = 0

        for symbol in symbols:
            try:
                orders = await exchange.get_open_orders(symbol)
                for order in orders:
                    order_count += 1
                    print(
                        f"   {order.symbol}: {order.side} {order.type} "
                        f"{order.quantity} @ ${order.price}"
                    )
                    print(f"      ID: {order.id}")
                    print(f"      Статус: {order.status}")
            except Exception:
                pass  # Игнорируем ошибки для символов без ордеров

        if order_count == 0:
            print("   Нет открытых ордеров")

        # 4. Информация об аккаунте
        print("\n📋 ИНФОРМАЦИЯ ОБ АККАУНТЕ:")

        # Получаем raw API ответ для более детальной информации
        try:
            import ccxt

            ccxt_exchange = ccxt.bybit(
                {
                    "apiKey": os.getenv("BYBIT_API_KEY"),
                    "secret": os.getenv("BYBIT_API_SECRET"),
                }
            )

            # Получаем информацию о маржинальном режиме
            account_info = await ccxt_exchange.fetch_balance()

            if "info" in account_info:
                info = account_info["info"]
                if "result" in info and "list" in info["result"]:
                    for acc in info["result"]["list"]:
                        if acc["coin"] == "USDT":
                            print(f"   Тип аккаунта: {acc.get('accountType', 'N/A')}")
                            print(
                                f"   Заблокировано: ${float(acc.get('locked', 0)):.2f}"
                            )
                            print(
                                f"   Ордер маржа: ${float(acc.get('orderIM', 0)):.2f}"
                            )
                            print(
                                f"   Позиционная маржа: ${float(acc.get('positionIM', 0)):.2f}"
                            )

        except Exception as e:
            print(f"   Не удалось получить детальную информацию: {e}")

        print("\n" + "=" * 60)

    finally:
        await exchange.disconnect()


if __name__ == "__main__":
    asyncio.run(check_account())
