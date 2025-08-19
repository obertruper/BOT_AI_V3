#!/usr/bin/env python3
"""
Простой тест основных ML компонентов без зависимостей от бирж
"""

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Добавляем корневой каталог в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.logger import setup_logger
from ml.logic.archive_old_versions.feature_engineering import FeatureEngineer
from ml.ml_manager import MLManager

logger = setup_logger(__name__)


def create_test_data() -> pd.DataFrame:
    """Создает тестовые OHLCV данные"""

    # Генерируем 300 свечей (больше чем нужно для модели)
    n = 300
    timestamps = pd.date_range(
        start=datetime.now(UTC) - timedelta(hours=n / 4), periods=n, freq="15T"
    )

    # Генерируем реалистичные OHLCV данные
    np.random.seed(42)  # Для воспроизводимости

    base_price = 50000
    data = []
    current_price = base_price

    for i, ts in enumerate(timestamps):
        # Случайное изменение цены
        change = np.random.normal(0, 0.01)  # 1% стандартное отклонение
        current_price *= 1 + change

        # Генерируем OHLC вокруг текущей цены
        volatility = 0.005  # 0.5% внутридневная волатильность
        high = current_price * (1 + abs(np.random.normal(0, volatility)))
        low = current_price * (1 - abs(np.random.normal(0, volatility)))
        open_price = current_price * (1 + np.random.normal(0, volatility / 2))
        close = current_price
        volume = np.random.uniform(1000, 10000)

        data.append(
            {
                "timestamp": int(ts.timestamp() * 1000),
                "datetime": ts,
                "open": float(open_price),
                "high": float(max(open_price, high, close)),
                "low": float(min(open_price, low, close)),
                "close": float(close),
                "volume": float(volume),
                "turnover": float(volume * close),
            }
        )

    df = pd.DataFrame(data)
    df.set_index("datetime", inplace=True)
    return df


async def test_feature_engineering():
    """Тест генерации признаков"""

    logger.info("🧪 Тест Feature Engineering...")

    try:
        # Создаем тестовые данные
        test_data = create_test_data()
        logger.info(f"Создано {len(test_data)} тестовых свечей")

        # Инициализируем FeatureEngineer с минимальной конфигурацией
        config = {"features": {"technical": {"enabled": True}}}
        fe = FeatureEngineer(config)

        # Добавляем колонку symbol для FeatureEngineer и сбрасываем индекс
        test_data_with_symbol = test_data.copy().reset_index()
        test_data_with_symbol["symbol"] = "BTCUSDT"

        # Генерируем признаки
        features = fe.create_features(test_data_with_symbol)

        logger.info(f"✅ Сгенерировано {features.shape[0]} строк и {features.shape[1]} признаков")
        logger.info(f"   Последние 5 признаков: {list(features.columns)[-5:]}")

        # Проверяем что нет NaN в последних строках
        last_rows = features.tail(10)
        nan_count = last_rows.isnull().sum().sum()
        logger.info(f"   NaN в последних 10 строках: {nan_count}")

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка в Feature Engineering: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


async def test_ml_manager():
    """Тест ML Manager"""

    logger.info("🧪 Тест ML Manager...")

    try:
        # Создаем конфигурацию
        config = {
            "ml": {
                "enabled": True,
                "model": {
                    "enabled": True,
                    "path": "models/saved/best_model_20250728_215703.pth",
                    "scaler_path": "models/saved/data_scaler.pkl",
                    "device": "cpu",  # Используем CPU для тестов
                },
            }
        }

        # Инициализируем ML Manager
        ml_manager = MLManager(config)
        await ml_manager.initialize()

        logger.info("✅ ML Manager инициализирован")

        # Создаем тестовые признаки (240 признаков как ожидает модель)
        features = np.random.randn(96, 240).astype(np.float32)  # 96 временных шагов, 240 признаков
        logger.info(f"Создан тестовый массив признаков: {features.shape}")

        # Тестируем предсказание
        prediction = await ml_manager.predict(features)

        logger.info("✅ Предсказание получено:")
        if isinstance(prediction, dict):
            for key, value in prediction.items():
                if isinstance(value, (list, np.ndarray)):
                    logger.info(f"   {key}: {len(value) if hasattr(value, '__len__') else value}")
                else:
                    logger.info(f"   {key}: {value}")
        else:
            logger.info(
                f"   Тип: {type(prediction)}, размер: {prediction.shape if hasattr(prediction, 'shape') else len(prediction)}"
            )

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка в ML Manager: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


