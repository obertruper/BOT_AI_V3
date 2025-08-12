#!/usr/bin/env python3
"""
Тестируем подпись API запросов Bybit
"""

import hashlib
import hmac
import json
import os
import time

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


def test_signature():
    """Тестируем генерацию подписи"""

    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")

    print("📊 Тестирование API подписи Bybit")
    print("=" * 50)
    print(f"API Key из .env: '{api_key}'")
    print(f"API Key длина: {len(api_key)} символов")
    print(f"API Secret из .env: '{api_secret}'")
    print(f"API Secret длина: {len(api_secret)} символов")
    print("=" * 50)

    # Проверяем, не содержат ли ключи лишние символы
    print("\n🔍 Проверка на лишние символы:")
    print(f"Первый символ key: ord('{api_key[0]}') = {ord(api_key[0])}")
    print(f"Последний символ key: ord('{api_key[-1]}') = {ord(api_key[-1])}")
    print(f"Первый символ secret: ord('{api_secret[0]}') = {ord(api_secret[0])}")
    print(f"Последний символ secret: ord('{api_secret[-1]}') = {ord(api_secret[-1])}")

    # Проверяем на невидимые символы
    import string

    printable = set(string.printable)

    non_printable_key = [c for c in api_key if c not in printable]
    non_printable_secret = [c for c in api_secret if c not in printable]

    if non_printable_key:
        print(f"⚠️ Непечатаемые символы в API key: {non_printable_key}")
    if non_printable_secret:
        print(f"⚠️ Непечатаемые символы в API secret: {non_printable_secret}")

    # Тестируем подпись как в Bybit
    print("\n📝 Генерация тестовой подписи:")
    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"

    # Для GET запроса к /v5/account/wallet-balance
    params = "accountType=UNIFIED&coin=USDT"

    # Формируем строку для подписи (GET запрос)
    param_str = timestamp + api_key + recv_window + params
    print(f"Строка для подписи: {param_str[:50]}...")

    # Генерируем подпись
    signature = hmac.new(
        bytes(api_secret, "utf-8"), bytes(param_str, "utf-8"), hashlib.sha256
    ).hexdigest()

    print(f"Подпись: {signature}")
    print(f"Длина подписи: {len(signature)} символов")

    # Теперь пробуем реальный запрос
    print("\n🌐 Тестовый запрос к Bybit API:")
    import asyncio

    import aiohttp

    async def test_request():
        url = "https://api.bybit.com/v5/account/wallet-balance"

        headers = {
            "X-BAPI-API-KEY": api_key,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-SIGN": signature,
            "X-BAPI-RECV-WINDOW": recv_window,
        }

        params = {"accountType": "UNIFIED", "coin": "USDT"}

        print(f"Headers: {json.dumps(headers, indent=2)}")
        print(f"Params: {params}")

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                status = response.status
                text = await response.text()

                print("\n📨 Ответ от Bybit:")
                print(f"Статус: {status}")
                print(f"Тело ответа: {text[:500]}")

                if status == 200:
                    data = json.loads(text)
                    if data.get("retCode") == 0:
                        print("✅ Аутентификация успешна!")
                    else:
                        print(f"❌ Ошибка API: {data.get('retMsg')}")
                else:
                    print(f"❌ HTTP ошибка: {status}")

    asyncio.run(test_request())


if __name__ == "__main__":
    test_signature()
