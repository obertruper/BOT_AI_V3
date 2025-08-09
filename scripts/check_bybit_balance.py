#!/usr/bin/env python3
"""Проверка баланса и подключения к Bybit"""

import asyncio
import os

import ccxt.async_support as ccxt
from dotenv import load_dotenv


async def check_bybit():
    """Проверка подключения и баланса Bybit"""
    load_dotenv()

    try:
        # Создаем клиента Bybit
        exchange = ccxt.bybit(
            {
                "apiKey": os.getenv("BYBIT_API_KEY"),
                "secret": os.getenv("BYBIT_API_SECRET"),
                "testnet": os.getenv("BYBIT_TESTNET", "false").lower() == "true",
                "options": {
                    "defaultType": "linear",  # USDT perpetual
                    "adjustForTimeDifference": True,
                },
            }
        )

        print("🔌 Подключение к Bybit...")

        # Загружаем рынки
        await exchange.load_markets()
        print("✅ Рынки загружены")

        # Проверяем баланс
        balance = await exchange.fetch_balance()

        print("\n💰 БАЛАНСЫ BYBIT:")
        print("=" * 50)

        # Показываем USDT баланс
        if "USDT" in balance:
            usdt = balance["USDT"]
            print("USDT:")
            print(f"  Свободно: {usdt['free']:.2f}")
            print(f"  Используется: {usdt['used']:.2f}")
            print(f"  Всего: {usdt['total']:.2f}")

        # Показываем другие балансы
        for currency, bal in balance.items():
            if currency in ["info", "free", "used", "total", "USDT"]:
                continue
            if bal["total"] > 0:
                print(f"\n{currency}:")
                print(f"  Свободно: {bal['free']:.8f}")
                print(f"  Используется: {bal['used']:.8f}")
                print(f"  Всего: {bal['total']:.8f}")

        # Проверяем открытые позиции
        print("\n📊 ОТКРЫТЫЕ ПОЗИЦИИ:")
        print("=" * 50)

        positions = await exchange.fetch_positions()
        if positions:
            for pos in positions:
                if pos["contracts"] > 0:
                    print(f"\nСимвол: {pos['symbol']}")
                    print(f"  Сторона: {pos['side']}")
                    print(f"  Контракты: {pos['contracts']}")
                    print(f"  Цена входа: {pos['markPrice']}")
                    print(f"  Нереализованный PnL: {pos['unrealizedPnl']:.2f}")
        else:
            print("Нет открытых позиций")

        # Проверяем режим позиций
        print("\n⚙️ НАСТРОЙКИ АККАУНТА:")
        print("=" * 50)

        # Получаем информацию об аккаунте
        account_info = await exchange.fetch_account()
        if account_info:
            print(f"Тип аккаунта: {account_info.get('type', 'N/A')}")
            print(f"VIP уровень: {account_info.get('vipLevel', 'N/A')}")

        # Проверяем последние сделки
        print("\n📈 ПОСЛЕДНИЕ СДЕЛКИ:")
        print("=" * 50)

        try:
            trades = await exchange.fetch_my_trades("BTCUSDT", limit=5)
            if trades:
                for trade in trades:
                    print(f"\nВремя: {trade['datetime']}")
                    print(f"  Символ: {trade['symbol']}")
                    print(f"  Сторона: {trade['side']}")
                    print(f"  Цена: {trade['price']}")
                    print(f"  Количество: {trade['amount']}")
                    print(
                        f"  Комиссия: {trade['fee']['cost']} {trade['fee']['currency']}"
                    )
            else:
                print("Нет недавних сделок")
        except Exception as e:
            print(f"Не удалось получить историю сделок: {e}")

        await exchange.close()
        print("\n✅ Проверка завершена успешно!")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print(f"Тип ошибки: {type(e).__name__}")

        # Дополнительная диагностика
        if "Invalid" in str(e) or "credentials" in str(e):
            print("\n⚠️ Проблема с API ключами. Проверьте:")
            print("1. API ключи актуальны и не истекли")
            print("2. API ключи имеют нужные права (spot/derivatives trading)")
            print("3. IP адрес добавлен в whitelist (если включен)")
            print("4. Правильный формат ключей в .env файле")


if __name__ == "__main__":
    asyncio.run(check_bybit())