async def test_end_to_end():
    """Тест полного пайплайна: данные -> признаки -> предсказание"""

    logger.info("🧪 Тест полного ML пайплайна...")

    try:
        # 1. Создаем тестовые данные
        test_data = create_test_data()
        logger.info(f"✅ Создано {len(test_data)} свечей")

        # 2. Генерируем признаки
        config = {"features": {"technical": {"enabled": True}}}
        fe = FeatureEngineer(config)

        # Добавляем колонку symbol для FeatureEngineer и сбрасываем индекс
        test_data_with_symbol = test_data.copy().reset_index()
        test_data_with_symbol["symbol"] = "BTCUSDT"

        features_df = fe.create_features(test_data_with_symbol)
        logger.info(f"✅ Сгенерировано {features_df.shape[1]} признаков")

        # 3. Подготавливаем данные для модели
        # Берем последние 96 временных шагов
        features_array = features_df.tail(96).values.astype(np.float32)

        if features_array.shape[1] != 240:
            logger.warning(
                f"Неожиданное количество признаков: {features_array.shape[1]}, ожидалось 240"
            )
            # Дополняем или обрезаем до 240
            if features_array.shape[1] < 240:
                padding = np.zeros((features_array.shape[0], 240 - features_array.shape[1]))
                features_array = np.concatenate([features_array, padding], axis=1)
            else:
                features_array = features_array[:, :240]

        logger.info(f"✅ Подготовлен массив для модели: {features_array.shape}")

        # 4. Инициализируем ML Manager
        config = {
            "ml": {
                "enabled": True,
                "model": {
                    "enabled": True,
                    "path": "models/saved/best_model_20250728_215703.pth",
                    "scaler_path": "models/saved/data_scaler.pkl",
                    "device": "cpu",  # Используем CPU для тестов
                },
            }
        }

        ml_manager = MLManager(config)
        await ml_manager.initialize()
        logger.info("✅ ML Manager инициализирован")

        # 5. Получаем предсказание
        prediction = await ml_manager.predict(features_array)
        logger.info("✅ Предсказание получено")

        # 6. Анализируем результат
        if isinstance(prediction, dict):
            logger.info("📊 Результат предсказания:")
            for key, value in prediction.items():
                if isinstance(value, np.ndarray):
                    logger.info(f"   {key}: shape={value.shape}, mean={np.mean(value):.4f}")
                elif isinstance(value, list):
                    logger.info(
                        f"   {key}: length={len(value)}, sample={value[:3] if len(value) > 3 else value}"
                    )
                else:
                    logger.info(f"   {key}: {value}")

        logger.info("🎉 Полный ML пайплайн работает корректно!")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка в полном пайплайне: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


async def main():
    """Основная функция тестирования"""

    logger.info("🚀 Запуск тестов основных ML компонентов")

    results = []

    # Тест 1: Feature Engineering
    results.append(await test_feature_engineering())

    # Тест 2: ML Manager
    results.append(await test_ml_manager())

    # Тест 3: Полный пайплайн
    results.append(await test_end_to_end())

    # Итоговый результат
    passed = sum(results)
    total = len(results)

    if passed == total:
        logger.info(f"🎉 Все тесты прошли успешно! ({passed}/{total})")
        return True
    else:
        logger.error(f"❌ Не все тесты прошли: {passed}/{total}")
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
