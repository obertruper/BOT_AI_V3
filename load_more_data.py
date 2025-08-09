#!/usr/bin/env python3
"""
Загрузка дополнительных исторических данных для ML торговли
"""

import asyncio
import sys
from datetime import datetime, timedelta
from typing import List

from sqlalchemy import func, select

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from data.data_loader import DataLoader
from database.connections import get_async_db
from database.models.market_data import RawMarketData

logger = setup_logger(__name__)


async def check_data_availability():
    """Проверяет количество доступных данных для каждого символа"""

    async with get_async_db() as db:
        # Получаем статистику по символам
        stmt = (
            select(
                RawMarketData.symbol,
                func.count(RawMarketData.id).label("count"),
                func.min(RawMarketData.datetime).label("min_date"),
                func.max(RawMarketData.datetime).label("max_date"),
            )
            .where(RawMarketData.interval_minutes == 15)
            .group_by(RawMarketData.symbol)
        )

        result = await db.execute(stmt)
        stats = result.all()

        logger.info("\n📊 Текущее состояние данных:")
        logger.info(f"{'Символ':<12} {'Записей':<10} {'Начало':<20} {'Конец':<20}")
        logger.info("-" * 70)

        symbols_needing_data = []

        for row in stats:
            logger.info(
                f"{row.symbol:<12} {row.count:<10} "
                f"{row.min_date.strftime('%Y-%m-%d %H:%M'):<20} "
                f"{row.max_date.strftime('%Y-%m-%d %H:%M'):<20}"
            )

            # Если меньше 300 записей - нужно больше данных
            if row.count < 300:
                symbols_needing_data.append(row.symbol)

        # Проверяем символы без данных
        all_symbols = [
            "BTCUSDT",
            "ETHUSDT",
            "BNBUSDT",
            "SOLUSDT",
            "XRPUSDT",
            "DOGEUSDT",
            "ADAUSDT",
            "AVAXUSDT",
            "DOTUSDT",
            "LINKUSDT",
        ]

        existing_symbols = [row.symbol for row in stats]
        missing_symbols = [s for s in all_symbols if s not in existing_symbols]

        if missing_symbols:
            logger.info(f"\n⚠️ Символы без данных: {', '.join(missing_symbols)}")
            symbols_needing_data.extend(missing_symbols)

        return symbols_needing_data


async def load_historical_data(symbols: List[str], days: int = 10):
    """Загружает исторические данные для указанных символов"""

    config_manager = ConfigManager()
    config = config_manager.get_config()

    # Инициализируем data loader
    data_loader = DataLoader(config_manager)

    # Даты для загрузки
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    logger.info(f"\n📥 Загрузка данных за {days} дней")
    logger.info(
        f"   С {start_date.strftime('%Y-%m-%d')} по {end_date.strftime('%Y-%m-%d')}"
    )
    logger.info(f"   Символы: {', '.join(symbols)}\n")

    for symbol in symbols:
        try:
            logger.info(f"⏳ Загружаем {symbol}...")

            # Загружаем данные
            df = await data_loader.load_ohlcv(
                symbol=symbol,
                exchange="bybit",
                interval_minutes=15,
                start_date=start_date,
                end_date=end_date,
            )

            if df is not None and not df.empty:
                logger.info(f"✅ {symbol}: загружено {len(df)} записей из биржи")
            else:
                logger.warning(f"❌ {symbol}: не удалось загрузить данные")

        except Exception as e:
            logger.error(f"Ошибка при загрузке {symbol}: {e}")

        # Небольшая задержка чтобы не перегружать API
        await asyncio.sleep(1)


async def main():
    """Основная функция"""

    logger.info("\n" + "=" * 70)
    logger.info("🔄 Загрузка дополнительных данных для ML торговли")
    logger.info("=" * 70 + "\n")

    # Проверяем текущее состояние
    symbols_needing_data = await check_data_availability()

    if symbols_needing_data:
        logger.info(
            f"\n📊 Требуется загрузить данные для {len(symbols_needing_data)} символов"
        )

        # Загружаем данные за 10 дней (400+ записей)
        await load_historical_data(symbols_needing_data, days=10)

        # Проверяем результат
        logger.info("\n📊 Проверка после загрузки:")
        await check_data_availability()

    else:
        logger.info("\n✅ Все символы имеют достаточно данных")

    logger.info("\n✅ Готово! Теперь можно запускать ML торговлю.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Загрузка прервана")
        sys.exit(0)
