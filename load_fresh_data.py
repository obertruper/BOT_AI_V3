#!/usr/bin/env python3
"""
Загрузка свежих данных для ML модели
"""

import asyncio
import os
from datetime import datetime
from typing import Any

import pandas as pd

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool
from exchanges.factory import ExchangeFactory

logger = setup_logger("data_loader")


async def load_market_data():
    """Загрузка свежих рыночных данных"""

    logger.info("🚀 Загрузка свежих рыночных данных")

    # Символы для загрузки
    symbols = [
        "BTCUSDT",
        "ETHUSDT",
        "BNBUSDT",
        "SOLUSDT",
        "XRPUSDT",
        "DOGEUSDT",
        "ADAUSDT",
        "AVAXUSDT",
        "DOTUSDT",
        "MATICUSDT",
    ]

    # Создаем клиента биржи
    factory = ExchangeFactory()

    try:
        # Используем публичный доступ для загрузки данных
        client = factory.create_client(
            exchange_type="bybit",
            api_key="public_access",
            api_secret="public_access",
            sandbox=False,
        )

        await client.connect()

        for symbol in symbols:
            try:
                logger.info(f"📥 Загрузка {symbol}...")

                # Загружаем последние 100 свечей 15m
                klines = await client.get_klines(symbol=symbol, interval="15", limit=100)

                if klines:
                    # Сохраняем в БД
                    for kline in klines:
                        await save_kline_to_db(symbol, kline)

                    logger.info(f"  ✅ Загружено {len(klines)} свечей для {symbol}")
                else:
                    logger.warning(f"  ⚠️ Нет данных для {symbol}")

                # Небольшая задержка между запросами
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"  ❌ Ошибка загрузки {symbol}: {e}")
                continue

        await client.disconnect()

    except Exception as e:
        logger.error(f"❌ Ошибка создания клиента: {e}")
        return False

    # Проверяем результат
    query = """
        SELECT
            COUNT(*) as total,
            COUNT(DISTINCT symbol) as symbols,
            MAX(timestamp) as latest
        FROM raw_market_data
        WHERE timestamp > EXTRACT(EPOCH FROM NOW() - INTERVAL '1 hour') * 1000
    """

    result = await AsyncPGPool.fetch(query)
    if result:
        row = result[0]
        logger.info("\n📊 Загружено в БД:")
        logger.info(f"  • Записей: {row['total']}")
        logger.info(f"  • Символов: {row['symbols']}")

        if row["latest"]:
            latest_time = datetime.fromtimestamp(row["latest"] / 1000)
            logger.info(f"  • Последние данные: {latest_time}")

    return True


async def save_kline_to_db(symbol: str, kline: dict[str, Any]):
    """Сохранение свечи в БД"""

    try:
        # Конвертируем данные
        timestamp = int(kline.get("timestamp", kline.get("open_time", 0)))
        if timestamp == 0:
            return

        # Проверяем существование записи
        check_query = """
            SELECT id FROM raw_market_data
            WHERE symbol = $1 AND timestamp = $2 AND exchange = 'bybit'
        """
        existing = await AsyncPGPool.fetch(check_query, symbol, timestamp)

        if existing:
            # Обновляем существующую запись
            update_query = """
                UPDATE raw_market_data
                SET open = $3, high = $4, low = $5, close = $6, volume = $7,
                    updated_at = NOW()
                WHERE symbol = $1 AND timestamp = $2 AND exchange = 'bybit'
            """
            await AsyncPGPool.execute(
                update_query,
                symbol,
                timestamp,
                float(kline.get("open", 0)),
                float(kline.get("high", 0)),
                float(kline.get("low", 0)),
                float(kline.get("close", 0)),
                float(kline.get("volume", 0)),
            )
        else:
            # Вставляем новую запись
            insert_query = """
                INSERT INTO raw_market_data
                (symbol, timestamp, exchange, open, high, low, close, volume, timeframe)
                VALUES ($1, $2, 'bybit', $3, $4, $5, $6, $7, '15m')
                ON CONFLICT (symbol, timestamp, exchange) DO UPDATE
                SET open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    updated_at = NOW()
            """
            await AsyncPGPool.execute(
                insert_query,
                symbol,
                timestamp,
                float(kline.get("open", 0)),
                float(kline.get("high", 0)),
                float(kline.get("low", 0)),
                float(kline.get("close", 0)),
                float(kline.get("volume", 0)),
            )

    except Exception as e:
        logger.debug(f"Ошибка сохранения {symbol}: {e}")


