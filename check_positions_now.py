#!/usr/bin/env python3
"""
Проверка текущих позиций
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# Добавляем корневую директорию в PATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()


async def check_positions():
    """Проверка открытых позиций"""
    from exchanges.bybit.client import BybitClient

    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")

    client = BybitClient(api_key=api_key, api_secret=api_secret)

    try:
        # Получаем позиции
        positions = await client.get_positions()

        if positions:
            print(f"\n📊 Открытые позиции ({len(positions)}):")
            print("=" * 80)

            total_pnl = 0
            for pos in positions:
                # Выводим все доступные атрибуты
                print(f"\n{pos.symbol}:")
                print(f"  Направление: {pos.side}")
                print(f"  Размер: {pos.size}")
                print(f"  Средняя цена: {pos.entry_price}")
                print(f"  Текущая цена: {pos.mark_price}")

                # Рассчитываем P&L вручную
                if pos.side == "Buy":
                    pnl = (pos.mark_price - pos.entry_price) * pos.size
                else:  # Sell
                    pnl = (pos.entry_price - pos.mark_price) * pos.size

                print(f"  P&L: ${pnl:.2f}")
                total_pnl += pnl

            print("\n" + "=" * 80)
            print(f"💰 Общий P&L: ${total_pnl:.2f}")
        else:
            print("📊 Нет открытых позиций")

        # Проверяем баланс
        balance = await client.get_balance("USDT")
        print("\n💵 Баланс USDT:")
        print(f"  Всего: {balance.total:.2f}")
        print(f"  Доступно: {balance.available:.2f}")
        print(f"  В позициях: {balance.total - balance.available:.2f}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(check_positions())
