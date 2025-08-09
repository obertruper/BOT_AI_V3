#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка уникальности данных в БД для разных символов
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import and_, select

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent))

from core.logger import setup_logger
from database.connections import get_async_db
from database.models.market_data import RawMarketData

logger = setup_logger(__name__)


async def check_database_uniqueness():
    """Проверяет уникальность данных в БД для разных символов"""

    symbols = ["BTCUSDT", "ETHUSDT"]
    lookback_minutes = 1440  # 24 часа

    logger.info("🔍 Проверка уникальности данных в БД...")

    data_stats = {}

    for symbol in symbols:
        logger.info(f"\n📊 Анализ данных для {symbol}:")

        # Получаем данные из БД
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(minutes=lookback_minutes)

        async with get_async_db() as session:
            stmt = (
                select(RawMarketData)
                .where(
                    and_(
                        RawMarketData.symbol == symbol,
                        RawMarketData.exchange == "bybit",
                        RawMarketData.datetime >= start_date,
                        RawMarketData.interval_minutes == 15,
                    )
                )
                .order_by(RawMarketData.timestamp)
                .limit(100)  # Последние 100 записей
            )

            result = await session.execute(stmt)
            data = result.scalars().all()

            if not data:
                logger.warning(f"❌ Нет данных для {symbol}")
                continue

            logger.info(f"✅ Найдено {len(data)} записей для {symbol}")

            # Конвертируем в DataFrame
            df = pd.DataFrame(
                [
                    {
                        "timestamp": d.timestamp,
                        "datetime": d.datetime,
                        "open": float(d.open),
                        "high": float(d.high),
                        "low": float(d.low),
                        "close": float(d.close),
                        "volume": float(d.volume),
                        "turnover": float(d.turnover) if d.turnover else 0,
                    }
                    for d in data
                ]
            )

            # Статистики
            stats = {
                "count": len(df),
                "close_min": df["close"].min(),
                "close_max": df["close"].max(),
                "close_mean": df["close"].mean(),
                "close_std": df["close"].std(),
                "volume_mean": df["volume"].mean(),
                "volume_std": df["volume"].std(),
                "last_10_closes": df["close"].tail(10).values.tolist(),
                "first_timestamp": df["datetime"].min(),
                "last_timestamp": df["datetime"].max(),
            }

            data_stats[symbol] = stats

            logger.info(f"   Записей: {stats['count']}")
            logger.info(
                f"   Цена close: {stats['close_min']:.2f} - {stats['close_max']:.2f} (mean: {stats['close_mean']:.2f})"
            )
            logger.info(
                f"   Объем: mean={stats['volume_mean']:.0f}, std={stats['volume_std']:.0f}"
            )
            logger.info(
                f"   Период: {stats['first_timestamp']} - {stats['last_timestamp']}"
            )
            logger.info(
                f"   Последние 10 close: {[f'{x:.2f}' for x in stats['last_10_closes']]}"
            )

    # Сравнение данных между символами
    if len(data_stats) >= 2:
        logger.info("\n📋 Сравнение данных между символами:")

        symbols_list = list(data_stats.keys())
        btc_stats = data_stats[symbols_list[0]]
        eth_stats = data_stats[symbols_list[1]]

        logger.info(f"{symbols_list[0]} vs {symbols_list[1]}:")
        logger.info(
            f"   Средние цены: {btc_stats['close_mean']:.2f} vs {eth_stats['close_mean']:.2f}"
        )
        logger.info(
            f"   Стандартные отклонения: {btc_stats['close_std']:.2f} vs {eth_stats['close_std']:.2f}"
        )

        # Проверяем, не одинаковые ли данные
        btc_closes = btc_stats["last_10_closes"]
        eth_closes = eth_stats["last_10_closes"]

        if len(btc_closes) == len(eth_closes):
            differences = [abs(btc - eth) for btc, eth in zip(btc_closes, eth_closes)]
            avg_diff = sum(differences) / len(differences)
            max_diff = max(differences)

            logger.info(f"   Средняя разность последних close: {avg_diff:.2f}")
            logger.info(f"   Максимальная разность: {max_diff:.2f}")

            if avg_diff < 1.0:
                logger.error("❌ ПОДОЗРЕНИЕ: Данные слишком похожи между символами!")
            else:
                logger.info("✅ Данные достаточно различны между символами")

    return data_stats


async def main():
    await check_database_uniqueness()


if __name__ == "__main__":
    asyncio.run(main())
