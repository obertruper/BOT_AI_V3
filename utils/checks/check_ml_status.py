#!/usr/bin/env python3
"""
Проверка статуса ML системы
"""

import asyncio
import logging
import os

import yaml

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def check_ml_system():
    """Проверка ML системы"""
    try:
        # Загружаем конфигурацию
        from core.config.config_manager import ConfigManager
        from ml.ml_manager import MLManager
        from ml.ml_signal_processor import MLSignalProcessor

        logger.info("🔍 Проверка ML системы...")

        # Инициализация конфигурации
        config_manager = ConfigManager()
        config_manager.get_ml_config()  # Проверяем что конфигурация загружается

        # Проверка символов
        # Получаем полную конфигурацию системы
        full_config = config_manager._config  # Обращаемся к полной конфигурации
        traders = full_config.get("traders", [])

        ml_trader = None
        for trader in traders:
            if trader.get("id") == "ml_trader_multi_crypto":
                ml_trader = trader
                break

        if ml_trader:
            symbols = ml_trader.get("symbols", [])
            logger.info(f"✅ ML трейдер найден с {len(symbols)} символами:")
            for symbol in symbols:
                logger.info(f"   - {symbol}")
        else:
            logger.error("❌ ML трейдер 'ml_trader_multi_crypto' не найден!")
            return

        # Проверка ML Manager
        logger.info("\n🧠 Инициализация ML Manager...")
        # ML Manager ожидает полную конфигурацию ML из файла ml_config.yaml
        ml_config_path = os.path.join(os.path.dirname(__file__), "config", "ml", "ml_config.yaml")
        with open(ml_config_path) as f:
            ml_full_config = yaml.safe_load(f)
        ml_manager = MLManager(config=ml_full_config)
        logger.info(f"✅ ML Manager инициализирован на устройстве: {ml_manager.device}")

        # Проверка модели
        if hasattr(ml_manager, "model") and ml_manager.model is not None:
            logger.info("✅ ML модель загружена")
        else:
            logger.error("❌ ML модель не загружена!")

        # Проверка ML Signal Processor
        logger.info("\n📊 Инициализация ML Signal Processor...")
        MLSignalProcessor(ml_manager=ml_manager, config={"symbols": symbols})
        logger.info("✅ ML Signal Processor инициализирован")

        # Генерация тестового сигнала
        logger.info("\n🎯 Генерация тестового ML сигнала...")
        import numpy as np
        import pandas as pd

        from ml.logic.archive_old_versions.feature_engineering import FeatureEngineer

        # Создаем тестовые данные
        test_data = pd.DataFrame(
            {
                "open": np.random.uniform(100, 110, 100),
                "high": np.random.uniform(110, 120, 100),
                "low": np.random.uniform(90, 100, 100),
                "close": np.random.uniform(95, 115, 100),
                "volume": np.random.uniform(1000, 10000, 100),
                "timestamp": pd.date_range(start="2025-08-09", periods=100, freq="15min"),
            }
        )

        # Генерируем признаки
        feature_engineer = FeatureEngineer()
        features = feature_engineer.engineer_features(test_data)

        if features is not None and not features.empty:
            logger.info(f"✅ Сгенерировано {features.shape[1]} признаков")

            # Делаем предсказание
            try:
                prediction = await ml_manager.predict(features, symbol="BTCUSDT")
                if prediction:
                    logger.info("✅ ML предсказание получено:")
                    logger.info(f"   - Signal Type: {prediction.get('signal_type', 'N/A')}")
                    logger.info(f"   - Confidence: {prediction.get('confidence', 0):.2%}")
                    logger.info(f"   - Risk Level: {prediction.get('risk_level', 'N/A')}")
                else:
                    logger.error("❌ Предсказание не получено")
            except Exception as e:
                logger.error(f"❌ Ошибка при предсказании: {e}")
        else:
            logger.error("❌ Не удалось сгенерировать признаки")

        logger.info("\n✨ Проверка завершена!")

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_ml_system())
