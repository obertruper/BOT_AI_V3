#!/usr/bin/env python3
"""Проверка реальных позиций на Bybit"""

import asyncio
import os

from dotenv import load_dotenv

from exchanges.bybit.client import BybitClient

load_dotenv()


async def check():
    client = BybitClient(
        api_key=os.getenv("BYBIT_API_KEY"), api_secret=os.getenv("BYBIT_API_SECRET")
    )

    try:
        await client.connect()

        # Получаем позиции
        positions = await client.get_positions()

        print("=" * 80)
        print("ТЕКУЩИЕ ПОЗИЦИИ НА BYBIT")
        print("=" * 80)

        open_positions = []
        total_unrealized_pnl = 0

        for pos in positions:
            if pos.size != 0:  # Только открытые позиции
                open_positions.append(pos)
                total_unrealized_pnl += pos.unrealised_pnl
                print(f"\n{pos.symbol}:")
                print(f"  Размер: {pos.size}")
                print(f"  Сторона: {pos.side}")
                print(f"  Цена входа: {pos.entry_price}")
                print(f"  Текущая цена: {pos.mark_price}")
                print(f"  Unrealized PnL: ${pos.unrealised_pnl:.2f}")
                print(f"  Плечо: {pos.leverage}x")

        print("\n" + "=" * 80)
        print(f"ИТОГО ОТКРЫТО ПОЗИЦИЙ: {len(open_positions)}")
        print(f"ОБЩИЙ UNREALIZED PNL: ${total_unrealized_pnl:.2f}")

        # Получаем баланс
        balance = await client.get_balance()
        usdt_balance = balance.get("USDT", {})

        print("\n" + "=" * 80)
        print("БАЛАНС АККАУНТА:")
        print(f"  Доступный баланс: ${usdt_balance.get('available_balance', 0):.2f}")
        print(
            f"  Используется в позициях: ${usdt_balance.get('position_margin', 0):.2f}"
        )
        print(f"  Общий баланс: ${usdt_balance.get('total_balance', 0):.2f}")

        # Проверяем открытые ордера
        orders = await client.get_open_orders()
        print("\n" + "=" * 80)
        print(f"АКТИВНЫХ ОРДЕРОВ: {len(orders)}")

        for order in orders:
            print(f"\n{order.symbol}: {order.side} {order.quantity} @ {order.price}")

    finally:
        # BybitClient не имеет метода close
        pass


if __name__ == "__main__":
    asyncio.run(check())
