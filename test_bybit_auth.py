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
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

import aiohttp
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


async def test_bybit_auth():
    """Проверка аутентификации с Bybit API"""

    # Получаем ключи из .env
    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")
    testnet = os.getenv("BYBIT_TESTNET", "false").lower() == "true"

    print("🔍 Проверка Bybit API ключей")
    print(f"   API Key: {api_key[:10]}..." if api_key else "   ❌ API Key не найден")
    print(f"   API Secret: {'*' * 10}" if api_secret else "   ❌ API Secret не найден")
    print(f"   Testnet: {testnet}")
    print()

    if not api_key or not api_secret:
        print("❌ API ключи не найдены в .env файле")
        return

    # URL для API
    base_url = "https://api-testnet.bybit.com" if testnet else "https://api.bybit.com"

    # Тест 1: Проверка баланса (требует аутентификации)
    print("📊 Тест 1: Получение баланса аккаунта")

    endpoint = "/v5/account/wallet-balance"
    url = f"{base_url}{endpoint}"

    # Параметры запроса
    params = {"accountType": "UNIFIED"}

    # Генерация подписи
    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"

    # Формируем строку для подписи (для GET запроса)
    param_str = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    sign_str = timestamp + api_key + recv_window + param_str

    # Создаем подпись
    signature = hmac.new(
        bytes(api_secret, "utf-8"), bytes(sign_str, "utf-8"), hashlib.sha256
    ).hexdigest()

    # Заголовки
    headers = {
        "X-BAPI-API-KEY": api_key,
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-SIGN": signature,
        "X-BAPI-RECV-WINDOW": recv_window,
    }

    print(f"   URL: {url}")
    print(f"   Параметры: {params}")
    print(f"   Timestamp: {timestamp}")
    print(f"   Signature: {signature[:20]}...")
    print()

    # Выполняем запрос
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, headers=headers) as response:
                data = await response.json()

                if data.get("retCode") == 0:
                    print("✅ Аутентификация успешна!")

                    # Показываем баланс
                    if data.get("result", {}).get("list"):
                        for wallet in data["result"]["list"]:
                            print(f"\n💰 Кошелек: {wallet.get('accountType')}")
                            if wallet.get("coin"):
                                for coin_info in wallet["coin"]:
                                    balance = float(coin_info.get("walletBalance", 0))
                                    if balance > 0:
                                        print(
                                            f"   • {coin_info['coin']}: {balance:.4f}"
                                        )
                else:
                    print("❌ Ошибка аутентификации:")
                    print(f"   Код: {data.get('retCode')}")
                    print(f"   Сообщение: {data.get('retMsg')}")

                    # Детальная информация об ошибке
                    if data.get("retCode") == 10003:
                        print("\n⚠️  Возможные причины:")
                        print("   1. Неверный API ключ или секрет")
                        print("   2. API ключи для testnet/mainnet перепутаны")
                        print("   3. IP адрес не в белом списке")
                        print("   4. Неправильная генерация подписи")

        except Exception as e:
            print(f"❌ Ошибка запроса: {e}")

    # Тест 2: Публичный запрос (без аутентификации)
    print("\n📊 Тест 2: Публичный запрос (тикеры)")

    public_url = f"{base_url}/v5/market/tickers"
    public_params = {"category": "linear", "symbol": "BTCUSDT"}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(public_url, params=public_params) as response:
                data = await response.json()

                if data.get("retCode") == 0:
                    print("✅ Публичный API работает")
                    if data.get("result", {}).get("list"):
                        ticker = data["result"]["list"][0]
                        print(f"   BTCUSDT: ${ticker.get('lastPrice', 'N/A')}")
                else:
                    print(f"❌ Ошибка публичного API: {data.get('retMsg')}")

        except Exception as e:
            print(f"❌ Ошибка запроса: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("🔧 ТЕСТ АУТЕНТИФИКАЦИИ BYBIT API")
    print("=" * 60)
    asyncio.run(test_bybit_auth())
    print("\n" + "=" * 60)
