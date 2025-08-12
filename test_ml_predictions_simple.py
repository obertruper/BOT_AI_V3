#!/usr/bin/env python3
"""
Простой тест ML предсказаний для проверки разнообразия сигналов
"""

import asyncio
import sys
from pathlib import Path

import numpy as np

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from core.logger import setup_logger
from ml.ml_manager import MLManager

logger = setup_logger("test_ml_simple")


async def test_predictions():
    """Тестирует предсказания модели с разными входными данными"""

    logger.info("🚀 Начинаем простой тест ML предсказаний...")

    # Создаем ML Manager с минимальной конфигурацией
    config = {
        "ml": {
            "model": {"device": "cpu"},  # Используем CPU для теста
            "model_directory": "models/saved",
        }
    }

    ml_manager = MLManager(config)
    await ml_manager.initialize()

    signal_counts = {"LONG": 0, "SHORT": 0, "NEUTRAL": 0}

    # Тестируем с разными наборами данных
    for i in range(10):
        logger.info(f"\n📊 Тест #{i + 1}")

        # Создаем случайные признаки с разными паттернами
        np.random.seed(i * 42)

        # 96 временных точек, 240 признаков
        features = np.random.randn(96, 240)

        # Добавляем разные паттерны в данные
        if i % 3 == 0:
            # Восходящий тренд
            features[:, 0:10] += np.linspace(0, 1, 96).reshape(-1, 1)
        elif i % 3 == 1:
            # Нисходящий тренд
            features[:, 0:10] -= np.linspace(0, 1, 96).reshape(-1, 1)
        else:
            # Боковое движение
            features[:, 0:10] += (
                np.sin(np.linspace(0, 4 * np.pi, 96)).reshape(-1, 1) * 0.5
            )

        try:
            # Получаем предсказание
            prediction = await ml_manager.predict(features)

            signal_type = prediction.get("signal_type", "UNKNOWN")
            confidence = prediction.get("confidence", 0)
            strength = prediction.get("signal_strength", 0)

            logger.info(
                f"   Результат: {signal_type} "
                f"(confidence: {confidence:.2f}, strength: {strength:.2f})"
            )

            # Подсчитываем
            if signal_type in signal_counts:
                signal_counts[signal_type] += 1

        except Exception as e:
            logger.error(f"   Ошибка: {e}")

    # Анализ результатов
    logger.info("\n" + "=" * 60)
    logger.info("📊 РЕЗУЛЬТАТЫ ТЕСТА")
    logger.info("=" * 60)

    total = sum(signal_counts.values())
    if total > 0:
        for signal_type, count in signal_counts.items():
            pct = (count / total) * 100
            logger.info(f"{signal_type:8}: {count:2d} ({pct:5.1f}%)")

        # Проверка баланса
        long_pct = (signal_counts["LONG"] / total) * 100
        short_pct = (signal_counts["SHORT"] / total) * 100

        logger.info("-" * 30)
        if signal_counts["LONG"] == 0:
            logger.error("❌ ПРОБЛЕМА: Нет LONG сигналов!")
        elif signal_counts["SHORT"] == 0:
            logger.error("❌ ПРОБЛЕМА: Нет SHORT сигналов!")
        elif long_pct > 80:
            logger.warning("⚠️ Дисбаланс: слишком много LONG")
        elif short_pct > 80:
            logger.warning("⚠️ Дисбаланс: слишком много SHORT")
        else:
            logger.info("✅ Сигналы диверсифицированы!")

            # Проверяем что исправление работает
            if 20 <= long_pct <= 80 and 20 <= short_pct <= 80:
                logger.info("🎯 УСПЕХ: Исправление работает правильно!")
                logger.info(f"   Баланс LONG/SHORT: {long_pct:.0f}%/{short_pct:.0f}%")

    logger.info("\n✅ Тест завершен")


if __name__ == "__main__":
    asyncio.run(test_predictions())
