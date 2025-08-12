#!/usr/bin/env python3
"""
Проверка API ключей Bybit
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from exchanges.bybit.client import BybitClient

load_dotenv()


async def check_keys():
    """Проверка API ключей"""

    # Пробуем разные варианты ключей
    keys_to_test = [
        # Текущие из .env
        {
            "name": "Current .env",
            "key": os.getenv("BYBIT_API_KEY"),
            "secret": os.getenv("BYBIT_API_SECRET"),
        },
        # Ключи которые user давал
        {
            "name": "User provided",
            "key": "NbH0wWQ3rmgJjO2YGw",
            "secret": "6TFlkmRjczVL4y2orFlGLQMBfPpAOSaDwTUJ",
        },
        # Возможно есть другие в файлах
    ]

    print("=" * 60)
    print("ПРОВЕРКА API КЛЮЧЕЙ BYBIT")
    print("=" * 60)

    for key_set in keys_to_test:
        if not key_set["key"] or not key_set["secret"]:
            continue

        print(f"\n🔑 Проверяем: {key_set['name']}")
        print(f"   Key: {key_set['key'][:10]}...")

        try:
            client = BybitClient(
                api_key=key_set["key"], api_secret=key_set["secret"], sandbox=False
            )

            # Пробуем получить баланс
            response = await client._make_request(
                "GET",
                "/v5/account/wallet-balance",
                {"accountType": "UNIFIED"},
                auth=True,
            )

            if response and "result" in response:
                result = response["result"]
                if "list" in result and result["list"]:
                    wallet = result["list"][0]
                    total_balance = float(wallet.get("totalEquity", 0))
                    print(f"   ✅ Ключи работают! Баланс: ${total_balance:.2f}")

                    # Детали баланса
                    coins = wallet.get("coin", [])
                    for coin in coins:
                        if float(coin.get("equity", 0)) > 0:
                            print(f"      {coin['coin']}: {coin['equity']}")
                else:
                    print("   ❌ Ключи не работают: пустой ответ")
            else:
                print("   ❌ Ключи не работают: нет ответа")

        except Exception as e:
            error_msg = str(e)
            if "10003" in error_msg:
                print("   ❌ Неверные API ключи")
            elif "33004" in error_msg:
                print("   ❌ API ключи истекли")
            else:
                print(f"   ❌ Ошибка: {error_msg}")

    print("\n" + "=" * 60)
    print("Поиск других ключей в конфигурации...")
    print("=" * 60)

    # Ищем ключи в других файлах
    config_files = [
        "config/credentials.yaml",
        "config/exchanges.yaml",
        ".env.production",
        ".env.local",
    ]

    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"📄 Найден файл: {config_file}")
            with open(config_file, "r") as f:
                content = f.read()
                if "api_key" in content.lower() or "bybit" in content.lower():
                    print("   Может содержать ключи, проверьте вручную")


if __name__ == "__main__":
    asyncio.run(check_keys())
