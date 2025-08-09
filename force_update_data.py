#!/usr/bin/env python3
"""
Принудительное обновление данных
"""

import asyncio
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

# Устанавливаем переменные окружения
os.environ["PGPORT"] = "5555"
os.environ["PGUSER"] = "obertruper"
os.environ["PGDATABASE"] = "bot_trading_v3"


async def force_update():
    """Принудительное обновление данных"""
    from database.connections.postgres import AsyncPGPool
    from exchanges.bybit.bybit_exchange import BybitExchange

    print(
        f"\n🔄 ПРИНУДИТЕЛЬНОЕ ОБНОВЛЕНИЕ ДАННЫХ - {datetime.now().strftime('%H:%M:%S')}"
    )
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
                # Получаем последние данные
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
                    # Убираем timezone info для сравнения
                    latest_naive = latest.replace(tzinfo=None)
                    start_time = latest_naive + timedelta(minutes=interval_minutes)
                else:
                    start_time = datetime.now() - timedelta(days=7)

                end_time = datetime.now()

                print(
                    f"   Загружаем с {start_time.strftime('%Y-%m-%d %H:%M')} до {end_time.strftime('%Y-%m-%d %H:%M')}"
                )

                # Получаем свечи
                candles = await exchange.get_candles(
                    symbol=symbol,
                    interval_minutes=interval_minutes,
                    start_time=start_time,
                    end_time=end_time,
                    limit=1000,
                )

                if candles:
                    print(f"   Получено {len(candles)} свечей")

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
                                int(
                                    candle.timestamp.timestamp() * 1000
                                ),  # Unix timestamp в миллисекундах
                                candle.open_price,
                                candle.high_price,
                                candle.low_price,
                                candle.close_price,
                                candle.volume,
                                interval_minutes,
                                "bybit",
                            )
                            saved += 1
                        except Exception as e:
                            print(f"      ⚠️ Ошибка сохранения свечи: {e}")

                    print(f"   ✅ Сохранено {saved} свечей")

                    # Проверяем актуальность
                    new_latest = await pool.fetchval(
                        """
                        SELECT MAX(datetime)
                        FROM raw_market_data
                        WHERE symbol = $1 AND interval_minutes = $2
                    """,
                        symbol,
                        interval_minutes,
                    )

                    if new_latest:
                        lag = datetime.now() - new_latest.replace(tzinfo=None)
                        lag_minutes = int(lag.total_seconds() / 60)
                        print(
                            f"   📈 Данные обновлены, отставание: {lag_minutes} минут"
                        )
                else:
                    print("   ❌ Нет новых данных")

            except Exception as e:
                print(f"   ❌ Ошибка обновления {symbol}: {e}")

        print("\n✅ Обновление завершено!")

        # Проверяем общую статистику
        print("\n📊 ОБЩАЯ СТАТИСТИКА:")

        stats = await pool.fetch(
            """
            SELECT
                symbol,
                COUNT(*) as count,
                MIN(datetime) as first,
                MAX(datetime) as last
            FROM raw_market_data
            WHERE interval_minutes = 15
                AND symbol IN ('BTCUSDT', 'ETHUSDT', 'SOLUSDT')
            GROUP BY symbol
            ORDER BY symbol
        """
        )

        for stat in stats:
            lag = datetime.now() - stat["last"].replace(tzinfo=None)
            lag_minutes = int(lag.total_seconds() / 60)
            print(
                f"   {stat['symbol']}: {stat['count']} свечей, последняя {lag_minutes} мин назад"
            )

    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await exchange.disconnect()
        await AsyncPGPool.close_pool()


if __name__ == "__main__":
    asyncio.run(force_update())
