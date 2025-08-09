#!/usr/bin/env python3
"""
Проверка баланса на Bybit
"""

import asyncio
import os

from dotenv import load_dotenv

load_dotenv()


async def check_balance():
    """Проверка баланса"""
    from exchanges.bybit.bybit_exchange import BybitExchange

    exchange = BybitExchange(
        api_key=os.getenv("BYBIT_API_KEY"),
        api_secret=os.getenv("BYBIT_API_SECRET"),
        sandbox=False,
    )

    try:
        await exchange.connect()
        print("✅ Подключено к Bybit")

        # Получаем балансы
        balances = await exchange.get_balances()

        print("\n💰 БАЛАНСЫ:")
        for balance in balances:
            if balance.total > 0:
                print(
                    f"   {balance.currency}: {balance.total:.4f} (доступно: {balance.available:.4f})"
                )

        # Проверяем позиции
        positions = await exchange.get_positions()

        if positions:
            print("\n📊 ПОЗИЦИИ:")
            for pos in positions:
                if pos.size > 0:
                    print(f"   {pos.symbol}: {pos.side} {pos.size} @ {pos.entry_price}")
        else:
            print("\n📊 Нет открытых позиций")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await exchange.disconnect()


if __name__ == "__main__":
    asyncio.run(check_balance())
