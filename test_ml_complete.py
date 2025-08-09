#!/usr/bin/env python3

import asyncio
import time
from datetime import datetime

import numpy as np
import pandas as pd

from core.logger import setup_logger
from ml.ml_manager import MLManager

logger = setup_logger("test_ml_complete")


async def test_ml_manager():
    """Полный тест ML Manager"""
    try:
        # Создаем тестовые данные
        logger.info("Создаем тестовые данные...")
        dates = pd.date_range(end=datetime.now(), periods=200, freq="15min")

        # Генерируем восходящий тренд
        base_price = 45000
        trend = np.linspace(0, 500, 200)

        data = pd.DataFrame(
            {
                "datetime": dates,
                "open": base_price + trend + np.random.normal(0, 20, 200),
                "high": base_price + trend + np.random.uniform(20, 50, 200),
                "low": base_price + trend - np.random.uniform(20, 50, 200),
                "close": base_price + trend + np.random.normal(0, 30, 200),
                "volume": np.random.uniform(100, 1000, 200),
                "symbol": "BTCUSDT",
            }
        )

        logger.info(f"Данные созданы: {data.shape}")
        logger.info(f"Период: {data['datetime'].min()} - {data['datetime'].max()}")

        # Создаем ML Manager
        config = {"ml": {"model": {"device": "cpu"}}}  # Принудительно CPU
        ml_manager = MLManager(config)

        # Инициализация
        logger.info("Инициализируем ML Manager...")
        start_time = time.time()
        await ml_manager.initialize()
        logger.info(f"Инициализация заняла {time.time() - start_time:.2f} сек")

        # Предсказание
        logger.info("Делаем предсказание...")
        start_time = time.time()
        prediction = await ml_manager.predict(data)
        logger.info(f"Предсказание заняло {time.time() - start_time:.2f} сек")

        # Результаты
        logger.info("=" * 60)
        logger.info("РЕЗУЛЬТАТЫ ML ПРЕДСКАЗАНИЯ:")
        logger.info("=" * 60)
        logger.info(f"📊 Сигнал: {prediction['signal_type']}")
        logger.info(f"💪 Сила сигнала: {prediction['signal_strength']:.3f}")
        logger.info(f"🎯 Уверенность: {prediction['confidence']:.3f}")
        logger.info(f"📈 Вероятность успеха: {prediction['success_probability']:.1%}")
        logger.info(f"⚠️  Уровень риска: {prediction['risk_level']}")

        if prediction["signal_type"] != "NEUTRAL":
            if prediction["stop_loss"]:
                logger.info(f"🛑 Stop Loss: {prediction['stop_loss']:.2f}")
            if prediction["take_profit"]:
                logger.info(f"✅ Take Profit: {prediction['take_profit']:.2f}")

        # Детали
        logger.info("\n📋 Детальные предсказания:")
        pred_details = prediction["predictions"]
        logger.info(f"   15мин доходность: {pred_details['returns_15m']:.3f}")
        logger.info(f"   1час доходность: {pred_details['returns_1h']:.3f}")
        logger.info(f"   4час доходность: {pred_details['returns_4h']:.3f}")
        logger.info(f"   12час доходность: {pred_details['returns_12h']:.3f}")

        # Проверка разнообразия
        raw_dirs = pred_details.get("raw_directions", [])
        if raw_dirs:
            unique_vals = len(set([round(d, 1) for d in raw_dirs]))
            logger.info("\n🔍 Анализ предсказаний:")
            logger.info(f"   Уникальных значений: {unique_vals} из {len(raw_dirs)}")
            logger.info(f"   Raw directions: {[f'{v:.2f}' for v in raw_dirs]}")

            # Проверяем монотонность
            if unique_vals == 1:
                logger.warning("⚠️  ВНИМАНИЕ: Все предсказания одинаковые!")
            else:
                logger.info("✅ Предсказания разнообразные")

        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(test_ml_manager())