async def process_market_data():
    """Обработка загруженных данных для ML"""

    logger.info("\n🔧 Обработка данных для ML...")

    try:
        # Получаем последние сырые данные
        query = """
            SELECT DISTINCT symbol
            FROM raw_market_data
            WHERE timestamp > EXTRACT(EPOCH FROM NOW() - INTERVAL '2 hours') * 1000
        """

        symbols = await AsyncPGPool.fetch(query)

        for row in symbols:
            symbol = row["symbol"]

            # Получаем данные для обработки
            data_query = """
                SELECT *
                FROM raw_market_data
                WHERE symbol = $1
                  AND timestamp > EXTRACT(EPOCH FROM NOW() - INTERVAL '24 hours') * 1000
                ORDER BY timestamp ASC
            """

            raw_data = await AsyncPGPool.fetch(data_query, symbol)

            if len(raw_data) < 20:
                logger.debug(f"Недостаточно данных для {symbol}")
                continue

            # Конвертируем в DataFrame
            df = pd.DataFrame([dict(r) for r in raw_data])

            # Вычисляем технические индикаторы
            df["rsi"] = calculate_rsi(df["close"].astype(float))
            df["macd"] = calculate_macd(df["close"].astype(float))
            df["bb_upper"], df["bb_lower"] = calculate_bollinger_bands(df["close"].astype(float))
            df["ema_short"] = df["close"].astype(float).ewm(span=9).mean()
            df["ema_long"] = df["close"].astype(float).ewm(span=21).mean()

            # Сохраняем обработанные данные
            for idx, row in df.iterrows():
                if pd.isna(row["rsi"]) or pd.isna(row["macd"]):
                    continue

                tech_indicators = {
                    "rsi": float(row["rsi"]),
                    "macd": float(row["macd"]),
                    "bb_upper": float(row["bb_upper"]),
                    "bb_lower": float(row["bb_lower"]),
                    "ema_short": float(row["ema_short"]),
                    "ema_long": float(row["ema_long"]),
                }

                # Вставляем в processed_market_data
                insert_query = """
                    INSERT INTO processed_market_data
                    (raw_data_id, symbol, timestamp, datetime,
                     open, high, low, close, volume, technical_indicators)
                    VALUES ($1, $2, $3, to_timestamp($3/1000), $4, $5, $6, $7, $8, $9::jsonb)
                    ON CONFLICT (raw_data_id) DO UPDATE
                    SET technical_indicators = EXCLUDED.technical_indicators,
                        updated_at = NOW()
                """

                await AsyncPGPool.execute(
                    insert_query,
                    int(row["id"]),
                    symbol,
                    int(row["timestamp"]),
                    float(row["open"]),
                    float(row["high"]),
                    float(row["low"]),
                    float(row["close"]),
                    float(row["volume"]),
                    json.dumps(tech_indicators),
                )

            logger.info(f"  ✅ Обработано {len(df)} записей для {symbol}")

    except Exception as e:
        logger.error(f"❌ Ошибка обработки: {e}")
        import traceback

        logger.error(traceback.format_exc())


def calculate_rsi(prices, period=14):
    """Расчет RSI"""

    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Расчет MACD"""
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    macd = ema_fast - ema_slow
    return macd


def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """Расчет полос Боллинджера"""
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return upper, lower


async def main():
    """Основная функция"""

    logger.info("=" * 60)
    logger.info("📊 ЗАГРУЗКА И ОБРАБОТКА ДАННЫХ ДЛЯ ML")
    logger.info("=" * 60)

    # Загружаем свежие данные
    success = await load_market_data()

    if success:
        # Обрабатываем для ML
        await process_market_data()

        # Проверяем результат
        logger.info("\n✅ Данные успешно загружены и обработаны!")

        # Запускаем проверку качества
        logger.info("\n🔍 Проверка качества данных...")
        os.system("python check_ml_data_quality_v2.py")
    else:
        logger.error("❌ Ошибка загрузки данных")


if __name__ == "__main__":
    import json

    asyncio.run(main())
