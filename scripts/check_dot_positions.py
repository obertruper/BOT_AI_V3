#!/usr/bin/env python3
"""
Скрипт для проверки позиций DOT и других активов
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool

logger = setup_logger("check_positions")


async def check_dot_positions():
    """Проверка позиций DOT и других активов"""

    logger.info("🔍 Проверка позиций DOT и других активов...")

    try:
        # Подключение к базе данных
        await AsyncPGPool.get_pool()

        # Проверяем ордера (активные позиции)
        orders_query = """
        SELECT
            symbol,
            side,
            order_type,
            status,
            quantity,
            price,
            created_at
        FROM orders
        WHERE symbol LIKE '%DOT%' OR symbol IN ('BTCUSDT', 'ETHUSDT', 'SOLUSDT')
        ORDER BY created_at DESC
        LIMIT 10
        """

        orders = await AsyncPGPool.fetch(orders_query)

        if orders:
            logger.info(f"📋 Последние {len(orders)} ордеров:")
            for order in orders:
                logger.info(
                    f"  {order['symbol']}: {order['side']} {order['order_type']} {order['status']} {order['quantity']} @ {order['price']}"
                )
        else:
            logger.info("✅ Ордеров DOT и других активов не найдено")

        # Проверяем исполненные сделки
        trades_query = """
        SELECT
            symbol,
            side,
            price,
            quantity,
            commission,
            created_at
        FROM trades
        WHERE symbol LIKE '%DOT%' OR symbol IN ('BTCUSDT', 'ETHUSDT', 'SOLUSDT')
        ORDER BY created_at DESC
        LIMIT 10
        """

        trades = await AsyncPGPool.fetch(trades_query)

        if trades:
            logger.info(f"💰 Последние {len(trades)} сделок:")
            for trade in trades:
                logger.info(
                    f"  {trade['symbol']}: {trade['side']} {trade['quantity']} @ {trade['price']} (комиссия: {trade['commission']})"
                )
        else:
            logger.info("✅ Сделок DOT и других активов не найдено")

        # Проверяем сигналы
        signals_query = """
        SELECT
            symbol,
            signal_type,
            strength,
            confidence,
            created_at
        FROM signals
        WHERE symbol LIKE '%DOT%' OR symbol IN ('BTCUSDT', 'ETHUSDT', 'SOLUSDT')
        ORDER BY created_at DESC
        LIMIT 10
        """

        signals = await AsyncPGPool.fetch(signals_query)

        if signals:
            logger.info(f"🎯 Последние {len(signals)} сигналов:")
            for signal in signals:
                logger.info(
                    f"  {signal['symbol']}: {signal['signal_type']} strength={signal['strength']} confidence={signal['confidence']}"
                )
        else:
            logger.info("✅ Сигналов DOT и других активов не найдено")

        # Анализ дублирующих сигналов
        duplicate_signals_query = """
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
        HAVING COUNT(*) > 1
        ORDER BY count DESC
        """

        duplicate_signals = await AsyncPGPool.fetch(duplicate_signals_query)

        if duplicate_signals:
            logger.info(
                f"⚠️ Найдено {len(duplicate_signals)} типов дублирующих сигналов:"
            )
            for signal in duplicate_signals:
                logger.info(
                    f"  {signal['symbol']}: {signal['signal_type']} strength={signal['strength']} confidence={signal['confidence']} (count={signal['count']})"
                )
        else:
            logger.info("✅ Дублирующих сигналов не найдено")

    except Exception as e:
        logger.error(f"❌ Ошибка проверки позиций: {e}")

    finally:
        await AsyncPGPool.close_pool()


if __name__ == "__main__":
    asyncio.run(check_dot_positions())
