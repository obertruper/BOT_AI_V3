#!/usr/bin/env python3
"""
Тест: проверяет, реагирует ли модель на разные входные данные
"""

import asyncio

import numpy as np

from core.logger import setup_logger
from ml.ml_manager import MLManager

logger = setup_logger("model_responsiveness_test")


async def test_model_responsiveness():
    """
    Проверяет, что модель дает РАЗНЫЕ предсказания для РАЗНЫХ входов
    """

    logger.info("=" * 60)
    logger.info("🔬 ТЕСТ ОТЗЫВЧИВОСТИ МОДЕЛИ")
    logger.info("=" * 60)

    # Инициализация
    config = {"ml": {"model": {"device": "cpu"}, "model_directory": "models/saved"}}

    ml_manager = MLManager(config)
    await ml_manager.initialize()

    # Тест 1: Все нули
    logger.info("\n📊 Тест 1: Входные данные = НУЛИ")
    features_zeros = np.zeros((96, 240))
    pred_zeros = await ml_manager.predict(features_zeros)
    signal_zeros = pred_zeros.get("signal_type")
    conf_zeros = pred_zeros.get("confidence", 0)
    raw_zeros = pred_zeros.get("predictions", {}).get("returns_15m", 0)
    logger.info(
        f"  Результат: {signal_zeros}, confidence: {conf_zeros:.3f}, return_15m: {raw_zeros:.6f}"
    )

    # Тест 2: Все единицы
    logger.info("\n📊 Тест 2: Входные данные = ЕДИНИЦЫ")
    features_ones = np.ones((96, 240))
    pred_ones = await ml_manager.predict(features_ones)
    signal_ones = pred_ones.get("signal_type")
    conf_ones = pred_ones.get("confidence", 0)
    raw_ones = pred_ones.get("predictions", {}).get("returns_15m", 0)
    logger.info(
        f"  Результат: {signal_ones}, confidence: {conf_ones:.3f}, return_15m: {raw_ones:.6f}"
    )

    # Тест 3: Случайные данные (seed=42)
    logger.info("\n📊 Тест 3: Входные данные = RANDOM (seed=42)")
    np.random.seed(42)
    features_random1 = np.random.randn(96, 240)
    pred_random1 = await ml_manager.predict(features_random1)
    signal_random1 = pred_random1.get("signal_type")
    conf_random1 = pred_random1.get("confidence", 0)
    raw_random1 = pred_random1.get("predictions", {}).get("returns_15m", 0)
    logger.info(
        f"  Результат: {signal_random1}, confidence: {conf_random1:.3f}, return_15m: {raw_random1:.6f}"
    )

    # Тест 4: Другие случайные данные (seed=123)
    logger.info("\n📊 Тест 4: Входные данные = RANDOM (seed=123)")
    np.random.seed(123)
    features_random2 = np.random.randn(96, 240)
    pred_random2 = await ml_manager.predict(features_random2)
    signal_random2 = pred_random2.get("signal_type")
    conf_random2 = pred_random2.get("confidence", 0)
    raw_random2 = pred_random2.get("predictions", {}).get("returns_15m", 0)
    logger.info(
        f"  Результат: {signal_random2}, confidence: {conf_random2:.3f}, return_15m: {raw_random2:.6f}"
    )

    # Тест 5: Сильный восходящий тренд
    logger.info("\n📊 Тест 5: Входные данные = ВОСХОДЯЩИЙ ТРЕНД")
    features_up = np.random.randn(96, 240) * 0.1
    trend_up = np.linspace(0, 2, 96).reshape(-1, 1)
    features_up[:, :50] += trend_up  # Добавляем тренд в первые 50 признаков
    pred_up = await ml_manager.predict(features_up)
    signal_up = pred_up.get("signal_type")
    conf_up = pred_up.get("confidence", 0)
    raw_up = pred_up.get("predictions", {}).get("returns_15m", 0)
    logger.info(f"  Результат: {signal_up}, confidence: {conf_up:.3f}, return_15m: {raw_up:.6f}")

    # Тест 6: Сильный нисходящий тренд
    logger.info("\n📊 Тест 6: Входные данные = НИСХОДЯЩИЙ ТРЕНД")
    features_down = np.random.randn(96, 240) * 0.1
    trend_down = np.linspace(0, -2, 96).reshape(-1, 1)
    features_down[:, :50] += trend_down  # Добавляем тренд в первые 50 признаков
    pred_down = await ml_manager.predict(features_down)
    signal_down = pred_down.get("signal_type")
    conf_down = pred_down.get("confidence", 0)
    raw_down = pred_down.get("predictions", {}).get("returns_15m", 0)
    logger.info(
        f"  Результат: {signal_down}, confidence: {conf_down:.3f}, return_15m: {raw_down:.6f}"
    )

    # АНАЛИЗ РЕЗУЛЬТАТОВ
    logger.info("\n" + "=" * 60)
    logger.info("📊 АНАЛИЗ ОТЗЫВЧИВОСТИ")
    logger.info("=" * 60)

    # Проверяем уникальность предсказаний
    all_signals = [
        signal_zeros,
        signal_ones,
        signal_random1,
        signal_random2,
        signal_up,
        signal_down,
    ]
    all_confidences = [
        conf_zeros,
        conf_ones,
        conf_random1,
        conf_random2,
        conf_up,
        conf_down,
    ]
    all_returns = [raw_zeros, raw_ones, raw_random1, raw_random2, raw_up, raw_down]

    unique_signals = len(set(all_signals))
    unique_confidences = len(set(all_confidences))
    confidence_variance = np.var(all_confidences)
    returns_variance = np.var(all_returns)

    logger.info(f"Уникальных типов сигналов: {unique_signals} из 6")
    logger.info(f"Уникальных значений confidence: {unique_confidences} из 6")
    logger.info(f"Вариация confidence: {confidence_variance:.6f}")
    logger.info(f"Вариация returns: {returns_variance:.9f}")

    # Оценка
    if unique_signals == 1 and confidence_variance < 0.001:
        logger.critical("❌ МОДЕЛЬ НЕ РАБОТАЕТ! Возвращает константные предсказания!")
        logger.critical("   Проблема с нормализацией или загрузкой весов")
    elif unique_signals <= 2:
        logger.warning("⚠️ Модель слабо реагирует на входные данные")
        logger.warning("   Возможна проблема с обучением или нормализацией")
    else:
        logger.info("✅ Модель реагирует на разные входные данные")

        # Проверяем логику
        if signal_up == "LONG" and signal_down == "SHORT":
            logger.info("✅ Логика предсказаний корректна (тренд вверх → LONG, тренд вниз → SHORT)")
        elif signal_up == "SHORT" and signal_down == "LONG":
            logger.warning("⚠️ Логика инвертирована (тренд вверх → SHORT, тренд вниз → LONG)")
        else:
            logger.warning("⚠️ Модель не различает тренды")

    logger.info("\n✅ Тест завершен")


if __name__ == "__main__":
    asyncio.run(test_model_responsiveness())
