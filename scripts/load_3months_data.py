#!/usr/bin/env python3
"""
Скрипт загрузки исторических данных за 3 месяца
Обеспечивает полную загрузку данных для ML системы
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import asyncpg
import ccxt.pro as ccxt
from dotenv import load_dotenv

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config.config_manager import ConfigManager
from core.logger import setup_logger

# Загружаем переменные окружения
load_dotenv()

logger = setup_logger("load_3months_data")

# Параметры подключения к БД
DB_USER = os.getenv("PGUSER", "obertruper")
DB_PASSWORD = os.getenv("PGPASSWORD", "")
DB_NAME = os.getenv("PGDATABASE", "bot_trading_v3")
DB_PORT = os.getenv("PGPORT", "5555")
DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@localhost:{DB_PORT}/{DB_NAME}"


async def create_tables(pool):
    """Создание таблиц если их нет"""
    async with pool.acquire() as conn:
        # Проверяем что таблица уже существует с правильной структурой
        result = await conn.fetchrow(
            """
            SELECT COUNT(*) as count
            FROM information_schema.tables
            WHERE table_name = 'raw_market_data'
        """
        )

        if result["count"] > 0:
            logger.info("✅ Таблица raw_market_data уже существует")
        else:
            # Создаем таблицу только если её нет
            await conn.execute(
                """
                CREATE TABLE raw_market_data (
                    id BIGSERIAL PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    timestamp BIGINT NOT NULL,
                    datetime TIMESTAMP WITH TIME ZONE NOT NULL,
                    open DECIMAL(20, 8) NOT NULL,
                    high DECIMAL(20, 8) NOT NULL,
                    low DECIMAL(20, 8) NOT NULL,
                    close DECIMAL(20, 8) NOT NULL,
                    volume DECIMAL(20, 8) NOT NULL,
                    turnover DECIMAL(20, 8),
                    interval_minutes INTEGER NOT NULL,
                    market_type markettype,
                    exchange VARCHAR(50),
                    open_interest DECIMAL(20, 8),
                    funding_rate DECIMAL(10, 8),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """
            )
            logger.info("✅ Таблица raw_market_data создана")

        # Индексы для оптимизации (проверяем что их еще нет)
        try:
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_raw_market_data_symbol_datetime_interval
                ON raw_market_data(symbol, datetime DESC, interval_minutes)
            """
            )
            logger.info("✅ Индексы проверены/созданы")
        except Exception as e:
            logger.warning(f"⚠️ Индексы уже существуют: {e}")

        # Таблица статистики загрузки
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS data_maintenance_log (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(50) NOT NULL,
                exchange VARCHAR(50) NOT NULL,
                interval_minutes INTEGER NOT NULL,
                start_date TIMESTAMP WITH TIME ZONE NOT NULL,
                end_date TIMESTAMP WITH TIME ZONE NOT NULL,
                records_loaded INTEGER NOT NULL,
                gaps_found INTEGER DEFAULT 0,
                execution_time_seconds FLOAT,
                status VARCHAR(20) NOT NULL,
                error_message TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """
        )

        logger.info("✅ Таблицы созданы/проверены")


async def check_existing_data(
    pool, symbol: str, exchange: str, interval_minutes: int
) -> Dict[str, Any]:
    """Проверка существующих данных для символа"""
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            """
            SELECT
                COUNT(*) as count,
                MIN(datetime) as min_date,
                MAX(datetime) as max_date
            FROM raw_market_data
            WHERE symbol = $1 AND exchange = $2 AND interval_minutes = $3
        """,
            symbol,
            exchange,
            interval_minutes,
        )

        return {
            "count": result["count"],
            "min_date": result["min_date"],
            "max_date": result["max_date"],
        }


async def find_data_gaps(
    pool,
    symbol: str,
    exchange: str,
    interval_minutes: int,
    start_date: datetime,
    end_date: datetime,
) -> List[Dict]:
    """Поиск пропусков в данных"""
    async with pool.acquire() as conn:
        # Получаем все временные метки
        rows = await conn.fetch(
            """
            SELECT datetime
            FROM raw_market_data
            WHERE symbol = $1 AND exchange = $2 AND interval_minutes = $3
                AND datetime >= $4 AND datetime <= $5
            ORDER BY datetime
        """,
            symbol,
            exchange,
            interval_minutes,
            start_date,
            end_date,
        )

        if len(rows) < 2:
            return []

        gaps = []
        expected_delta = timedelta(minutes=interval_minutes)

        for i in range(1, len(rows)):
            prev_time = rows[i - 1]["datetime"]
            curr_time = rows[i]["datetime"]
            actual_delta = curr_time - prev_time

            if actual_delta > expected_delta * 1.5:  # Пропуск больше 1.5 интервалов
                gaps.append(
                    {
                        "start": prev_time,
                        "end": curr_time,
                        "missing_candles": int(
                            actual_delta.total_seconds() / 60 / interval_minutes
                        )
                        - 1,
                    }
                )

        return gaps


async def load_symbol_data(
    exchange,
    symbol: str,
    interval_minutes: int,
    start_date: datetime,
    end_date: datetime,
    pool,
) -> Dict[str, Any]:
    """Загрузка данных для одного символа с учетом пропусков"""
    start_time = datetime.now()
    stats = {
        "symbol": symbol,
        "loaded": 0,
        "gaps_filled": 0,
        "errors": 0,
        "status": "success",
    }

    try:
        # Проверяем существующие данные
        existing = await check_existing_data(pool, symbol, "bybit", interval_minutes)
        logger.info(f"📊 {symbol}: найдено {existing['count']} записей")

        # Определяем периоды для загрузки
        if existing["count"] > 0 and existing["max_date"]:
            # Проверяем пропуски
            gaps = await find_data_gaps(
                pool,
                symbol,
                "bybit",
                interval_minutes,
                start_date,
                existing["max_date"],
            )

            if gaps:
                logger.warning(f"⚠️ {symbol}: найдено {len(gaps)} пропусков в данных")

            # Загружаем только новые данные
            if existing["max_date"] < end_date:
                load_start = existing["max_date"] + timedelta(minutes=interval_minutes)
            else:
                logger.info(f"✅ {symbol}: данные уже актуальны")
                return stats
        else:
            load_start = start_date
            gaps = []

        # Загружаем данные частями
        current_start = load_start
        all_candles = []

        while current_start < end_date:
            since = int(current_start.timestamp() * 1000)

            try:
                # Преобразуем interval_minutes в timeframe
                timeframe_str = f"{interval_minutes}m"
                candles = await exchange.fetch_ohlcv(
                    symbol, timeframe=timeframe_str, since=since, limit=1000
                )

                if not candles:
                    break

                all_candles.extend(candles)

                # Обновляем позицию
                last_timestamp = candles[-1][0]
                current_start = datetime.fromtimestamp(
                    last_timestamp / 1000
                ) + timedelta(minutes=interval_minutes)

                # Небольшая задержка для rate limit
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"❌ {symbol}: ошибка загрузки части данных: {e}")
                stats["errors"] += 1
                await asyncio.sleep(1)
                continue

        # Сохраняем в БД
        if all_candles:
            async with pool.acquire() as conn:
                values = []
                for candle in all_candles:
                    timestamp_ms = candle[0]
                    timestamp_dt = datetime.fromtimestamp(timestamp_ms / 1000)
                    values.append(
                        (
                            symbol,
                            timestamp_ms,  # timestamp as bigint
                            timestamp_dt,  # datetime as timestamptz
                            float(candle[1]),  # open
                            float(candle[2]),  # high
                            float(candle[3]),  # low
                            float(candle[4]),  # close
                            float(candle[5]),  # volume
                            interval_minutes,
                            "bybit",  # exchange
                        )
                    )

                # Вставляем данные
                result = await conn.executemany(
                    """
                    INSERT INTO raw_market_data
                    (symbol, timestamp, datetime, open, high, low, close, volume, interval_minutes, exchange)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (symbol, timestamp, interval_minutes, exchange) DO NOTHING
                """,
                    values,
                )

                stats["loaded"] = len(all_candles)
                logger.info(f"✅ {symbol}: загружено {stats['loaded']} новых свечей")

        # Логируем операцию
        execution_time = (datetime.now() - start_time).total_seconds()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO data_maintenance_log
                (symbol, exchange, interval_minutes, start_date, end_date,
                 records_loaded, gaps_found, execution_time_seconds, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
                symbol,
                "bybit",
                interval_minutes,
                load_start,
                end_date,
                stats["loaded"],
                len(gaps),
                execution_time,
                stats["status"],
            )

    except Exception as e:
        logger.error(f"❌ {symbol}: критическая ошибка: {e}")
        stats["status"] = "error"
        stats["error"] = str(e)

        # Логируем ошибку
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO data_maintenance_log
                (symbol, exchange, interval_minutes, start_date, end_date,
                 records_loaded, execution_time_seconds, status, error_message)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
                symbol,
                "bybit",
                interval_minutes,
                start_date,
                end_date,
                0,
                0,
                "error",
                str(e),
            )

    return stats


async def load_symbols_batch(
    exchange,
    symbols: List[str],
    interval_minutes: int,
    start_date: datetime,
    end_date: datetime,
    pool,
    batch_size: int = 5,
):
    """Загрузка символов пакетами для оптимизации"""
    all_stats = []

    # Разбиваем на батчи
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i : i + batch_size]
        logger.info(
            f"\n📦 Загрузка батча {i // batch_size + 1}/{(len(symbols) + batch_size - 1) // batch_size}"
        )

        # Загружаем батч параллельно
        tasks = []
        for symbol in batch:
            task = load_symbol_data(
                exchange, symbol, interval_minutes, start_date, end_date, pool
            )
            tasks.append(task)

        # Ждем завершения батча
        batch_stats = await asyncio.gather(*tasks)
        all_stats.extend(batch_stats)

        # Пауза между батчами
        if i + batch_size < len(symbols):
            await asyncio.sleep(2)

    return all_stats


async def main():
    """Основная функция"""
    logger.info("🚀 Загрузка данных за 3 месяца")
    logger.info(f"📊 БД: {DB_NAME} на порту {DB_PORT}")

    # Инициализируем конфигурацию
    config_manager = ConfigManager()
    await config_manager.initialize()

    # Получаем символы из конфигурации
    ml_config = config_manager.get_ml_config()
    symbols = ml_config.get("symbols", [])

    if not symbols:
        logger.error("❌ Нет символов в конфигурации!")
        return

    # Параметры загрузки
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)  # 3 месяца
    interval_minutes = 15  # 15-минутные свечи

    logger.info(
        f"📅 Период: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}"
    )
    logger.info(f"📈 Символы ({len(symbols)}): {', '.join(symbols[:5])}...")
    logger.info(f"⏱️ Интервал: {interval_minutes} минут")

    # Создаем пул подключений к БД
    pool = await asyncpg.create_pool(DB_URL, min_size=5, max_size=20)

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

        # Загружаем данные пакетами
        logger.info("\n🔄 Начинаем загрузку данных...")
        all_stats = await load_symbols_batch(
            exchange,
            symbols,
            interval_minutes,
            start_date,
            end_date,
            pool,
            batch_size=5,
        )

        # Статистика
        total_loaded = sum(s["loaded"] for s in all_stats)
        successful = sum(1 for s in all_stats if s["status"] == "success")
        failed = sum(1 for s in all_stats if s["status"] == "error")

        logger.info("\n" + "=" * 60)
        logger.info("📊 ИТОГОВАЯ СТАТИСТИКА:")
        logger.info(f"✅ Успешно обработано: {successful} символов")
        logger.info(f"❌ С ошибками: {failed} символов")
        logger.info(f"📈 Всего загружено свечей: {total_loaded:,}")

        # Проверяем общую статистику в БД
        async with pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT
                    COUNT(DISTINCT symbol) as symbols,
                    COUNT(*) as total_records,
                    MIN(datetime) as min_date,
                    MAX(datetime) as max_date
                FROM raw_market_data
                WHERE interval_minutes = $1
            """,
                interval_minutes,
            )

            logger.info("\n📊 СОСТОЯНИЕ БАЗЫ ДАННЫХ:")
            logger.info(f"📈 Символов: {result['symbols']}")
            logger.info(f"📊 Всего записей: {result['total_records']:,}")
            logger.info(f"📅 Период: {result['min_date']} - {result['max_date']}")

        await exchange.close()

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await pool.close()

    logger.info("\n✅ Загрузка завершена!")


if __name__ == "__main__":
    asyncio.run(main())
