#!/usr/bin/env python3
"""
Скрипт для проверки и оптимизации базы данных для ML системы
"""

import asyncio
import os
import sys

# Добавляем корневую директорию в путь
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text

from core.logger import setup_logger
from database.connections import AsyncSessionLocal

logger = setup_logger(__name__)


async def check_tables():
    """Проверка существования необходимых таблиц"""
    logger.info("🔍 Проверка существования таблиц ML системы...")

    required_tables = [
        "raw_market_data",
        "processed_market_data",
        "signals",
        "technical_indicators",
        "market_data_snapshots",
    ]

    async with AsyncSessionLocal() as session:
        # Проверяем существование таблиц
        result = await session.execute(
            text(
                """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = ANY(:tables)
            ORDER BY table_name;
        """
            ),
            {"tables": required_tables},
        )

        existing_tables = [row[0] for row in result]

        logger.info(f"✅ Найдено таблиц: {len(existing_tables)}")
        for table in existing_tables:
            logger.info(f"  ✓ {table}")

        missing_tables = set(required_tables) - set(existing_tables)
        if missing_tables:
            logger.warning(f"❌ Отсутствуют таблицы: {missing_tables}")
            return False

        return True


async def check_indexes():
    """Проверка и создание оптимальных индексов"""
    logger.info("\n🔍 Проверка индексов...")

    async with AsyncSessionLocal() as session:
        # Проверяем существующие индексы
        result = await session.execute(
            text(
                """
            SELECT
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND tablename IN ('raw_market_data', 'processed_market_data', 'signals')
            ORDER BY tablename, indexname;
        """
            )
        )

        existing_indexes = {}
        for row in result:
            table = row[1]
            if table not in existing_indexes:
                existing_indexes[table] = []
            existing_indexes[table].append(row[2])

        logger.info("✅ Существующие индексы:")
        for table, indexes in existing_indexes.items():
            logger.info(f"\n  Таблица {table}:")
            for idx in indexes:
                logger.info(f"    ✓ {idx}")


async def create_missing_indexes():
    """Создание недостающих индексов для оптимальной производительности"""
    logger.info("\n🛠️ Создание оптимизированных индексов...")

    indexes_to_create = [
        # Для raw_market_data - дополнительные индексы для ML
        {
            "name": "idx_raw_market_data_symbol_timestamp_desc",
            "table": "raw_market_data",
            "columns": "symbol, timestamp DESC",
            "condition": None,
        },
        {
            "name": "idx_raw_market_data_interval_symbol",
            "table": "raw_market_data",
            "columns": "interval_minutes, symbol",
            "condition": None,
        },
        # Для processed_market_data - индексы для быстрого доступа к ML данным
        {
            "name": "idx_processed_market_data_timestamp_desc",
            "table": "processed_market_data",
            "columns": "timestamp DESC",
            "condition": None,
        },
        {
            "name": "idx_processed_market_data_ml_features",
            "table": "processed_market_data",
            "columns": "ml_features",
            "condition": None,
            "method": "gin",
        },
        # Для signals - индексы для эффективной выборки
        {
            "name": "idx_signals_created_at_desc",
            "table": "signals",
            "columns": "created_at DESC",
            "condition": None,
        },
        {
            "name": "idx_signals_expires_at",
            "table": "signals",
            "columns": "expires_at",
            "condition": "WHERE expires_at IS NOT NULL",
        },
        {
            "name": "idx_signals_signal_type_symbol",
            "table": "signals",
            "columns": "signal_type, symbol",
            "condition": None,
        },
    ]

    async with AsyncSessionLocal() as session:
        for index in indexes_to_create:
            try:
                # Проверяем существование индекса
                check_result = await session.execute(
                    text(
                        """
                    SELECT 1 FROM pg_indexes
                    WHERE schemaname = 'public'
                    AND indexname = :index_name
                """
                    ),
                    {"index_name": index["name"]},
                )

                if check_result.scalar():
                    logger.info(f"  ✓ Индекс {index['name']} уже существует")
                    continue

                # Создаем индекс
                method = f"USING {index['method']}" if index.get("method") else ""
                condition = index.get("condition", "")

                sql = f"""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS {index["name"]}
                    ON {index["table"]} {method} ({index["columns"]})
                    {condition}
                """

                await session.execute(text(sql))
                await session.commit()
                logger.info(f"  ✅ Создан индекс {index['name']}")

            except Exception as e:
                logger.error(f"  ❌ Ошибка создания индекса {index['name']}: {e}")


