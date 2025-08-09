#!/usr/bin/env python3
"""
Тест получения свечей с биржи
"""

import asyncio
from datetime import datetime, timedelta

from exchanges.factory import get_exchange_factory


async def test_candles():
    """Тест получения свечей"""

    # Создаем фабрику
    factory = get_exchange_factory()

    # Создаем клиент Bybit
    exchange = factory.create_client(
        "bybit",
        api_key="dckOW0zIY2jb15f1P7",
        api_secret="M40KthE65wqknDA2vs0XWScN4RZGpH9TeUqt",
        sandbox=False,
    )

    print(f"Создан клиент: {exchange.name}")

    # Подключаемся
    connected = await exchange.connect()
    print(f"Подключение: {connected}")

    # Пробуем получить свечи
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=2)

        candles = await exchange.get_candles(
            symbol="BTCUSDT",
            interval_minutes=15,
            start_time=start_time,
            end_time=end_time,
            limit=10,
        )

        print(f"Получено свечей: {len(candles)}")

        if candles:
            print(f"Первая свеча: {candles[0]}")

    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback

        traceback.print_exc()

    finally:
        await exchange.disconnect()


if __name__ == "__main__":
    asyncio.run(test_candles())
