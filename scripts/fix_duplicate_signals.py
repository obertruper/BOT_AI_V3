#!/usr/bin/env python3
"""
Скрипт для исправления проблемы с дублирующими сигналами
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool

logger = setup_logger("fix_duplicates")


async def fix_duplicate_signals():
    """Исправление дублирующих сигналов"""

    logger.info("🔧 Исправление дублирующих сигналов...")

    try:
        # Подключение к базе данных
        await AsyncPGPool.get_pool()

        # Находим дублирующие сигналы за последние 24 часа
        duplicate_query = """
        WITH duplicates AS (
            SELECT
                symbol,
                signal_type,
                strength,
                confidence,
                created_at,
                ROW_NUMBER() OVER (
                    PARTITION BY symbol, signal_type, strength, confidence
                    ORDER BY created_at DESC
                ) as rn
            FROM signals
            WHERE created_at > NOW() - INTERVAL '24 hours'
        )
        SELECT * FROM duplicates WHERE rn > 1
        """

        duplicates = await AsyncPGPool.fetch(duplicate_query)

        if duplicates:
            logger.info(f"📊 Найдено {len(duplicates)} дублирующих сигналов:")

            # Удаляем дубликаты
            delete_query = """
            DELETE FROM signals
            WHERE id IN (
                SELECT id FROM (
                    SELECT
                        id,
                        ROW_NUMBER() OVER (
                            PARTITION BY symbol, signal_type, strength, confidence
                            ORDER BY created_at DESC
                        ) as rn
                    FROM signals
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                ) t WHERE rn > 1
            )
            """

            result = await AsyncPGPool.execute(delete_query)
            logger.info(f"✅ Удалено {result} дублирующих сигналов")

            # Показываем оставшиеся уникальные сигналы
            unique_query = """
            SELECT
                symbol,
                signal_type,
                strength,
                confidence,
                COUNT(*) as count,
                MIN(created_at) as first_seen,
                MAX(created_at) as last_seen
            FROM signals
            WHERE created_at > NOW() - INTERVAL '24 hours'
            GROUP BY symbol, signal_type, strength, confidence
            ORDER BY last_seen DESC
            """

            unique_signals = await AsyncPGPool.fetch(unique_query)

            logger.info("📋 Уникальные сигналы за последние 24 часа:")
            for signal in unique_signals:
                logger.info(
                    f"  {signal['symbol']}: {signal['signal_type']} strength={signal['strength']} confidence={signal['confidence']} (count={signal['count']})"
                )
        else:
            logger.info("✅ Дублирующих сигналов не найдено")

        # Проверяем ордера, созданные от дублирующих сигналов
        duplicate_orders_query = """
        SELECT
            symbol,
            side,
            order_type,
            status,
            quantity,
            COUNT(*) as count
        FROM orders
        WHERE created_at > NOW() - INTERVAL '24 hours'
        GROUP BY symbol, side, order_type, status, quantity
        HAVING COUNT(*) > 1
        ORDER BY count DESC
        """

        duplicate_orders = await AsyncPGPool.fetch(duplicate_orders_query)

        if duplicate_orders:
            logger.info(f"📋 Найдено {len(duplicate_orders)} типов дублирующих ордеров:")
            for order in duplicate_orders:
                logger.info(
                    f"  {order['symbol']}: {order['side']} {order['order_type']} {order['status']} {order['quantity']} (count={order['count']})"
                )
        else:
            logger.info("✅ Дублирующих ордеров не найдено")

    except Exception as e:
        logger.error(f"❌ Ошибка исправления дубликатов: {e}")

    finally:
        await AsyncPGPool.close_pool()


async def add_signal_uniqueness_constraint():
    """Добавление ограничения уникальности для сигналов"""

    logger.info("🔒 Добавление ограничения уникальности для сигналов...")

    try:
        await AsyncPGPool.get_pool()

        # Создаем индекс для предотвращения дубликатов (без DATE_TRUNC)
        index_query = """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_signals_unique
        ON signals (symbol, signal_type, strength, confidence)
        """

        await AsyncPGPool.execute(index_query)
        logger.info("✅ Индекс уникальности создан")

    except Exception as e:
        logger.error(f"❌ Ошибка создания индекса: {e}")

    finally:
        await AsyncPGPool.close_pool()


if __name__ == "__main__":
    asyncio.run(fix_duplicate_signals())
    # Создаем индекс только после удаления дубликатов
    asyncio.run(add_signal_uniqueness_constraint())
