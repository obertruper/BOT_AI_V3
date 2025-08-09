#!/usr/bin/env python3
"""
Проверка текущих цен
"""

import asyncio
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()


async def check_current_prices():
    from exchanges.bybit.bybit_exchange import BybitExchange

    exchange = BybitExchange(
        api_key=os.getenv("BYBIT_API_KEY"),
        api_secret=os.getenv("BYBIT_API_SECRET"),
        sandbox=False,
    )

    try:
        await exchange.connect()

        # Получаем текущие цены
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

        print(f"⏰ Текущее время: {datetime.now()}\n")
        print("💲 ТЕКУЩИЕ ЦЕНЫ:")

        for symbol in symbols:
            ticker = await exchange.get_ticker(symbol)
            print(
                f"   {symbol}: ${ticker.last_price:.2f} (время биржи: {ticker.timestamp})"
            )

        # Проверяем последние свечи
        print("\n📊 ПОСЛЕДНИЕ СВЕЧИ (15м):")

        for symbol in symbols:
            candles = await exchange.get_candles(symbol, 15, limit=1)
            if candles:
                candle = candles[0]
                print(
                    f"   {symbol}: открытие в {candle.timestamp.strftime('%H:%M')}, цена: ${candle.close_price:.2f}"
                )

    finally:
        await exchange.disconnect()


if __name__ == "__main__":
    asyncio.run(check_current_prices())
