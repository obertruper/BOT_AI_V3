#!/usr/bin/env python3
"""
Прямой тест Bybit API без обёрток
"""

import asyncio
import os

import ccxt.pro as ccxt
from dotenv import load_dotenv

load_dotenv()


async def test_bybit_direct():
    """Прямой тест через ccxt"""
    print("=" * 60)
    print("ПРЯМОЙ ТЕСТ BYBIT ЧЕРЕЗ CCXT")
    print("=" * 60)

    # Создаем клиент Bybit
    exchange = ccxt.bybit(
        {
            "apiKey": os.getenv("BYBIT_API_KEY"),
            "secret": os.getenv("BYBIT_API_SECRET"),
            "enableRateLimit": True,
            "options": {
                "defaultType": "spot",  # Используем spot для начала
            },
        }
    )

    try:
        # 1. Загрузка рынков
        print("\n1. Загрузка рынков...")
        markets = await exchange.load_markets()
        print(f"✅ Загружено {len(markets)} рынков")

        # 2. Проверка баланса
        print("\n2. Проверка баланса...")
        balance = await exchange.fetch_balance()

        # Показываем USDT баланс
        usdt_free = balance["USDT"]["free"]
        usdt_total = balance["USDT"]["total"]
        print("✅ USDT баланс:")
        print(f"   Свободно: ${usdt_free:.2f}")
        print(f"   Всего: ${usdt_total:.2f}")

        # Показываем другие ненулевые балансы
        print("\n   Другие балансы:")
        for currency, info in balance.items():
            if (
                isinstance(info, dict)
                and info.get("total", 0) > 0
                and currency != "USDT"
            ):
                print(f"   {currency}: {info['total']:.8f}")

        # 3. Получение тикера
        print("\n3. Проверка рыночных данных...")
        ticker = await exchange.fetch_ticker("BTC/USDT")
        print("✅ BTC/USDT:")
        print(f"   Цена: ${ticker['last']:,.2f}")
        print(f"   Объем 24ч: {ticker['quoteVolume']:,.2f} USDT")
        print(f"   Изменение 24ч: {ticker['percentage']:.2f}%")

        # 4. Проверка открытых ордеров
        print("\n4. Проверка открытых ордеров...")
        open_orders = await exchange.fetch_open_orders()
        print(f"✅ Открытых ордеров: {len(open_orders)}")

        # 5. Тест создания ордера (dry run)
        print("\n5. Тест создания ордера (симуляция)...")
        symbol = "BTC/USDT"
        amount = 0.0001  # Минимальное количество
        price = ticker["bid"] * 0.99  # На 1% ниже текущей цены

        print("   Симуляция BUY ордера:")
        print(f"   Символ: {symbol}")
        print(f"   Количество: {amount} BTC")
        print(f"   Цена: ${price:,.2f}")
        print(f"   Сумма: ${amount * price:.2f}")

        # Проверка достаточности баланса
        if usdt_free >= amount * price:
            print("   ✅ Баланса достаточно для этого ордера")
        else:
            print(f"   ❌ Недостаточно баланса (нужно ${amount * price:.2f})")

        print("\n✅ Все тесты пройдены успешно!")
        print("   Bybit API работает корректно")
        print("   Можно запускать торговую систему")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()

    finally:
        await exchange.close()


if __name__ == "__main__":
    asyncio.run(test_bybit_direct())
