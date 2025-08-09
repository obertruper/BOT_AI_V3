#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Диагностика потери уникальности в ML pipeline BOT_AI_V3
Отслеживает передачу данных между компонентами для выявления места потери уникальности
"""

import asyncio
import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent))

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from data.data_loader import DataLoader
from ml.logic.feature_engineering import FeatureEngineer
from ml.ml_manager import MLManager
from ml.ml_signal_processor import MLSignalProcessor
from ml.realtime_indicator_calculator import RealTimeIndicatorCalculator

logger = setup_logger(__name__)


class MLUniquenessDiagnostic:
    """
    Диагностический класс для отслеживания уникальности в ML pipeline
    """

    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()
        self.ml_manager = None
        self.signal_processor = None
        self.feature_engineer = None
        self.indicator_calculator = None
        self.data_loader = None

    async def initialize(self):
        """Инициализация всех компонентов"""
        logger.info("🔄 Инициализация диагностических компонентов...")

        # Инициализируем ML Manager
        self.ml_manager = MLManager(self.config)
        await self.ml_manager.initialize()

        # Инициализируем Signal Processor
        self.signal_processor = MLSignalProcessor(
            ml_manager=self.ml_manager,
            config=self.config,
            config_manager=self.config_manager,
        )
        await self.signal_processor.initialize()

        # Инициализируем Feature Engineer
        self.feature_engineer = FeatureEngineer(self.config)

        # Инициализируем Indicator Calculator
        self.indicator_calculator = RealTimeIndicatorCalculator(
            cache_ttl=300, config=self.config
        )

        # Инициализируем Data Loader
        self.data_loader = DataLoader(self.config_manager)

        logger.info("✅ Диагностические компоненты инициализированы")

    def calculate_data_hash(self, data, description=""):
        """Вычисляет хэш данных для отслеживания уникальности"""
        if isinstance(data, pd.DataFrame):
            # Для DataFrame используем хэш значений
            if not data.empty:
                # Включаем symbol в хэш если есть
                if "symbol" in data.columns:
                    symbol_info = f"_{data['symbol'].iloc[0]}" if len(data) > 0 else ""
                else:
                    symbol_info = "_no_symbol"

                hash_data = str(data.values.tobytes()) + symbol_info
            else:
                hash_data = "empty_dataframe"
        elif isinstance(data, np.ndarray):
            hash_data = str(data.tobytes())
        else:
            hash_data = str(data)

        data_hash = hashlib.md5(hash_data.encode()).hexdigest()[:8]
        logger.info(
            f"🔍 [{description}] Hash: {data_hash}, Shape: {getattr(data, 'shape', 'N/A')}"
        )

        if isinstance(data, pd.DataFrame) and not data.empty:
            if "symbol" in data.columns:
                logger.info(
                    f"   Symbol: {data['symbol'].iloc[0] if len(data) > 0 else 'unknown'}"
                )
            else:
                logger.warning("   ❌ Symbol колонки НЕТ в данных!")

        return data_hash

    async def test_symbol_propagation(self, symbols=["BTCUSDT", "ETHUSDT"]):
        """Тестирует передачу символов через весь pipeline"""
        logger.info(f"🧪 Тестирование передачи символов: {symbols}")

        results = {}

        for symbol in symbols:
            logger.info(f"\n📊 === Тестирование символа {symbol} ===")

            # 1. Получаем OHLCV данные
            logger.info("1️⃣ Получение OHLCV данных...")
            ohlcv_df = await self.signal_processor._fetch_latest_ohlcv(
                symbol=symbol, exchange="bybit", lookback_minutes=7200
            )

            if ohlcv_df is None or len(ohlcv_df) < 96:
                logger.error(f"❌ Недостаточно данных для {symbol}")
                continue

            # Проверяем наличие symbol в OHLCV
            ohlcv_hash = self.calculate_data_hash(ohlcv_df, f"OHLCV for {symbol}")

            # 2. Проверяем передачу в indicator_calculator
            logger.info("2️⃣ Вызов prepare_ml_input...")
            features_array, metadata = await self.indicator_calculator.prepare_ml_input(
                symbol=symbol,
                ohlcv_df=ohlcv_df,
                lookback=96,
            )

            features_hash = self.calculate_data_hash(
                features_array, f"Features for {symbol}"
            )

            # 3. Проверяем передачу в ml_manager
            logger.info("3️⃣ Вызов ml_manager.predict...")
            prediction = await self.ml_manager.predict(features_array)

            prediction_hash = self.calculate_data_hash(
                str(prediction), f"Prediction for {symbol}"
            )

            # 4. Сохраняем результаты
            results[symbol] = {
                "ohlcv_hash": ohlcv_hash,
                "features_hash": features_hash,
                "prediction_hash": prediction_hash,
                "prediction": prediction,
                "metadata": metadata,
            }

            logger.info(f"✅ {symbol} обработан")

        # Анализируем результаты
        logger.info("\n📋 === АНАЛИЗ УНИКАЛЬНОСТИ ===")

        # Проверяем уникальность хэшей
        ohlcv_hashes = [r["ohlcv_hash"] for r in results.values()]
        features_hashes = [r["features_hash"] for r in results.values()]
        prediction_hashes = [r["prediction_hash"] for r in results.values()]

        logger.info(f"OHLCV хэши: {ohlcv_hashes}")
        logger.info(f"Features хэши: {features_hashes}")
        logger.info(f"Prediction хэши: {prediction_hashes}")

        # Выводы
        if len(set(ohlcv_hashes)) == len(symbols):
            logger.info("✅ OHLCV данные уникальны для каждого символа")
        else:
            logger.error("❌ OHLCV данные ОДИНАКОВЫЕ для разных символов!")

        if len(set(features_hashes)) == len(symbols):
            logger.info("✅ Feature данные уникальны для каждого символа")
        else:
            logger.error("❌ Feature данные ОДИНАКОВЫЕ для разных символов!")

        if len(set(prediction_hashes)) == len(symbols):
            logger.info("✅ Predictions уникальны для каждого символа")
        else:
            logger.error("❌ Predictions ОДИНАКОВЫЕ для разных символов!")

        # Детальный анализ predictions
        logger.info("\n📋 === ДЕТАЛЬНЫЙ АНАЛИЗ PREDICTIONS ===")
        for symbol, result in results.items():
            pred = result["prediction"]
            logger.info(f"{symbol}:")
            logger.info(f"  Тип: {type(pred)}")
            if isinstance(pred, dict):
                for key, value in pred.items():
                    logger.info(f"    {key}: {value}")
            else:
                logger.info(f"  Значение: {pred}")

        return results

    async def test_direct_feature_generation(self, symbols=["BTCUSDT", "ETHUSDT"]):
        """Тестирует генерацию признаков напрямую через FeatureEngineer"""
        logger.info(f"🔬 Прямое тестирование FeatureEngineer для символов: {symbols}")

        results = {}

        for symbol in symbols:
            logger.info(f"\n📊 === Прямой тест {symbol} ===")

            # Получаем OHLCV данные
            ohlcv_df = await self.signal_processor._fetch_latest_ohlcv(
                symbol=symbol, exchange="bybit", lookback_minutes=7200
            )

            if ohlcv_df is None or len(ohlcv_df) < 96:
                logger.error(f"❌ Недостаточно данных для {symbol}")
                continue

            # Проверяем есть ли symbol в DataFrame
            if "symbol" not in ohlcv_df.columns:
                logger.warning(f"⚠️ Добавляем symbol={symbol} в DataFrame")
                ohlcv_df["symbol"] = symbol

            ohlcv_hash = self.calculate_data_hash(
                ohlcv_df, f"Direct OHLCV for {symbol}"
            )

            # Генерируем признаки напрямую
            logger.info(f"Генерация признаков напрямую для {symbol}...")
            features = self.feature_engineer.create_features(ohlcv_df)

            features_hash = self.calculate_data_hash(
                features, f"Direct Features for {symbol}"
            )

            results[symbol] = {
                "ohlcv_hash": ohlcv_hash,
                "features_hash": features_hash,
                "features_shape": features.shape,
            }

        # Анализ результатов прямой генерации
        logger.info("\n📋 === АНАЛИЗ ПРЯМОЙ ГЕНЕРАЦИИ ===")

        features_hashes = [r["features_hash"] for r in results.values()]
        logger.info(f"Прямые Features хэши: {features_hashes}")

        if len(set(features_hashes)) == len(symbols):
            logger.info("✅ Прямая генерация признаков уникальна для каждого символа")
        else:
            logger.error(
                "❌ Прямая генерация признаков ОДИНАКОВАЯ для разных символов!"
            )

        return results

    async def test_cache_behavior(self):
        """Тестирует поведение кэша в ml_signal_processor"""
        logger.info("🧪 Тестирование поведения кэша...")

        # Очищаем кэш
        self.signal_processor.prediction_cache.clear()

        symbol = "BTCUSDT"

        # Первый вызов
        logger.info("1️⃣ Первый вызов process_realtime_signal...")
        signal1 = await self.signal_processor.process_realtime_signal(symbol)
        cache_size1 = len(self.signal_processor.prediction_cache)
        logger.info(f"Размер кэша после первого вызова: {cache_size1}")

        # Второй вызов (должен использовать кэш)
        logger.info("2️⃣ Второй вызов process_realtime_signal...")
        signal2 = await self.signal_processor.process_realtime_signal(symbol)
        cache_size2 = len(self.signal_processor.prediction_cache)
        logger.info(f"Размер кэша после второго вызова: {cache_size2}")

        # Сравнение результатов
        logger.info("📋 Сравнение результатов:")
        if signal1 and signal2:
            logger.info(
                f"Signal1: {signal1.signal_type}, confidence: {signal1.confidence}"
            )
            logger.info(
                f"Signal2: {signal2.signal_type}, confidence: {signal2.confidence}"
            )

            if (
                signal1.signal_type == signal2.signal_type
                and abs(signal1.confidence - signal2.confidence) < 0.001
            ):
                logger.info("✅ Кэш работает корректно - результаты одинаковые")
            else:
                logger.error("❌ Кэш работает некорректно - результаты разные!")
        else:
            logger.warning("⚠️ Один из сигналов None")

        # Проверяем содержимое кэша
        logger.info("\n📋 Содержимое кэша:")
        for key in self.signal_processor.prediction_cache.keys():
            logger.info(f"  Cache key: {key}")

    async def run_full_diagnostic(self):
        """Запуск полной диагностики"""
        logger.info("🚀 Запуск полной диагностики ML pipeline...")

        try:
            await self.initialize()

            # Тест 1: Передача символов
            await self.test_symbol_propagation()

            # Тест 2: Прямая генерация признаков
            await self.test_direct_feature_generation()

            # Тест 3: Поведение кэша
            await self.test_cache_behavior()

            logger.info("✅ Диагностика завершена")

        except Exception as e:
            logger.error(f"❌ Ошибка диагностики: {e}")
            raise


async def main():
    """Основная функция"""
    diagnostic = MLUniquenessDiagnostic()
    await diagnostic.run_full_diagnostic()


if __name__ == "__main__":
    asyncio.run(main())
