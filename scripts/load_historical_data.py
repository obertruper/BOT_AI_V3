#!/usr/bin/env python3
"""
Скрипт загрузки исторических данных для ML
Загружает OHLCV данные с биржи для всех символов из конфигурации
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from data.data_loader import DataLoader

logger = setup_logger("load_historical")


async def load_symbol_data(
    data_loader: DataLoader,
    symbol: str,
    exchange: str = "bybit",
    days: int = 30,  # По умолчанию 30 дней данных
) -> Optional[pd.DataFrame]:
    """Загрузка данных для одного символа"""
    try:
        logger.info(f"📥 Загрузка {symbol} за {days} дней...")

        # Рассчитываем количество свечей
        candles_per_day = 24 * 4  # 15-минутные свечи
        limit = candles_per_day * days

        # Загружаем данные
        df = await data_loader.load_ohlcv(
            symbol=symbol,
            exchange=exchange,
            interval="15m",
            limit=min(limit, 1000),  # Bybit ограничение
            save_to_db=True,  # Сохраняем в БД
        )

        if df is not None and not df.empty:
            logger.info(
                f"✅ {symbol}: загружено {len(df)} свечей "
                f"({df.index[0]} - {df.index[-1]})"
            )
            return df
        else:
            logger.warning(f"⚠️ {symbol}: нет данных")
            return None

    except Exception as e:
        logger.error(f"❌ {symbol}: ошибка загрузки - {e}")
        return None


async def load_all_symbols(config_manager: ConfigManager, days: int = 30):
    """Загрузка данных для всех символов из конфигурации"""
    logger.info("🚀 Начинаем загрузку исторических данных...")

    # Получаем список символов
    ml_config = config_manager.get_ml_config()
    symbols = ml_config.get("data", {}).get("symbols", [])

    # Берем символы из system.yaml если они есть
    system_config = config_manager.get_system_config()
    ml_symbols = system_config.get("ml", {}).get("symbols", [])

    # Используем символы из system.yaml если они определены
    if ml_symbols:
        symbols = ml_symbols

    logger.info(f"📋 Найдено {len(symbols)} символов для загрузки")

    # Инициализируем DataLoader
    data_loader = DataLoader(config_manager)
    await data_loader.initialize()

    # Загружаем данные для каждого символа
    results = {"success": [], "failed": [], "total_candles": 0}

    for i, symbol in enumerate(symbols, 1):
        logger.info(f"\n[{i}/{len(symbols)}] Обработка {symbol}...")

        df = await load_symbol_data(data_loader, symbol, days=days)

        if df is not None:
            results["success"].append(symbol)
            results["total_candles"] += len(df)
        else:
            results["failed"].append(symbol)

        # Небольшая задержка между запросами
        if i < len(symbols):
            await asyncio.sleep(0.5)

    # Выводим результаты
    logger.info("\n" + "=" * 50)
    logger.info("📊 РЕЗУЛЬТАТЫ ЗАГРУЗКИ:")
    logger.info(f"✅ Успешно загружено: {len(results['success'])} символов")
    logger.info(f"❌ Не удалось загрузить: {len(results['failed'])} символов")
    logger.info(f"📈 Всего свечей загружено: {results['total_candles']}")

    if results["success"]:
        logger.info(f"\n✅ Успешные: {', '.join(results['success'][:10])}")
        if len(results["success"]) > 10:
            logger.info(f"   и еще {len(results['success']) - 10} символов...")

    if results["failed"]:
        logger.info(f"\n❌ Неудачные: {', '.join(results['failed'])}")

    return results


async def check_and_update_data(config_manager: ConfigManager):
    """Проверка и обновление данных до актуального состояния"""
    logger.info("🔄 Проверка актуальности данных...")

    data_loader = DataLoader(config_manager)
    await data_loader.initialize()

    # Получаем символы
    system_config = config_manager.get_system_config()
    symbols = system_config.get("ml", {}).get("symbols", [])[:5]  # Первые 5 для теста

    for symbol in symbols:
        try:
            # Загружаем последние данные
            df = await data_loader.load_ohlcv(
                symbol=symbol,
                exchange="bybit",
                interval="15m",
                limit=100,
                save_to_db=True,
            )

            if df is not None and not df.empty:
                last_candle = df.index[-1]
                now = datetime.now()
                age = now - last_candle

                if age > timedelta(hours=1):
                    logger.warning(
                        f"⚠️ {symbol}: данные устарели на {age.total_seconds() / 3600:.1f} часов"
                    )
                else:
                    logger.info(
                        f"✅ {symbol}: данные актуальны (обновлены {age.total_seconds() / 60:.0f} мин назад)"
                    )

        except Exception as e:
            logger.error(f"❌ {symbol}: ошибка проверки - {e}")


async def main():
    """Основная функция"""
    try:
        # Парсим аргументы
        import argparse

        parser = argparse.ArgumentParser(
            description="Загрузка исторических данных для ML"
        )
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Количество дней данных для загрузки (по умолчанию 30)",
        )
        parser.add_argument(
            "--check-only",
            action="store_true",
            help="Только проверить актуальность данных",
        )
        parser.add_argument(
            "--symbols",
            nargs="+",
            help="Список символов для загрузки (по умолчанию из конфигурации)",
        )

        args = parser.parse_args()

        # Инициализируем конфигурацию
        config_manager = ConfigManager()
        await config_manager.initialize()

        if args.check_only:
            # Только проверка
            await check_and_update_data(config_manager)
        else:
            # Загрузка данных
            if args.symbols:
                # Переопределяем символы
                system_config = config_manager.get_system_config()
                system_config.setdefault("ml", {})["symbols"] = args.symbols

            results = await load_all_symbols(config_manager, days=args.days)

            # Проверяем результаты
            if results["success"]:
                logger.info("\n🟢 Данные успешно загружены!")
                logger.info("🚀 Теперь можно запускать ML систему")
            else:
                logger.error("\n🔴 Не удалось загрузить данные")

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
