#!/usr/bin/env python3
"""
Скрипт проверки доступности данных для ML генерации сигналов
Проверяет наличие достаточного количества исторических данных
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from data.data_loader import DataLoader
from database.connections import get_async_db

logger = setup_logger("check_data")


async def check_raw_data_availability():
    """Проверка наличия данных в таблице raw_market_data"""
    try:
        async with get_async_db() as session:
            # Получаем общее количество записей
            result = await session.execute(text("SELECT COUNT(*) FROM raw_market_data"))
            total_records = result.scalar()

            # Получаем количество записей по символам
            result = await session.execute(
                text(
                    """
                SELECT symbol, COUNT(*) as count,
                       MIN(timestamp) as min_date,
                       MAX(timestamp) as max_date
                FROM raw_market_data
                GROUP BY symbol
                ORDER BY count DESC
            """
                )
            )

            symbol_stats = result.fetchall()

            logger.info(f"📊 Всего записей в БД: {total_records}")
            logger.info("📈 Статистика по символам:")

            for stat in symbol_stats[:20]:  # Показываем топ-20
                logger.info(
                    f"  {stat.symbol}: {stat.count} записей "
                    f"({stat.min_date.strftime('%Y-%m-%d')} - "
                    f"{stat.max_date.strftime('%Y-%m-%d')})"
                )

            return symbol_stats

    except Exception as e:
        logger.error(f"❌ Ошибка при проверке данных в БД: {e}")
        return []


async def check_data_for_ml(config_manager: ConfigManager):
    """Проверка доступности данных для ML генерации"""
    logger.info("🔍 Проверка доступности данных для ML...")

    # Получаем ML конфигурацию
    ml_config = config_manager.get_ml_config()
    ml_symbols = ml_config.get("symbols", [])
    min_candles = 240  # Минимум для ML предсказания

    logger.info(f"📋 Проверяем {len(ml_symbols)} символов из ml_config.yaml")

    # Инициализируем DataLoader
    data_loader = DataLoader(config_manager)
    await data_loader.initialize()

    results = {}
    missing_symbols = []
    ready_symbols = []

    for symbol in ml_symbols[:10]:  # Проверяем первые 10
        try:
            logger.info(f"\n🔍 Проверка {symbol}...")

            # Пробуем загрузить данные
            df = await data_loader.load_ohlcv(
                symbol=symbol, exchange="bybit", interval="15m", limit=min_candles + 10
            )

            if df is not None and len(df) >= min_candles:
                logger.info(f"✅ {symbol}: {len(df)} свечей доступно")
                ready_symbols.append(symbol)
                results[symbol] = {
                    "status": "ready",
                    "candles": len(df),
                    "first": df.index[0],
                    "last": df.index[-1],
                }
            else:
                candles = len(df) if df is not None else 0
                logger.warning(f"⚠️ {symbol}: только {candles}/{min_candles} свечей")
                missing_symbols.append(symbol)
                results[symbol] = {
                    "status": "insufficient",
                    "candles": candles,
                    "needed": min_candles,
                }

        except Exception as e:
            logger.error(f"❌ {symbol}: ошибка загрузки - {e}")
            missing_symbols.append(symbol)
            results[symbol] = {"status": "error", "error": str(e)}

    # Итоги
    logger.info("\n📊 ИТОГИ ПРОВЕРКИ:")
    logger.info(f"✅ Готовы к ML: {len(ready_symbols)} символов")
    logger.info(f"⚠️ Недостаточно данных: {len(missing_symbols)} символов")

    if ready_symbols:
        logger.info(f"\n🟢 Готовые символы: {', '.join(ready_symbols)}")

    if missing_symbols:
        logger.info(f"\n🔴 Проблемные символы: {', '.join(missing_symbols)}")
        logger.info("\n💡 Для загрузки недостающих данных используйте:")
        logger.info("   python scripts/load_historical_data.py")

    return results


async def check_ml_system_readiness(config_manager: ConfigManager):
    """Полная проверка готовности ML системы"""
    logger.info("🚀 Проверка готовности ML системы к запуску...")

    checks = {
        "model": False,
        "scaler": False,
        "database": False,
        "data": False,
        "config": False,
    }

    # 1. Проверка модели
    model_path = Path("models/saved/best_model_20250728_215703.pth")
    if model_path.exists():
        logger.info(f"✅ ML модель найдена: {model_path}")
        checks["model"] = True
    else:
        logger.error(f"❌ ML модель не найдена: {model_path}")

    # 2. Проверка scaler
    scaler_path = Path("models/saved/data_scaler.pkl")
    if scaler_path.exists():
        logger.info(f"✅ Data scaler найден: {scaler_path}")
        checks["scaler"] = True
    else:
        logger.error(f"❌ Data scaler не найден: {scaler_path}")

    # 3. Проверка БД
    try:
        async with get_async_db() as session:
            await session.execute(text("SELECT 1"))
            logger.info("✅ Подключение к БД работает")
            checks["database"] = True
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к БД: {e}")

    # 4. Проверка конфигурации
    ml_config = config_manager.get_ml_config()
    if ml_config and ml_config.get("model", {}).get("enabled"):
        logger.info("✅ ML конфигурация загружена")
        checks["config"] = True
    else:
        logger.error("❌ ML отключен в конфигурации")

    # 5. Проверка данных
    data_results = await check_data_for_ml(config_manager)
    ready_count = sum(1 for r in data_results.values() if r["status"] == "ready")
    if ready_count > 0:
        logger.info(f"✅ Данные доступны для {ready_count} символов")
        checks["data"] = True
    else:
        logger.error("❌ Нет доступных данных для ML")

    # Итоговый результат
    all_ready = all(checks.values())

    logger.info("\n" + "=" * 50)
    logger.info("📋 РЕЗУЛЬТАТЫ ПРОВЕРКИ:")
    for check, status in checks.items():
        icon = "✅" if status else "❌"
        logger.info(f"  {icon} {check.upper()}: {'OK' if status else 'FAILED'}")

    if all_ready:
        logger.info("\n🟢 СИСТЕМА ГОТОВА К ЗАПУСКУ!")
        logger.info("🚀 Запустите: python main.py")
    else:
        logger.info("\n🔴 СИСТЕМА НЕ ГОТОВА")
        logger.info("❗ Исправьте проблемы выше перед запуском")

    return all_ready


async def main():
    """Основная функция"""
    try:
        # Инициализируем конфигурацию
        config_manager = ConfigManager()
        await config_manager.initialize()

        # Проверяем данные в БД
        logger.info("=" * 50)
        logger.info("📊 ПРОВЕРКА ДАННЫХ В БАЗЕ")
        logger.info("=" * 50)
        await check_raw_data_availability()

        # Проверяем готовность ML системы
        logger.info("\n" + "=" * 50)
        logger.info("🤖 ПРОВЕРКА ML СИСТЕМЫ")
        logger.info("=" * 50)
        is_ready = await check_ml_system_readiness(config_manager)

        return is_ready

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    is_ready = asyncio.run(main())
    sys.exit(0 if is_ready else 1)
