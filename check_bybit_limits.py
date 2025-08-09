#!/usr/bin/env python3
"""
Проверка баланса и минимальных лимитов на Bybit
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
    print("=== Проверка Bybit лимитов и баланса ===\n")

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

        # 1. Проверяем баланс
        print("1️⃣ Баланс аккаунта:")

        # Получаем баланс USDT
        usdt_balance_info = await exchange.get_balance("USDT")

        # Balance - это объект, не словарь
        if usdt_balance_info:
            usdt_balance = (
                usdt_balance_info.free if hasattr(usdt_balance_info, "free") else 0
            )
            usdt_total = (
                usdt_balance_info.total if hasattr(usdt_balance_info, "total") else 0
            )
        else:
            usdt_balance = 0
            usdt_total = 0

        print(f"   USDT: {usdt_total:.4f} (свободно: {usdt_balance:.4f})")
        print(f"\n💰 Доступно USDT для торговли: ${usdt_balance:.2f}")

        # 2. Проверяем открытые позиции
        print("\n2️⃣ Проверка открытых позиций:")

        try:
            # Получаем позиции
            positions = await exchange.get_positions()
            if positions:
                print(f"   Найдено {len(positions)} позиций:")
                for pos in positions:
                    if (
                        hasattr(pos, "symbol")
                        and hasattr(pos, "size")
                        and pos.size != 0
                    ):
                        print(
                            f"   {pos.symbol}: {pos.size} (PnL: {getattr(pos, 'pnl', 'N/A')})"
                        )
            else:
                print("   Нет открытых позиций")
        except Exception as e:
            print(f"   Ошибка получения позиций: {e}")

        # 3. Проверяем открытые ордера
        print("\n3️⃣ Проверка открытых ордеров:")

        try:
            # Используем client напрямую
            client = exchange.client if hasattr(exchange, "client") else exchange
            open_orders = await client.get_open_orders("BTCUSDT")

            if open_orders:
                print(f"   Найдено {len(open_orders)} ордеров:")
                for order in open_orders[:5]:
                    print(
                        f"   {order.get('symbol')}: {order.get('side')} {order.get('qty')} @ {order.get('price')}"
                    )
            else:
                print("   Нет открытых ордеров")
        except Exception as e:
            print(f"   Ошибка получения ордеров: {e}")

        # 4. Текущая цена BTC
        print("\n4️⃣ Текущая цена BTC:")
        ticker = await exchange.get_ticker("BTCUSDT")
        current_price = ticker.last if hasattr(ticker, "last") else ticker.price
        print(f"   BTC/USDT: ${current_price:.2f}")

        # 5. Минимальные лимиты (стандартные для Bybit)
        min_order_value = 5.0  # Минимум $5 на Bybit
        min_order_qty = 0.001  # Минимум 0.001 BTC

        min_position_usd = max(min_order_value, min_order_qty * current_price)

        print("\n📊 Минимальные требования Bybit:")
        print(f"   Минимальный размер позиции: ${min_position_usd:.2f}")
        print(f"   Это примерно: {min_position_usd / current_price:.6f} BTC")

        # 6. Анализ ситуации
        print("\n⚠️ ВНИМАНИЕ:")
        print(f"   У вас есть ${usdt_total:.2f} USDT, но все средства заблокированы!")
        print(f"   Свободно: ${usdt_balance:.2f}")
        print("\n   Возможные причины:")
        print("   - Есть открытые позиции")
        print("   - Есть активные ордера")
        print("   - Средства в других активах")

        if usdt_balance == 0:
            print("\n❌ Нет свободных средств для торговли!")
            print("   Закройте открытые позиции или отмените ордера")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()

    finally:
        if "exchange" in locals():
            # BybitExchange не имеет метода close
            pass


if __name__ == "__main__":
    asyncio.run(main())
