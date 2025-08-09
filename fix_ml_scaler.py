#!/usr/bin/env python3
"""
Скрипт для переобучения scaler на актуальных данных
Решает проблему несоответствия нормализации
"""

import asyncio
import pickle
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler

sys.path.append("/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3")

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from data.data_loader import DataLoader
from ml.logic.feature_engineering import FeatureEngineer

logger = setup_logger("fix_ml_scaler")


async def retrain_scaler():
    """Переобучаем scaler на актуальных данных"""

    logger.info("🔧 ПЕРЕОБУЧЕНИЕ SCALER НА АКТУАЛЬНЫХ ДАННЫХ")
    logger.info("=" * 50)

    # Инициализация
    data_loader = DataLoader()
    config_manager = ConfigManager()
    feature_engineer = FeatureEngineer(config_manager.get_ml_config())

    try:
        await data_loader.initialize()

        # Символы для обучения scaler
        training_symbols = [
            "BTCUSDT",
            "ETHUSDT",
            "ADAUSDT",
            "BNBUSDT",
            "XRPUSDT",
            "SOLUSDT",
            "DOTUSDT",
            "LINKUSDT",
        ]

        logger.info(f"Сбор данных из {len(training_symbols)} символов...")

        all_features = []

        for symbol in training_symbols:
            logger.info(f"  Обработка {symbol}...")

            # Загружаем данные
            data = await data_loader.get_data_for_ml(symbol, limit=2000)

            if data is None or len(data) < 300:
                logger.warning(
                    f"  Недостаточно данных для {symbol}: {len(data) if data is not None else 0}"
                )
                continue

            # Генерируем признаки
            features = feature_engineer.create_features(data)

            if isinstance(features, pd.DataFrame):
                # Извлекаем числовые признаки
                numeric_cols = features.select_dtypes(include=[np.number]).columns
                # Исключаем целевые переменные и метаданные
                feature_cols = [
                    col
                    for col in numeric_cols
                    if not col.startswith(("future_", "direction_", "profit_"))
                    and col not in ["id", "timestamp", "datetime", "symbol"]
                ]
                features_array = features[feature_cols].values
            elif isinstance(features, np.ndarray):
                features_array = features
            else:
                logger.error(
                    f"  Неожиданный тип признаков для {symbol}: {type(features)}"
                )
                continue

            # Убираем NaN и Inf
            mask = np.isfinite(features_array).all(axis=1)
            features_clean = features_array[mask]

            if len(features_clean) > 0:
                all_features.append(features_clean)
                logger.info(
                    f"  Добавлено {len(features_clean)} образцов, размерность: {features_clean.shape[1]}"
                )
            else:
                logger.warning(f"  Нет валидных данных для {symbol}")

        if not all_features:
            logger.error("❌ Не удалось собрать данные ни для одного символа!")
            return False

        # Объединяем все признаки
        X = np.vstack(all_features)
        logger.info(f"Общий размер данных для обучения scaler: {X.shape}")

        # Проверяем размерность
        expected_features = 240
        if X.shape[1] != expected_features:
            logger.warning(
                f"⚠️ Несоответствие размерности признаков: ожидалось {expected_features}, получено {X.shape[1]}"
            )

            if X.shape[1] < expected_features:
                # Дополняем нулями
                padding = np.zeros((X.shape[0], expected_features - X.shape[1]))
                X = np.hstack([X, padding])
                logger.info(f"Дополнено нулями до {X.shape[1]} признаков")
            else:
                # Обрезаем
                X = X[:, :expected_features]
                logger.info(f"Обрезано до {X.shape[1]} признаков")

        # Обучаем новый scaler
        logger.info("Обучение нового RobustScaler...")
        new_scaler = RobustScaler(
            quantile_range=(5.0, 95.0)
        )  # Более робастный диапазон
        new_scaler.fit(X)

        # Тестируем новый scaler
        logger.info("Тестирование нового scaler...")

        # Берем небольшую выборку для теста
        test_sample = X[:1000] if len(X) > 1000 else X[:100]
        scaled_test = new_scaler.transform(test_sample)

        logger.info("Результаты тестирования:")
        logger.info(
            f"  Исходные данные - среднее: {test_sample.mean():.2f}, std: {test_sample.std():.2f}"
        )
        logger.info(
            f"  После scaler - среднее: {scaled_test.mean():.6f}, std: {scaled_test.std():.6f}"
        )
        logger.info(
            f"  Диапазон после scaler: [{scaled_test.min():.3f}, {scaled_test.max():.3f}]"
        )

        # Проверяем разумность значений
        if abs(scaled_test.mean()) > 1.0 or scaled_test.std() > 10.0:
            logger.error("❌ Новый scaler дает подозрительные значения!")
            return False

        # Сохраняем старый scaler как бэкап
        model_dir = Path("models/saved")
        old_scaler_path = model_dir / "data_scaler.pkl"
        backup_path = (
            model_dir
            / f"data_scaler_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        )

        if old_scaler_path.exists():
            import shutil

            shutil.copy2(old_scaler_path, backup_path)
            logger.info(f"Старый scaler сохранен как: {backup_path}")

        # Сохраняем новый scaler
        with open(old_scaler_path, "wb") as f:
            pickle.dump(new_scaler, f)

        logger.info(f"✅ Новый scaler сохранен: {old_scaler_path}")

        # Дополнительная проверка - сравниваем разные символы
        logger.info("\nПроверка различий между символами с новым scaler:")

        for symbol in ["BTCUSDT", "ETHUSDT"][:2]:  # Берем только 2 для быстрой проверки
            data = await data_loader.get_data_for_ml(symbol, limit=100)
            if data is not None:
                features = feature_engineer.create_features(data)
                if isinstance(features, pd.DataFrame):
                    numeric_cols = features.select_dtypes(include=[np.number]).columns
                    feature_cols = [
                        col
                        for col in numeric_cols
                        if not col.startswith(("future_", "direction_", "profit_"))
                        and col not in ["id", "timestamp", "datetime", "symbol"]
                    ]
                    features_array = features[feature_cols].values
                elif isinstance(features, np.ndarray):
                    features_array = features

                if features_array.shape[1] != expected_features:
                    if features_array.shape[1] < expected_features:
                        padding = np.zeros(
                            (
                                features_array.shape[0],
                                expected_features - features_array.shape[1],
                            )
                        )
                        features_array = np.hstack([features_array, padding])
                    else:
                        features_array = features_array[:, :expected_features]

                scaled = new_scaler.transform(features_array[-1:])  # Последняя строка
                logger.info(
                    f"  {symbol}: среднее={scaled.mean():.6f}, std={scaled.std():.6f}"
                )

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка переобучения scaler: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        await data_loader.cleanup()


if __name__ == "__main__":
    success = asyncio.run(retrain_scaler())
    if success:
        print("✅ Scaler успешно переобучен!")
        print("🔄 Перезапустите ML систему для применения изменений")
    else:
        print("❌ Ошибка переобучения scaler!")
