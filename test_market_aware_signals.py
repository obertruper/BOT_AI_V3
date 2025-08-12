#!/usr/bin/env python3
"""
Тест сигналов с учетом рыночного контекста
Проверяет адекватность сигналов текущему состоянию рынка
"""

import asyncio
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from core.logger import setup_logger
from ml.ml_manager import MLManager

logger = setup_logger("market_aware_test")


async def simulate_market_conditions():
    """
    Симулирует разные рыночные условия и проверяет адекватность сигналов
    """

    # Инициализация ML Manager
    config = {"ml": {"model": {"device": "cpu"}, "model_directory": "models/saved"}}

    ml_manager = MLManager(config)
    await ml_manager.initialize()

    logger.info("=" * 60)
    logger.info("🔍 ТЕСТ АДЕКВАТНОСТИ СИГНАЛОВ РЫНОЧНЫМ УСЛОВИЯМ")
    logger.info("=" * 60)

    # Тестовые сценарии
    scenarios = [
        {
            "name": "🐂 СИЛЬНЫЙ БЫЧИЙ ТРЕНД",
            "trend": "up",
            "volatility": 0.02,
            "expected_long_ratio": (0.5, 0.9),  # Ожидаем 50-90% LONG
            "expected_short_ratio": (0.0, 0.3),  # Ожидаем 0-30% SHORT
        },
        {
            "name": "🐻 СИЛЬНЫЙ МЕДВЕЖИЙ ТРЕНД",
            "trend": "down",
            "volatility": 0.03,
            "expected_long_ratio": (0.0, 0.3),  # Ожидаем 0-30% LONG
            "expected_short_ratio": (0.5, 0.9),  # Ожидаем 50-90% SHORT
        },
        {
            "name": "↔️ БОКОВОЕ ДВИЖЕНИЕ",
            "trend": "sideways",
            "volatility": 0.01,
            "expected_long_ratio": (0.2, 0.5),  # Ожидаем 20-50% LONG
            "expected_short_ratio": (0.2, 0.5),  # Ожидаем 20-50% SHORT
        },
    ]

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]

    for scenario in scenarios:
        logger.info(f"\n{'=' * 50}")
        logger.info(f"📊 Сценарий: {scenario['name']}")
        logger.info(f"{'=' * 50}")

        signal_counts = {"LONG": 0, "SHORT": 0, "NEUTRAL": 0}

        # Генерируем данные для каждого символа с учетом сценария
        for symbol in symbols:
            # Создаем данные с нужным трендом
            features = generate_market_data(
                trend=scenario["trend"],
                volatility=scenario["volatility"],
                symbol=symbol,
            )

            try:
                # Получаем предсказание
                prediction = await ml_manager.predict(features)
                signal_type = prediction.get("signal_type", "UNKNOWN")
                confidence = prediction.get("confidence", 0)

                if signal_type in signal_counts:
                    signal_counts[signal_type] += 1

                # Детальное логирование для анализа
                directions = prediction.get("predictions", {}).get(
                    "directions_by_timeframe", []
                )
                logger.debug(
                    f"  {symbol}: {signal_type} (conf: {confidence:.2f}) "
                    f"directions: {directions}"
                )

            except Exception as e:
                logger.error(f"  Ошибка для {symbol}: {e}")

        # Анализ результатов
        total = sum(signal_counts.values())
        if total > 0:
            long_ratio = signal_counts["LONG"] / total
            short_ratio = signal_counts["SHORT"] / total
            neutral_ratio = signal_counts["NEUTRAL"] / total

            logger.info("\n📈 Результаты:")
            logger.info(f"  LONG:    {signal_counts['LONG']} ({long_ratio:.1%})")
            logger.info(f"  SHORT:   {signal_counts['SHORT']} ({short_ratio:.1%})")
            logger.info(f"  NEUTRAL: {signal_counts['NEUTRAL']} ({neutral_ratio:.1%})")

            # Проверка адекватности
            is_adequate = True
            issues = []

            # Проверяем LONG
            if not (
                scenario["expected_long_ratio"][0]
                <= long_ratio
                <= scenario["expected_long_ratio"][1]
            ):
                is_adequate = False
                issues.append(
                    f"LONG: {long_ratio:.1%} вне ожидаемого диапазона "
                    f"{scenario['expected_long_ratio'][0]:.0%}-{scenario['expected_long_ratio'][1]:.0%}"
                )

            # Проверяем SHORT
            if not (
                scenario["expected_short_ratio"][0]
                <= short_ratio
                <= scenario["expected_short_ratio"][1]
            ):
                is_adequate = False
                issues.append(
                    f"SHORT: {short_ratio:.1%} вне ожидаемого диапазона "
                    f"{scenario['expected_short_ratio'][0]:.0%}-{scenario['expected_short_ratio'][1]:.0%}"
                )

            if is_adequate:
                logger.info("\n✅ АДЕКВАТНО: Сигналы соответствуют рыночным условиям")
            else:
                logger.warning("\n⚠️ ПРОБЛЕМА: Сигналы НЕ соответствуют рынку")
                for issue in issues:
                    logger.warning(f"  - {issue}")

    logger.info("\n" + "=" * 60)
    logger.info("✅ Тест завершен")


def generate_market_data(trend="up", volatility=0.02, symbol="BTCUSDT"):
    """
    Генерирует синтетические рыночные данные с заданным трендом

    Args:
        trend: 'up', 'down', или 'sideways'
        volatility: уровень волатильности
        symbol: торговый символ

    Returns:
        numpy array с признаками (96, 240)
    """
    np.random.seed(hash(symbol) % 10000)

    # Базовые признаки
    features = np.random.randn(96, 240) * volatility

    # Добавляем тренд в ключевые признаки (первые 20)
    if trend == "up":
        # Восходящий тренд
        trend_component = np.linspace(0, 1, 96).reshape(-1, 1)
        features[:, :20] += trend_component * 0.5
        # Увеличиваем значения RSI-подобных индикаторов
        features[:, 20:30] += 0.3
    elif trend == "down":
        # Нисходящий тренд
        trend_component = np.linspace(0, -1, 96).reshape(-1, 1)
        features[:, :20] += trend_component * 0.5
        # Уменьшаем значения RSI-подобных индикаторов
        features[:, 20:30] -= 0.3
    else:  # sideways
        # Боковое движение - синусоида
        sideways_component = np.sin(np.linspace(0, 4 * np.pi, 96)).reshape(-1, 1)
        features[:, :20] += sideways_component * 0.2
        # RSI около 50
        features[:, 20:30] *= 0.5

    # Добавляем шум для реалистичности
    features += np.random.randn(96, 240) * volatility * 0.5

    return features


if __name__ == "__main__":
    asyncio.run(simulate_market_conditions())
