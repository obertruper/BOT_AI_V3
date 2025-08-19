#!/usr/bin/env python3
"""
Добавление тестовых балансов для торговли
"""

import asyncio
import json

import redis.asyncio as redis


async def add_test_balances():
    """Добавляет тестовые балансы через Redis"""

    # Подключаемся к Redis
    redis_client = redis.from_url("redis://localhost:6379/5")

    # Тестовые балансы
    test_balances = {
        "USDT": {"total": "10000", "available": "10000", "locked": "0"},
        "BTC": {"total": "0.5", "available": "0.5", "locked": "0"},
        "ETH": {"total": "5", "available": "5", "locked": "0"},
        "BNB": {"total": "20", "available": "20", "locked": "0"},
        "SOL": {"total": "100", "available": "100", "locked": "0"},
        "XRP": {"total": "10000", "available": "10000", "locked": "0"},
        "DOGE": {"total": "50000", "available": "50000", "locked": "0"},
        "DOT": {"total": "500", "available": "500", "locked": "0"},
        "LINK": {"total": "500", "available": "500", "locked": "0"},
        "ADA": {"total": "10000", "available": "10000", "locked": "0"},
    }

    # Сохраняем балансы в Redis
    for symbol, balance_data in test_balances.items():
        key = f"balance:bybit:{symbol}"
        balance_data["last_updated"] = "2025-08-18T18:40:00"
        await redis_client.setex(key, 3600, json.dumps(balance_data))  # TTL 1 час
        print(f"✅ Добавлен баланс {symbol}: {balance_data['available']}")

    # Также добавим фейковые балансы для exchange_balances
    exchange_balances_key = "exchange_balances:bybit"
    await redis_client.setex(exchange_balances_key, 3600, json.dumps(test_balances))

    print("\n✅ Все тестовые балансы добавлены в Redis")

    # Проверяем что сохранилось
    print("\n📊 Проверка сохраненных балансов:")
    for symbol in test_balances:
        key = f"balance:bybit:{symbol}"
        data = await redis_client.get(key)
        if data:
            balance = json.loads(data)
            print(f"  {symbol}: {balance['available']}")

    await redis_client.close()


if __name__ == "__main__":
    asyncio.run(add_test_balances())
