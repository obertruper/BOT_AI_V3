#!/usr/bin/env python3
"""
Быстрый скрипт загрузки исторических данных в БД
Загружает OHLCV данные напрямую с биржи без лишних зависимостей
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import asyncpg
import ccxt.pro as ccxt
from dotenv import load_dotenv

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

# Загружаем переменные окружения
load_dotenv()

# Параметры подключения к БД
DB_USER = os.getenv("PGUSER", "obertruper")
DB_PASSWORD = os.getenv("PGPASSWORD", "")
DB_NAME = os.getenv("PGDATABASE", "bot_trading_v3")
DB_PORT = os.getenv("PGPORT", "5555")
DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@localhost:{DB_PORT}/{DB_NAME}"

# Параметры загрузки
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]


async def create_tables(pool):
    """Создание таблиц если их нет"""
    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS raw_market_data (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(50) NOT NULL,
                exchange VARCHAR(50) NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                open DECIMAL(20, 8) NOT NULL,
                high DECIMAL(20, 8) NOT NULL,
                low DECIMAL(20, 8) NOT NULL,
                close DECIMAL(20, 8) NOT NULL,
                volume DECIMAL(20, 8) NOT NULL,
                timeframe VARCHAR(10) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, exchange, timestamp, timeframe)
            )
        """
        )

        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_raw_market_data_symbol_timestamp
            ON raw_market_data(symbol, timestamp DESC)
        """
        )

        print("✅ Таблицы созданы/проверены")


async def load_symbol_data(exchange, symbol, timeframe, days, pool):
    """Загрузка данных для одного символа"""
    try:
        print(f"📥 Загрузка {symbol} за {days} дней...")

        # Вычисляем временной период
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        # Конвертируем в миллисекунды
        since = int(start_time.timestamp() * 1000)

        # Загружаем данные с биржи
        all_candles = []
        while since < int(end_time.timestamp() * 1000):
            candles = await exchange.fetch_ohlcv(
                symbol, timeframe=timeframe, since=since, limit=1000
            )

            if not candles:
                break

            all_candles.extend(candles)
            since = candles[-1][0] + 1  # Следующая свеча

            # Небольшая задержка чтобы не превысить rate limit
            await asyncio.sleep(0.1)

        print(f"  📊 Загружено {len(all_candles)} свечей")

        # Сохраняем в БД
        if all_candles:
            async with pool.acquire() as conn:
                # Подготавливаем данные для вставки
                values = []
                for candle in all_candles:
                    timestamp = datetime.fromtimestamp(candle[0] / 1000)
                    values.append(
                        (
                            symbol,
                            "bybit",
                            timestamp,
                            float(candle[1]),  # open
                            float(candle[2]),  # high
                            float(candle[3]),  # low
                            float(candle[4]),  # close
                            float(candle[5]),  # volume
                            timeframe,
                        )
                    )

                # Вставляем данные
                await conn.executemany(
                    """
                    INSERT INTO raw_market_data
                    (symbol, exchange, timestamp, open, high, low, close, volume, timeframe)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (symbol, exchange, timestamp, timeframe) DO NOTHING
                """,
                    values,
                )

                print(f"  ✅ {symbol} сохранен в БД")

    except Exception as e:
        print(f"  ❌ Ошибка загрузки {symbol}: {e}")


async def main():
    """Основная функция"""
    print("🚀 Быстрая загрузка исторических данных")
    print(f"📊 БД: {DB_NAME} на порту {DB_PORT}")

    # Параметры из командной строки
    days = 7
    symbols = DEFAULT_SYMBOLS
    timeframe = "15m"

    if len(sys.argv) > 1:
        days = int(sys.argv[1])
    if len(sys.argv) > 2:
        symbols = sys.argv[2].split(",")

    print(f"⏰ Период: {days} дней")
    print(f"📈 Символы: {', '.join(symbols)}")
    print(f"⏱️ Таймфрейм: {timeframe}")

    # Создаем пул подключений к БД
    pool = await asyncpg.create_pool(DB_URL, min_size=5, max_size=10)

    try:
        # Создаем таблицы
        await create_tables(pool)

        # Инициализируем биржу
        exchange = ccxt.bybit(
            {
                "enableRateLimit": True,
                "options": {
                    "defaultType": "linear",  # USDT perpetual
                },
            }
        )

        # Загружаем данные для каждого символа
        for symbol in symbols:
            await load_symbol_data(exchange, symbol, timeframe, days, pool)
            await asyncio.sleep(0.5)  # Пауза между символами

        # Проверяем что загрузилось
        async with pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT COUNT(*) as total, COUNT(DISTINCT symbol) as symbols FROM raw_market_data"
            )
            print("\n📊 ИТОГО В БД:")
            print(f"  Записей: {result['total']}")
            print(f"  Символов: {result['symbols']}")

        await exchange.close()

    finally:
        await pool.close()

    print("\n✅ Загрузка завершена!")


if __name__ == "__main__":
    asyncio.run(main())
