#!/usr/bin/env python3
"""
Тест аутентификации Bybit API
"""

import asyncio
import hashlib
import hmac
import os
import sys
import time

from dotenv import load_dotenv

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()


async def test_raw_api():
    """Тест прямого API запроса"""
    import aiohttp

    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")

    print(f"API Key: {api_key}")
    print(f"API Secret length: {len(api_secret) if api_secret else 0}")

    # Создаем подпись
    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"

    # Для GET запроса
    param_str = "accountType=UNIFIED"
    sign_str = f"{timestamp}{api_key}{recv_window}{param_str}"

    signature = hmac.new(
        api_secret.encode("utf-8"), sign_str.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    headers = {
        "X-BAPI-API-KEY": api_key,
        "X-BAPI-SIGN": signature,
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-RECV-WINDOW": recv_window,
        "Content-Type": "application/json",
    }

    print("\nHeaders:")
    for k, v in headers.items():
        if k == "X-BAPI-SIGN":
            print(f"  {k}: {v[:10]}...")
        else:
            print(f"  {k}: {v}")

    url = f"https://api.bybit.com/v5/account/wallet-balance?{param_str}"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                status = response.status
                text = await response.text()
                print(f"\nStatus: {status}")
                print(f"Response: {text[:200]}...")

                if status == 200:
                    import json

                    data = json.loads(text)
                    if data.get("retCode") == 0:
                        print("\n✅ Аутентификация успешна!")
                        if "result" in data and "list" in data["result"]:
                            for account in data["result"]["list"]:
                                for coin in account.get("coin", []):
                                    if coin["coin"] == "USDT":
                                        print("\nUSDT баланс:")
                                        print(
                                            f"  Wallet: {coin.get('walletBalance', 'N/A')}"
                                        )
                                        print(
                                            f"  Available: {coin.get('availableBalance', 'N/A')}"
                                        )
                    else:
                        print(f"\n❌ API Error: {data.get('retMsg', 'Unknown error')}")

        except Exception as e:
            print(f"\n❌ Request error: {e}")


async def main():
    """Главная функция"""
    print("=== Тест аутентификации Bybit API ===\n")

    await test_raw_api()


if __name__ == "__main__":
    asyncio.run(main())
