#!/usr/bin/env python3
"""
Обновление последних данных
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


async def update_recent():
    """Обновление последних данных"""
    from database.connections.postgres import AsyncPGPool
    from exchanges.bybit.bybit_exchange import BybitExchange

    print(f"\n🔄 ОБНОВЛЕНИЕ ПОСЛЕДНИХ ДАННЫХ - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)

    exchange = BybitExchange(
        api_key=os.getenv("BYBIT_API_KEY"),
        api_secret=os.getenv("BYBIT_API_SECRET"),
        sandbox=False,
    )

    try:
        await exchange.connect()
        pool = await AsyncPGPool.get_pool()

        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        interval_minutes = 15

        for symbol in symbols:
            print(f"\n📊 Обновляем {symbol}...")

            try:
                # Получаем последние 200 свечей (50 часов)
                candles = await exchange.get_candles(
                    symbol=symbol, interval_minutes=interval_minutes, limit=200
                )

                if candles:
                    print(f"   Получено {len(candles)} свечей")
                    print(f"   Первая: {candles[0].timestamp}")
                    print(f"   Последняя: {candles[-1].timestamp}")

                    # Сохраняем в БД
                    saved = 0
                    for candle in candles:
                        try:
                            await pool.execute(
                                """
                                INSERT INTO raw_market_data
                                (symbol, datetime, timestamp, open, high, low, close, volume, interval_minutes, exchange)
                                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                                ON CONFLICT (symbol, timestamp, interval_minutes, exchange)
                                DO UPDATE SET
                                    datetime = EXCLUDED.datetime,
                                    open = EXCLUDED.open,
                                    high = EXCLUDED.high,
                                    low = EXCLUDED.low,
                                    close = EXCLUDED.close,
                                    volume = EXCLUDED.volume
                            """,
                                symbol,
                                candle.timestamp,
                                int(candle.timestamp.timestamp() * 1000),
                                candle.open_price,
                                candle.high_price,
                                candle.low_price,
                                candle.close_price,
                                candle.volume,
                                interval_minutes,
                                "bybit",
                            )
                            saved += 1
                        except Exception:
                            pass  # Игнорируем дубликаты

                    print(f"   ✅ Сохранено/обновлено {saved} свечей")

                    # Проверяем актуальность
                    latest = await pool.fetchval(
                        """
                        SELECT MAX(datetime)
                        FROM raw_market_data
                        WHERE symbol = $1 AND interval_minutes = $2
                    """,
                        symbol,
                        interval_minutes,
                    )

                    if latest:
                        lag = datetime.now() - latest.replace(tzinfo=None)
                        lag_minutes = int(lag.total_seconds() / 60)
                        status = "✅" if lag_minutes < 30 else "⚠️"
                        print(
                            f"   {status} Данные актуальны, отставание: {lag_minutes} минут"
                        )
                else:
                    print("   ❌ Нет данных")

            except Exception as e:
                print(f"   ❌ Ошибка: {e}")

        print("\n✅ Обновление завершено!")

    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await exchange.disconnect()
        await AsyncPGPool.close_pool()


if __name__ == "__main__":
    asyncio.run(update_recent())
