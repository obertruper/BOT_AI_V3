#!/usr/bin/env python3
"""
Тест исправления формата ML модели
"""
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from ml.ml_manager import MLManager

logger = setup_logger(__name__)


async def test_ml_format():
    """Тест правильного формата возвращаемых данных ML"""
    try:
        logger.info("🧪 Тестирование исправления формата ML данных...")

        # Инициализация
        config_manager = ConfigManager()
        await config_manager.initialize()

        ml_manager = MLManager(config_manager.get_config())
        await ml_manager.initialize()

        # Создаем тестовые данные
        dates = pd.date_range(
            start=datetime.now() - timedelta(hours=37.5), end=datetime.now(), freq="15min"
        )[:150]

        np.random.seed(42)
        close_prices = 50000 + np.cumsum(np.random.randn(len(dates)) * 100)

        test_data = pd.DataFrame(
            {
                "datetime": dates,
                "open": close_prices * (1 + np.random.randn(len(dates)) * 0.001),
                "high": close_prices * (1 + np.abs(np.random.randn(len(dates)) * 0.002)),
                "low": close_prices * (1 - np.abs(np.random.randn(len(dates)) * 0.002)),
                "close": close_prices,
                "volume": np.random.uniform(100, 1000, len(dates)),
                "turnover": close_prices * np.random.uniform(100, 1000, len(dates)),
                "symbol": "BTCUSDT",
            }
        )
        # НЕ делаем datetime индексом, оставляем как колонку

        # Тестируем предсказание
        result = await ml_manager.predict(test_data, symbol="BTCUSDT")

        # Проверяем тип результата
        if isinstance(result, dict):
            logger.info("✅ ML Manager возвращает dict как ожидалось")

            # Проверяем ключевые поля
            expected_fields = ["signal_type", "confidence", "signal_strength"]
            found_fields = [field for field in expected_fields if field in result]

            logger.info(f"   Найденные поля: {found_fields}")
            logger.info(f"   Всего ключей в result: {len(result)}")

            if len(found_fields) >= 2:
                logger.info("✅ Основные поля присутствуют в результате")
                return True
            else:
                logger.warning("⚠️ Не все ожидаемые поля найдены")
                logger.info(f"   Все ключи: {list(result.keys())}")
                return False

        elif isinstance(result, np.ndarray):
            logger.error("❌ ML Manager все еще возвращает numpy array!")
            return False
        else:
            logger.error(f"❌ ML Manager возвращает неожиданный тип: {type(result)}")
            return False

    except Exception as e:
        logger.error(f"❌ Ошибка в тесте: {e}")
        return False


async def main():
    logger.info("🚀 Проверка исправления формата ML данных...")

    success = await test_ml_format()

    if success:
        logger.info("🎉 Исправление работает корректно!")
    else:
        logger.warning("⚠️ Требуются дополнительные исправления")

    return success


if __name__ == "__main__":
    asyncio.run(main())
