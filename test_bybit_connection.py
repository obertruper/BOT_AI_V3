#!/usr/bin/env python3
"""
Тест подключения к Bybit API
"""

import asyncio
import os
import sys
from datetime import datetime

import ccxt
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


async def test_bybit_connection():
    """Тестирование подключения к Bybit"""

    print("=" * 60)
    print("  ТЕСТ ПОДКЛЮЧЕНИЯ К BYBIT")
    print("=" * 60)

    # Получаем API ключи
    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")
    testnet = os.getenv("BYBIT_TESTNET", "false").lower() == "true"

    if not api_key or not api_secret:
        print("❌ ОШИБКА: API ключи не найдены в .env файле!")
        return False

    print(f"🔑 API ключ: {api_key[:10]}...")
    print(f"🌐 Режим: {'Testnet' if testnet else 'Mainnet'}")
    print("-" * 50)

    try:
        # Создаем подключение к Bybit
        exchange = ccxt.bybit(
            {
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": True,
                "options": {
                    "defaultType": "linear",  # USDT perpetual
                    "recvWindow": 10000,
                },
            }
        )

        if testnet:
            exchange.set_sandbox_mode(True)

        print("🔌 Подключаемся к Bybit...")

        # Тест 1: Проверка баланса
        print("\n📊 Проверка баланса:")
        balance = exchange.fetch_balance()
        usdt_balance = balance.get("USDT", {})

        print("💰 USDT баланс:")
        print(f"   Всего: {usdt_balance.get('total', 0):.2f}")
        print(f"   Свободно: {usdt_balance.get('free', 0):.2f}")
        print(f"   Используется: {usdt_balance.get('used', 0):.2f}")

        # Тест 2: Проверка рынков
        print("\n📈 Проверка доступных рынков:")
        markets = exchange.load_markets()
        perp_markets = [
            m for m in markets.values() if m["type"] == "swap" and m["quote"] == "USDT"
        ]
        print(f"   Найдено {len(perp_markets)} USDT perpetual рынков")

        # Тест 3: Проверка цен для 10 криптовалют
        print("\n💹 Текущие цены (10 основных криптовалют):")
        symbols = [
            "BTC/USDT:USDT",
            "ETH/USDT:USDT",
            "BNB/USDT:USDT",
            "SOL/USDT:USDT",
            "XRP/USDT:USDT",
            "ADA/USDT:USDT",
            "DOGE/USDT:USDT",
            "DOT/USDT:USDT",
            "LINK/USDT:USDT",
            "MATIC/USDT:USDT",
        ]

        for symbol in symbols:
            try:
                ticker = exchange.fetch_ticker(symbol)
                print(f"   {symbol.split('/')[0]}: ${ticker['last']:.4f}")
            except Exception:
                print(f"   {symbol.split('/')[0]}: Недоступен")

        # Тест 4: Проверка открытых позиций
        print("\n📋 Открытые позиции:")
        positions = exchange.fetch_positions()
        open_positions = [p for p in positions if p["contracts"] > 0]

        if open_positions:
            for pos in open_positions:
                print(
                    f"   {pos['symbol']}: {pos['side']} {pos['contracts']} контрактов"
                )
        else:
            print("   Нет открытых позиций")

        # Тест 5: Проверка режима хеджирования
        print("\n⚙️ Настройки аккаунта:")
        try:
            # Для Bybit v5 API
            account_info = exchange.private_get_v5_account_info()
            print(
                f"   Режим маржи: {account_info.get('result', {}).get('marginMode', 'N/A')}"
            )
        except:
            print("   Не удалось получить информацию об аккаунте")

        print("\n✅ УСПЕХ! Подключение к Bybit работает!")
        print(f"🕐 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return True

    except Exception as e:
        print(f"\n❌ ОШИБКА подключения: {str(e)}")
        return False

    finally:
        if "exchange" in locals():
            exchange.close()


if __name__ == "__main__":
    # Запускаем тест
    result = asyncio.run(test_bybit_connection())
    sys.exit(0 if result else 1)