async def check_table_sizes():
    """Проверка размеров таблиц и статистики"""
    logger.info("\n📊 Статистика таблиц:")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
            SELECT
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
                pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes,
                (SELECT COUNT(*) FROM pg_stat_user_tables WHERE schemaname = t.schemaname AND tablename = t.tablename) as stats_count
            FROM pg_tables t
            WHERE schemaname = 'public'
            AND tablename IN ('raw_market_data', 'processed_market_data', 'signals', 'technical_indicators')
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
        """
            )
        )

        for row in result:
            logger.info(f"  {row[1]:25} | Размер: {row[2]:>10}")

        # Проверяем количество записей
        for table in ["raw_market_data", "processed_market_data", "signals"]:
            try:
                count_result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = count_result.scalar()
                logger.info(f"  {table:25} | Записей: {count:>10,}")
            except Exception as e:
                logger.error(f"  {table:25} | Ошибка подсчета: {e}")


async def create_scheduler_metrics_table():
    """Создание таблицы для метрик планировщика если её нет"""
    logger.info("\n🛠️ Проверка таблицы scheduler_metrics...")

    async with AsyncSessionLocal() as session:
        # Проверяем существование таблицы
        result = await session.execute(
            text(
                """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'scheduler_metrics'
            );
        """
            )
        )

        exists = result.scalar()

        if not exists:
            logger.info("  ⚠️ Таблица scheduler_metrics не найдена, создаем...")

            await session.execute(
                text(
                    """
                CREATE TABLE scheduler_metrics (
                    id BIGSERIAL PRIMARY KEY,
                    cycle_start TIMESTAMP WITH TIME ZONE NOT NULL,
                    cycle_end TIMESTAMP WITH TIME ZONE NOT NULL,
                    duration_seconds FLOAT NOT NULL,
                    symbols_processed INTEGER NOT NULL,
                    signals_generated INTEGER NOT NULL,
                    errors_count INTEGER DEFAULT 0,
                    avg_symbol_processing_time FLOAT,
                    memory_usage_mb FLOAT,
                    cpu_usage_percent FLOAT,
                    status VARCHAR(20) DEFAULT 'completed',
                    error_details JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );

                CREATE INDEX idx_scheduler_metrics_cycle_start ON scheduler_metrics(cycle_start DESC);
                CREATE INDEX idx_scheduler_metrics_status ON scheduler_metrics(status);
            """
                )
            )

            await session.commit()
            logger.info("  ✅ Таблица scheduler_metrics создана")
        else:
            logger.info("  ✅ Таблица scheduler_metrics существует")


async def check_performance():
    """Проверка производительности для обработки 50+ символов"""
    logger.info("\n⚡ Проверка производительности для ML системы...")

    async with AsyncSessionLocal() as session:
        # Тест выборки последних данных для символа
        test_query = """
            SELECT
                symbol,
                datetime,
                close,
                volume
            FROM raw_market_data
            WHERE symbol = 'BTCUSDT'
            AND interval_minutes = 15
            ORDER BY timestamp DESC
            LIMIT 100;
        """

        import time

        start_time = time.time()

        try:
            await session.execute(text(test_query))
            elapsed = (time.time() - start_time) * 1000

            logger.info(f"  ✅ Тест выборки данных: {elapsed:.2f} мс")

            if elapsed > 50:
                logger.warning("  ⚠️ Выборка занимает более 50мс, рекомендуется оптимизация")

        except Exception as e:
            logger.error(f"  ❌ Ошибка теста производительности: {e}")


async def main():
    """Основная функция"""
    logger.info("🚀 Запуск проверки БД для ML системы BOT_AI_V3")
    logger.info("=" * 60)

    try:
        # Выполняем проверки
        tables_ok = await check_tables()

        if tables_ok:
            await check_indexes()
            await create_missing_indexes()
            await create_scheduler_metrics_table()
            await check_table_sizes()
            await check_performance()

            logger.info("\n" + "=" * 60)
            logger.info("✅ Проверка БД завершена успешно!")
            logger.info("🚀 База данных готова для ML системы")
        else:
            logger.error("\n" + "=" * 60)
            logger.error("❌ Необходимо применить миграции!")
            logger.error("Выполните: alembic upgrade head")

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
