#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест исправлений критических ML ошибок
"""

import asyncio
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent))

from core.logger import setup_logger
from ml.logic.feature_engineering import FeatureEngineer
from ml.ml_manager import MLManager
from ml.realtime_indicator_calculator import RealTimeIndicatorCalculator

logger = setup_logger(__name__)


def create_sample_ohlcv_data(num_candles: int = 300) -> pd.DataFrame:
    """Создает тестовые OHLCV данные"""
    # Генерируем случайные данные, имитирующие BTCUSDT
    np.random.seed(42)

    base_price = 50000
    dates = pd.date_range(start="2024-01-01", periods=num_candles, freq="15min")

    # Генерируем цены с случайным блужданием
    price_changes = np.random.normal(0, 0.01, num_candles)  # 1% волатильность
    cumulative_changes = np.cumsum(price_changes)

    close_prices = base_price * (1 + cumulative_changes)

    # Генерируем остальные цены относительно close
    high_multiplier = 1 + np.abs(np.random.normal(0, 0.005, num_candles))
    low_multiplier = 1 - np.abs(np.random.normal(0, 0.005, num_candles))
    open_prices = close_prices * (1 + np.random.normal(0, 0.002, num_candles))

    high_prices = np.maximum(close_prices, open_prices) * high_multiplier
    low_prices = np.minimum(close_prices, open_prices) * low_multiplier

    volumes = np.random.exponential(100, num_candles)

    df = pd.DataFrame(
        {
            "datetime": dates,
            "open": open_prices,
            "high": high_prices,
            "low": low_prices,
            "close": close_prices,
            "volume": volumes,
            "symbol": "BTCUSDT",
        }
    )

    df.set_index("datetime", inplace=True)
    return df


async def test_feature_engineering():
    """Тестирует FeatureEngineer на корректность типов"""
    logger.info("🧪 Тестирование FeatureEngineer...")

    # Создаем тестовые данные
    df = create_sample_ohlcv_data(300)

    # Инициализируем FeatureEngineer
    config = {}
    feature_engineer = FeatureEngineer(config)

    try:
        # Тестируем create_features
        features_array = feature_engineer.create_features(df)

        # Проверяем тип результата
        assert isinstance(features_array, np.ndarray), (
            f"Expected np.ndarray, got {type(features_array)}"
        )
        logger.info(
            f"✅ FeatureEngineer.create_features() возвращает {type(features_array)}"
        )
        logger.info(f"✅ Shape: {features_array.shape}")

        # Проверяем что можем обратиться к последней строке
        last_row = features_array[-1]
        assert isinstance(last_row, np.ndarray), (
            f"Expected np.ndarray for last row, got {type(last_row)}"
        )
        logger.info(f"✅ Последняя строка доступна: {len(last_row)} признаков")

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка в FeatureEngineer: {e}")
        return False


async def test_realtime_calculator():
    """Тестирует RealTimeIndicatorCalculator"""
    logger.info("🧪 Тестирование RealTimeIndicatorCalculator...")

    # Создаем тестовые данные
    df = create_sample_ohlcv_data(300)

    # Инициализируем калькулятор
    config = {}
    calculator = RealTimeIndicatorCalculator(config=config)

    try:
        # Тестируем calculate_indicators
        result = await calculator.calculate_indicators("BTCUSDT", df, save_to_db=False)

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "ml_features" in result, "ml_features not found in result"

        ml_features = result["ml_features"]
        assert isinstance(ml_features, dict), (
            f"Expected dict for ml_features, got {type(ml_features)}"
        )
        logger.info(f"✅ calculate_indicators успешно: {len(ml_features)} признаков")

        # Тестируем get_features_for_ml
        features_array = await calculator.get_features_for_ml("BTCUSDT", df)

        assert isinstance(features_array, np.ndarray), (
            f"Expected np.ndarray, got {type(features_array)}"
        )
        assert features_array.ndim == 1, (
            f"Expected 1D array, got {features_array.ndim}D"
        )
        logger.info(f"✅ get_features_for_ml успешно: shape {features_array.shape}")

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка в RealTimeIndicatorCalculator: {e}")
        return False


async def test_ml_manager():
    """Тестирует MLManager"""
    logger.info("🧪 Тестирование MLManager...")

    # Создаем тестовые данные
    df = create_sample_ohlcv_data(300)

    # Инициализируем MLManager
    config = {
        "ml": {
            "model": {
                "device": "cpu",  # Принудительно CPU для тестов
                "model_directory": "models/saved",
            }
        }
    }

    ml_manager = MLManager(config)

    try:
        # Проверяем валидацию типов без инициализации
        try:
            await ml_manager.predict(df)
            logger.error("❌ Должна была быть ошибка инициализации")
            return False
        except ValueError as e:
            if "not initialized" in str(e):
                logger.info("✅ Валидация инициализации работает")
            else:
                raise

        # Проверяем валидацию типов входных данных
        try:
            # Имитируем инициализацию
            ml_manager._initialized = True
            ml_manager.model = "fake_model"  # Заглушка

            await ml_manager.predict("invalid_type")
            logger.error("❌ Должна была быть ошибка типа")
            return False
        except TypeError as e:
            if "must be pd.DataFrame or np.ndarray" in str(e):
                logger.info("✅ Валидация типов входных данных работает")
            else:
                raise

        logger.info("✅ MLManager валидация работает корректно")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка в MLManager: {e}")
        return False


async def main():
    """Основная функция тестирования"""
    logger.info("🚀 Запуск тестов исправлений ML ошибок...")

    results = []

    # Тест 1: FeatureEngineer
    results.append(await test_feature_engineering())

    # Тест 2: RealTimeIndicatorCalculator
    results.append(await test_realtime_calculator())

    # Тест 3: MLManager
    results.append(await test_ml_manager())

    # Подводим итоги
    passed = sum(results)
    total = len(results)

    logger.info(f"\n{'=' * 50}")
    logger.info(f"📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ: {passed}/{total} тестов прошло")

    if passed == total:
        logger.info("🎉 ВСЕ КРИТИЧЕСКИЕ ОШИБКИ ИСПРАВЛЕНЫ!")
        return True
    else:
        logger.error(f"❌ {total - passed} тестов провалилось")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
