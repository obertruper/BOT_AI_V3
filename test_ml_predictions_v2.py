#!/usr/bin/env python3
"""
Тест ML предсказаний с новой feature engineering из LLM TRANSFORM
"""

import asyncio
import os
import sys

import pandas as pd

# Добавляем проект в path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool
from ml.ml_manager import MLManager

logger = setup_logger("test_ml_v2")


async def test_ml_predictions():
    """Тестирование ML предсказаний с реальными данными"""
    try:
        # Загружаем последние данные
        logger.info("Загружаем данные из БД...")
        query = """
        SELECT
            datetime,
            open, high, low, close, volume,
            'BTCUSDT' as symbol
        FROM raw_market_data
        WHERE symbol = 'BTCUSDT'
        ORDER BY datetime DESC
        LIMIT 200
        """

        # Используем существующий пул из AsyncPGPool
        rows = await AsyncPGPool.fetch(query)

        if not rows:
            logger.error("Нет данных в БД")
            return

        # Преобразуем в DataFrame
        data = pd.DataFrame([dict(row) for row in rows])
        data["datetime"] = pd.to_datetime(data["datetime"])

        # Преобразуем Decimal в float
        for col in ["open", "high", "low", "close", "volume"]:
            data[col] = data[col].astype(float)

        data["turnover"] = data["volume"] * data["close"]

        # Сортируем по времени (от старых к новым)
        data = data.sort_values("datetime").reset_index(drop=True)

        logger.info(f"Загружено {len(data)} свечей")
        logger.info(f"Период: {data['datetime'].min()} - {data['datetime'].max()}")
        logger.info(f"Последняя цена: {data['close'].iloc[-1]:.2f}")

        # Инициализируем ML Manager
        logger.info("Инициализируем ML Manager...")
        config = {"ml": {"model": {"device": "auto"}}}

        ml_manager = MLManager(config)
        await ml_manager.initialize()

        # Делаем предсказание
        logger.info("Делаем ML предсказание...")
        prediction = await ml_manager.predict(data)

        # Выводим результаты
        logger.info("=" * 50)
        logger.info("РЕЗУЛЬТАТЫ ML ПРЕДСКАЗАНИЯ (v2):")
        logger.info("=" * 50)
        logger.info(f"Сигнал: {prediction['signal_type']}")
        logger.info(f"Сила сигнала: {prediction['signal_strength']:.3f}")
        logger.info(f"Уверенность: {prediction['confidence']:.3f}")
        logger.info(f"Вероятность успеха: {prediction['success_probability']:.1%}")
        logger.info(f"Уровень риска: {prediction['risk_level']}")

        if prediction["stop_loss"]:
            logger.info(f"Stop Loss: {prediction['stop_loss']:.2f}")
        if prediction["take_profit"]:
            logger.info(f"Take Profit: {prediction['take_profit']:.2f}")

        logger.info("\nДетали предсказаний:")
        for key, value in prediction["predictions"].items():
            if isinstance(value, list):
                logger.info(f"  {key}: {[f'{v:.3f}' for v in value]}")
            else:
                logger.info(f"  {key}: {value:.3f}")

        # Проверяем разнообразие предсказаний
        raw_dirs = prediction["predictions"].get("raw_directions", [])
        if raw_dirs:
            unique_dirs = len(set([round(d, 2) for d in raw_dirs]))
            logger.info(
                f"\nРазнообразие raw_directions: {unique_dirs} уникальных из {len(raw_dirs)}"
            )

        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(test_ml_predictions())
