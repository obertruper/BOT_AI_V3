#!/usr/bin/env python3
"""
Закрытие всех открытых позиций на Bybit
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# Добавляем корневую директорию в PATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()


async def close_all_positions():
    """Закрытие всех открытых позиций"""
    from exchanges.base.order_types import OrderRequest, OrderSide, OrderType
    from exchanges.bybit.client import BybitClient

    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")

    client = BybitClient(api_key=api_key, api_secret=api_secret)

    try:
        # Получаем позиции
        positions = await client.get_positions()

        if not positions:
            print("📊 Нет открытых позиций для закрытия")
            return

        print(f"\n📊 Найдено {len(positions)} открытых позиций")
        print("=" * 80)

        # Автоматическое подтверждение для скрипта
        print("\n⚠️ ВНИМАНИЕ: Закрываем ВСЕ позиции по рыночной цене!")
        print("✅ Автоматическое подтверждение")

        # Закрываем каждую позицию
        for pos in positions:
            print(f"\nЗакрываем {pos.symbol}:")
            print(f"  Направление: {pos.side}")
            print(f"  Размер: {pos.size}")

            try:
                # Для закрытия позиции создаем противоположный ордер
                # с тем же размером
                side = OrderSide.SELL if pos.side == "Buy" else OrderSide.BUY

                # Создаем рыночный ордер для закрытия
                order_request = OrderRequest(
                    symbol=pos.symbol,
                    side=side,
                    order_type=OrderType.MARKET,
                    quantity=pos.size,
                    reduce_only=True,  # Только закрытие позиции
                    time_in_force="IOC",  # Immediate or Cancel
                )

                result = await client.place_order(order_request)
                if result:
                    print("  ✅ Позиция закрыта")
                else:
                    print("  ❌ Не удалось закрыть позицию")

            except Exception as e:
                print(f"  ❌ Ошибка при закрытии: {e}")

        # Проверяем финальный баланс
        await asyncio.sleep(2)  # Ждем обновления баланса

        balance = await client.get_balance("USDT")
        print("\n💵 Финальный баланс USDT:")
        print(f"  Всего: {balance.total:.2f}")
        print(f"  Доступно: {balance.available:.2f}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(close_all_positions())
