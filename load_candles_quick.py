#!/usr/bin/env python3
"""
Быстрая загрузка свечей для ML
"""

import asyncio
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

# Устанавливаем переменные окружения
os.environ["PGPORT"] = "5555"
os.environ["PGUSER"] = "obertruper"
os.environ["PGDATABASE"] = "bot_trading_v3"


async def load_candles():
    """Загрузка свечей через Bybit API"""
    print("🚀 Загрузка исторических данных для ML...")

    from database.connections.postgres import AsyncPGPool
    from exchanges.bybit.client import BybitClient

    # Инициализация клиента
    client = BybitClient(
        api_key=os.getenv("BYBIT_API_KEY"),
        api_secret=os.getenv("BYBIT_API_SECRET"),
        sandbox=False,
    )

    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
    interval = "15"  # 15 минут
    limit = 200  # Максимум свечей за запрос

    for symbol in symbols:
        print(f"\n📊 Загрузка данных для {symbol}...")

        try:
            # Получаем свечи через API
            params = {
                "category": "linear",
                "symbol": symbol,
                "interval": interval,
                "limit": limit,
            }

            response = await client._make_request("GET", "/v5/market/kline", params)

            if response and "list" in response:
                candles = response["list"]
                print(f"  Получено {len(candles)} свечей")

                # Сохраняем в БД
                saved = 0
                for candle in reversed(candles):  # От старых к новым
                    timestamp = datetime.fromtimestamp(int(candle[0]) / 1000)

                    await AsyncPGPool.execute(
                        """
                        INSERT INTO raw_market_data
                        (symbol, timeframe, timestamp, open, high, low, close, volume)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        ON CONFLICT (symbol, timeframe, timestamp) DO NOTHING
                    """,
                        symbol,
                        "15m",
                        timestamp,
                        float(candle[1]),
                        float(candle[2]),
                        float(candle[3]),
                        float(candle[4]),
                        float(candle[5]),
                    )
                    saved += 1

                print(f"  ✅ Сохранено {saved} свечей в БД")

            else:
                print("  ❌ Нет данных")

        except Exception as e:
            print(f"  ❌ Ошибка: {e}")

    # Проверка количества данных
    print("\n📈 Проверка загруженных данных:")
    for symbol in symbols:
        count = await AsyncPGPool.fetchval(
            """
            SELECT COUNT(*) FROM raw_market_data
            WHERE symbol = $1 AND timeframe = '15m'
            AND timestamp > NOW() - INTERVAL '7 days'
        """,
            symbol,
        )
        print(f"  {symbol}: {count} свечей за последние 7 дней")


if __name__ == "__main__":
    asyncio.run(load_candles())
