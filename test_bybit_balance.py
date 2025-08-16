#!/usr/bin/env python3
"""
Проверка баланса Bybit через API
"""

import asyncio
import os

from dotenv import load_dotenv

load_dotenv()


async def check_balance():
    """Проверка баланса через Bybit client"""
    from exchanges.bybit.client import BybitClient

    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")

    print(f"🔑 Using API key: {api_key[:10]}...")

    client = BybitClient(api_key=api_key, api_secret=api_secret)

    try:
        # Проверяем баланс
        balance = await client.get_balance("USDT")
        print("✅ Баланс получен успешно:")
        print(f"   USDT: {balance}")

        # Проверяем позиции
        positions = await client.get_positions()
        if positions:
            print(f"📊 Открытые позиции: {len(positions)}")
            for pos in positions:
                print(f"   - {pos['symbol']}: {pos.get('size', 0)} @ {pos.get('avgPrice', 0)}")
        else:
            print("📊 Нет открытых позиций")

        # Проверяем открытые ордера
        orders = await client.get_open_orders()
        if orders:
            print(f"📝 Открытые ордера: {len(orders)}")
        else:
            print("📝 Нет открытых ордеров")

        return True

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(check_balance())
