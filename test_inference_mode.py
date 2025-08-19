#!/usr/bin/env python3
"""
Тест для проверки работы inference mode
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from core.logger import setup_logger
from ml.config.features_240 import REQUIRED_FEATURES_240
from ml.logic.archive_old_versions.feature_engineering_v2 import FeatureEngineer

logger = setup_logger("test_inference_mode")


def test_inference_mode():
    """
    Тестирует работу inference mode в feature engineering
    """
    try:
        logger.info("=" * 60)
        logger.info("🧪 ТЕСТ INFERENCE MODE")
        logger.info("=" * 60)

        # 1. Создаем тестовые данные
        logger.info("\n1️⃣ Создание тестовых OHLCV данных...")

        dates = pd.date_range(end=pd.Timestamp.now(), periods=300, freq="15min")
        price_base = 50000  # BTC цена
        price_changes = np.random.randn(300) * 0.001
        prices = price_base * np.cumprod(1 + price_changes)

        test_data = pd.DataFrame(
            {
                "datetime": dates,
                "open": prices * (1 + np.random.randn(300) * 0.0001),
                "high": prices * (1 + np.abs(np.random.randn(300)) * 0.0002),
                "low": prices * (1 - np.abs(np.random.randn(300)) * 0.0002),
                "close": prices,
                "volume": np.random.randint(100, 1000, 300).astype(float),
                "symbol": "BTCUSDT",
            }
        )
        test_data["turnover"] = test_data["close"] * test_data["volume"]

        logger.info(f"  ✅ Создано {len(test_data)} свечей для BTCUSDT")

        # 2. Инициализируем FeatureEngineer
        logger.info("\n2️⃣ Инициализация FeatureEngineer...")

        config = {"features": {}}
        engineer = FeatureEngineer(config)
        engineer.disable_progress = True  # Отключаем прогресс для теста

        # 3. Генерируем признаки БЕЗ inference mode
        logger.info("\n3️⃣ Генерация признаков БЕЗ inference mode...")

        features_full = engineer.create_features(test_data.copy(), inference_mode=False)

        # Фильтруем числовые колонки
        numeric_cols_full = features_full.select_dtypes(include=[np.number]).columns.tolist()
        # Исключаем метаданные
        metadata = ["open", "high", "low", "close", "volume", "turnover"]
        features_cols_full = [col for col in numeric_cols_full if col not in metadata]

        logger.info(f"  📊 Сгенерировано признаков (полный режим): {len(features_cols_full)}")
        logger.info(f"  📊 Всего колонок в DataFrame: {len(features_full.columns)}")

        # 4. Генерируем признаки С inference mode
        logger.info("\n4️⃣ Генерация признаков С inference mode...")

        features_inference = engineer.create_features(test_data.copy(), inference_mode=True)

        # Фильтруем числовые колонки
        numeric_cols_inference = features_inference.select_dtypes(
            include=[np.number]
        ).columns.tolist()
        # Исключаем метаданные
        features_cols_inference = [col for col in numeric_cols_inference if col not in metadata]

        logger.info(
            f"  📊 Сгенерировано признаков (inference mode): {len(features_cols_inference)}"
        )
        logger.info(f"  📊 Всего колонок в DataFrame: {len(features_inference.columns)}")

        # 5. Проверка количества
        logger.info("\n5️⃣ Проверка соответствия ожиданиям...")

        if len(features_cols_inference) == 240:
            logger.info("  ✅ УСПЕХ: Inference mode генерирует ровно 240 признаков!")
        else:
            logger.error(f"  ❌ ОШИБКА: Ожидалось 240, получено {len(features_cols_inference)}")

            # Анализ разницы
            logger.info("\n  📊 Анализ признаков:")
            logger.info(f"     Полный режим: {len(features_cols_full)} признаков")
            logger.info(f"     Inference mode: {len(features_cols_inference)} признаков")
            logger.info(f"     Разница: {len(features_cols_full) - len(features_cols_inference)}")

        # 6. Проверка наличия нужных признаков
        logger.info("\n6️⃣ Проверка наличия требуемых признаков...")

        missing_features = []
        for feature in REQUIRED_FEATURES_240[:10]:  # Проверяем первые 10
            if feature not in features_inference.columns:
                missing_features.append(feature)

        if missing_features:
            logger.warning(f"  ⚠️ Отсутствуют признаки: {missing_features}")
        else:
            logger.info("  ✅ Основные признаки присутствуют")

        # 7. Проверка значений
        logger.info("\n7️⃣ Проверка значений признаков...")

        # Берем последнюю строку
        last_row = features_inference.iloc[-1]

        # Статистика для числовых признаков
        numeric_values = last_row[features_cols_inference]
        # Конвертируем в числовые значения
        numeric_values = pd.to_numeric(numeric_values, errors="coerce")
        non_zero = np.sum(numeric_values != 0)
        non_nan = np.sum(~numeric_values.isna())

        logger.info("  📊 Статистика последней строки:")
        logger.info(
            f"     - Ненулевых: {non_zero}/{len(numeric_values)} ({non_zero / len(numeric_values) * 100:.1f}%)"
        )
        logger.info(
            f"     - Не NaN: {non_nan}/{len(numeric_values)} ({non_nan / len(numeric_values) * 100:.1f}%)"
        )

        # 8. Итоговый вердикт
        logger.info("\n" + "=" * 60)
        logger.info("📊 ИТОГОВЫЙ РЕЗУЛЬТАТ")
        logger.info("=" * 60)

        success = True

        if len(features_cols_inference) != 240:
            logger.error(
                f"❌ Неверное количество признаков: {len(features_cols_inference)} вместо 240"
            )
            success = False

        if non_zero < len(numeric_values) * 0.3:
            logger.error(f"❌ Слишком много нулевых признаков: {len(numeric_values) - non_zero}")
            success = False

        if success:
            logger.info("✅ ТЕСТ УСПЕШНО ПРОЙДЕН!")
            logger.info("  - Inference mode работает корректно")
            logger.info("  - Генерируется ровно 240 признаков")
        else:
            logger.error("❌ ТЕСТ НЕ ПРОЙДЕН")
            logger.info("\n💡 РЕКОМЕНДАЦИИ:")
            logger.info("  1. Проверьте логику фильтрации в create_features")
            logger.info("  2. Убедитесь, что REQUIRED_FEATURES_240 правильно импортируется")
            logger.info("  3. Проверьте, что все необходимые методы вызываются")

        return success

    except Exception as e:
        logger.error(f"❌ Ошибка теста: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_inference_mode()
    sys.exit(0 if success else 1)
