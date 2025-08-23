#!/usr/bin/env python3
"""
Тестирование исправлений ошибок и предупреждений
"""

import asyncio
import sys
from pathlib import Path

# Добавляем проект в путь
sys.path.append(str(Path(__file__).parent))

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from database.db_manager import get_db
from ml.realtime_indicator_calculator import RealTimeIndicatorCalculator
from trading.sltp.enhanced_manager import EnhancedSLTPManager

logger = setup_logger(__name__)


async def test_database_connection():
    """Тест подключения к базе данных"""
    try:
        logger.info("🔍 Тестирование подключения к базе данных...")
        db = await get_db()
        health = await db.health_check()
        logger.info(f"✅ База данных: {health['status']}")
        logger.info(f"   Pool: {health.get('pool', {})}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к базе данных: {e}")
        return False


async def test_ml_features():
    """Тест генерации ML признаков"""
    try:
        logger.info("🔍 Тестирование генерации ML признаков...")
        calculator = RealTimeIndicatorCalculator(use_inference_mode=True)

        # Создаем тестовые данные
        from datetime import datetime, timedelta

        import numpy as np
        import pandas as pd

        # Генерируем 150 свечей (15 минут каждая)
        dates = pd.date_range(
            start=datetime.now() - timedelta(hours=37.5),  # 150 * 15 минут
            end=datetime.now(),
            freq="15min",
        )[:150]

        # Создаем синтетические OHLCV данные
        np.random.seed(42)  # Для воспроизводимости
        close_prices = 50000 + np.cumsum(np.random.randn(len(dates)) * 100)

        test_data = pd.DataFrame(
            {
                "datetime": dates,
                "open": close_prices * (1 + np.random.randn(len(dates)) * 0.001),
                "high": close_prices * (1 + np.abs(np.random.randn(len(dates)) * 0.002)),
                "low": close_prices * (1 - np.abs(np.random.randn(len(dates)) * 0.002)),
                "close": close_prices,
                "volume": np.random.uniform(100, 1000, len(dates)),
            }
        ).set_index("datetime")

        # Тестируем расчет признаков
        features_array, metadata = await calculator.prepare_ml_input(
            "BTCUSDT", test_data, lookback=96
        )

        logger.info(f"✅ ML признаки: shape={features_array.shape}")
        logger.info(f"   Metadata: {metadata}")

        # Проверяем дисперсию
        if features_array.size > 0:
            feature_sample = features_array[0]  # Убираем batch dimension
            std_values = np.std(feature_sample, axis=0)
            zero_var_count = np.sum(std_values <= 1e-6)
            logger.info(f"   Zero variance features: {zero_var_count}/{len(std_values)}")

            if zero_var_count > 0:
                logger.warning(f"⚠️ Найдено {zero_var_count} признаков с нулевой дисперсией")
            else:
                logger.info("✅ Все признаки имеют ненулевую дисперсию")

        return True
    except Exception as e:
        logger.error(f"❌ Ошибка генерации ML признаков: {e}")
        return False


async def test_sltp_config():
    """Тест конфигурации SL/TP менеджера"""
    try:
        logger.info("🔍 Тестирование конфигурации SL/TP менеджера...")
        config_manager = ConfigManager()
        await config_manager.initialize()

        sltp_manager = EnhancedSLTPManager(config_manager)
        logger.info("✅ Enhanced SL/TP Manager инициализирован без ошибок")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации SL/TP менеджера: {e}")
        return False


async def main():
    """Главная функция тестирования"""
    logger.info("🚀 Запуск тестов исправлений...")

    tests = [
        ("База данных", test_database_connection),
        ("ML признаки", test_ml_features),
        ("SL/TP менеджер", test_sltp_config),
    ]

    results = []
    for test_name, test_func in tests:
        logger.info(f"\n📋 Тест: {test_name}")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ Критическая ошибка в тесте {test_name}: {e}")
            results.append((test_name, False))

    # Итоги
    logger.info("\n" + "=" * 60)
    logger.info("📊 ИТОГИ ТЕСТИРОВАНИЯ:")
    logger.info("=" * 60)

    passed = 0
    for test_name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        logger.info(f"   {test_name}: {status}")
        if result:
            passed += 1

    total = len(results)
    logger.info(f"\n🏁 Результат: {passed}/{total} тестов пройдено")

    if passed == total:
        logger.info("🎉 Все исправления работают корректно!")
        return True
    else:
        logger.warning(f"⚠️ {total - passed} тестов провалено")
        return False


if __name__ == "__main__":
    asyncio.run(main())
