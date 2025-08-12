#!/usr/bin/env python3
"""Проверка текущих открытых позиций"""

import asyncio

from exchanges.factory import ExchangeFactory


async def check():
    factory = ExchangeFactory()
    client = await factory.create_client("bybit")
    if client:
        positions = await client.get_positions()
        print(f"Всего позиций: {len(positions)}")
        open_positions = []
        for pos in positions:
            if pos.size != 0:
                open_positions.append(pos)
                print(
                    f"{pos.symbol}: size={pos.size}, side={pos.side}, upnl={pos.unrealized_pnl:.2f}, entry={pos.entry_price}"
                )
        print(f"\nОткрытых позиций: {len(open_positions)}")

        # Проверим баланс
        balance = await client.get_balance()
        print(f"\nБаланс USDT: {balance.get('USDT', 0):.2f}")

        await client.close()


if __name__ == "__main__":
    asyncio.run(check())
