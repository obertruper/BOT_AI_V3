#!/usr/bin/env python3
"""
Переобучение scaler'а с исправленными признаками FeatureEngineer
"""

import asyncio
import pickle
import sys
from pathlib import Path

import numpy as np
from sklearn.preprocessing import RobustScaler

sys.path.append(str(Path(__file__).parent))

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from data.data_loader import DataLoader
from ml.logic.archive_old_versions.feature_engineering import FeatureEngineer

logger = setup_logger(__name__)


async def retrain_scaler():
    """Переобучение scaler'а с новыми признаками"""
    try:
        logger.info("🔄 Начинаем переобучение scaler'а...")

        # Инициализация
        config_manager = ConfigManager()
        data_loader = DataLoader(config_manager)
        feature_engineer = FeatureEngineer(config_manager._config)

        # Загружаем данные для всех символов
        symbols = [
            "BTCUSDT",
            "ETHUSDT",
            "BNBUSDT",
            "SOLUSDT",
            "XRPUSDT",
            "ADAUSDT",
            "DOGEUSDT",
            "DOTUSDT",
            "LINKUSDT",
        ]
        all_features = []

        for symbol in symbols:
            logger.info(f"Загружаем данные для {symbol}...")
            try:
                # Получаем данные
                ohlcv_data = await data_loader.get_data_for_ml(symbol, limit=1000)

                if ohlcv_data is None or len(ohlcv_data) < 300:
                    logger.warning(
                        f"Недостаточно данных для {symbol}: {len(ohlcv_data) if ohlcv_data is not None else 0}"
                    )
                    continue

                logger.info(f"Генерируем признаки для {symbol}...")

                # Подготавливаем DataFrame для FeatureEngineer
                df = ohlcv_data.copy().reset_index()  # Переносим индекс в колонки
                if "symbol" not in df.columns:
                    df["symbol"] = symbol
                # datetime уже есть после reset_index()

                # Генерируем признаки с ИСПРАВЛЕННЫМ FeatureEngineer
                features = feature_engineer.create_features(df)

                if features is not None and len(features) > 0:
                    logger.info(f"✅ Сгенерировано {features.shape} признаков для {symbol}")
                    all_features.append(features)
                else:
                    logger.warning(f"Не удалось сгенерировать признаки для {symbol}")

            except Exception as e:
                logger.error(f"Ошибка обработки {symbol}: {e}")
                continue

        if not all_features:
            logger.error("Не удалось получить признаки ни для одного символа!")
            return False

        # Объединяем все признаки
        logger.info("📊 Объединяем признаки всех символов...")
        combined_features = np.vstack(all_features)
        logger.info(f"Итоговый размер данных: {combined_features.shape}")

        # Убираем NaN и Inf
        logger.info("🧹 Очистка данных...")
        finite_mask = np.isfinite(combined_features).all(axis=1)
        clean_features = combined_features[finite_mask]
        logger.info(
            f"После очистки: {clean_features.shape} (удалено {combined_features.shape[0] - clean_features.shape[0]} строк)"
        )

        # Обучаем новый scaler
        logger.info("🔧 Обучаем новый RobustScaler...")
        scaler = RobustScaler()
        scaler.fit(clean_features)

        # Сохраняем scaler
        scaler_path = Path("models/saved/data_scaler.pkl")
        scaler_path.parent.mkdir(parents=True, exist_ok=True)

        with open(scaler_path, "wb") as f:
            pickle.dump(scaler, f)

        logger.info(f"✅ Новый scaler сохранен: {scaler_path}")

        # Проверяем качество нормализации
        normalized = scaler.transform(clean_features[:100])  # Тестируем на первых 100 строках
        logger.info("📈 Статистика нормализованных данных:")
        logger.info(f"  Среднее: {np.mean(normalized):.6f}")
        logger.info(f"  Стандартное отклонение: {np.std(normalized):.6f}")
        logger.info(f"  Мин: {np.min(normalized):.6f}")
        logger.info(f"  Макс: {np.max(normalized):.6f}")

        # Проверяем разнообразие признаков
        feature_vars = np.var(clean_features, axis=0)
        const_features = np.sum(feature_vars < 1e-8)
        logger.info("🎯 Анализ признаков:")
        logger.info(f"  Всего признаков: {clean_features.shape[1]}")
        logger.info(f"  Константных признаков: {const_features}")
        logger.info(f"  Переменных признаков: {clean_features.shape[1] - const_features}")

        if const_features > clean_features.shape[1] * 0.5:
            logger.warning(
                f"⚠️ Много константных признаков: {const_features}/{clean_features.shape[1]}"
            )
        else:
            logger.info(
                f"✅ Признаки разнообразные: {const_features}/{clean_features.shape[1]} константных"
            )

        return True

    except Exception as e:
        logger.error(f"Ошибка переобучения scaler'а: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = asyncio.run(retrain_scaler())
    if success:
        print("✅ Scaler успешно переобучен!")
    else:
        print("❌ Ошибка переобучения scaler'а")
        sys.exit(1)
