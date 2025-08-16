#!/usr/bin/env python3
"""
Проверка API ключей Bybit
"""

import asyncio
import os

from dotenv import load_dotenv
from pybit.unified_trading import HTTP

load_dotenv()


async def test_bybit_keys():
    """Тестирование API ключей Bybit"""

    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")

    print(f"🔑 API Key: {api_key[:10]}...")
    print(f"🔒 Secret: {api_secret[:10]}...")

    try:
        # Создаем сессию (тестнет = False для реальной торговли)
        session = HTTP(testnet=False, api_key=api_key, api_secret=api_secret)

        # Проверяем баланс аккаунта
        result = session.get_wallet_balance(accountType="UNIFIED", coin="USDT")

        if result["retCode"] == 0:
            print("✅ API ключи валидны!")

            # Показываем баланс
            balance_info = result["result"]["list"][0]
            if balance_info["coin"]:
                for coin_data in balance_info["coin"]:
                    if coin_data["coin"] == "USDT":
                        print(f"💰 Баланс USDT: {coin_data['walletBalance']}")
                        print(f"   Доступно: {coin_data['availableToWithdraw']}")
        else:
            print(f"❌ Ошибка API: {result['retMsg']}")

    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        print("\n⚠️ Возможные причины:")
        print("1. Неверные API ключи")
        print("2. IP адрес не в белом списке")
        print("3. Недостаточные права API ключа")
        print("4. Ключи для testnet, а используется mainnet")


if __name__ == "__main__":
    asyncio.run(test_bybit_keys())
