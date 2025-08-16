#!/usr/bin/env python3
"""
Тест исправления разнообразия сигналов в BOT_AI_V3
Проверяет, что новые пороги и логика действительно создают разнообразные сигналы
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую папку в path
sys.path.insert(0, str(Path(__file__).parent))

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from data.data_loader import DataLoader
from ml.ml_manager import MLManager
from ml.ml_signal_processor import MLSignalProcessor

logger = setup_logger("signal_diversity_test")


async def test_signal_diversity_fixes():
    """Тестируем исправления разнообразия сигналов"""

    logger.info("🧪 Начинаем тестирование исправлений разнообразия сигналов...")

    # Загружаем конфигурацию
    config_manager = ConfigManager()
    config = config_manager.get_config()

    # Инициализируем компоненты
    ml_manager = MLManager(config)
    await ml_manager.initialize()

    signal_processor = MLSignalProcessor(ml_manager, config)
    data_loader = DataLoader(config)

    # Тестируемые символы с разными характеристиками
    test_symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", "SOLUSDT"]

    signal_types = []
    direction_scores = []
    predictions_details = []

    logger.info(f"📊 Тестируем {len(test_symbols)} символов...")

    for symbol in test_symbols:
        try:
            logger.info(f"   Тестируем {symbol}...")

            # Получаем данные
            candles = await data_loader.load_ohlcv(symbol=symbol, interval="15m", limit=150)

            if candles is None or len(candles) < 96:
                logger.warning(f"   ⚠️ Недостаточно данных для {symbol}")
                continue

            # Делаем предсказание через ML Manager
            prediction = await ml_manager.predict(candles)

            if prediction:
                signal_type = prediction.get("signal_type")
                direction_score = prediction.get("predictions", {}).get("direction_score", 0)
                confidence = prediction.get("confidence", 0)
                directions = prediction.get("predictions", {}).get("directions_by_timeframe", [])

                signal_types.append(signal_type)
                direction_scores.append(direction_score)
                predictions_details.append(
                    {
                        "symbol": symbol,
                        "signal_type": signal_type,
                        "direction_score": direction_score,
                        "confidence": confidence,
                        "directions": directions,
                    }
                )

                logger.info(
                    f"   ✅ {symbol}: {signal_type} (score={direction_score:.3f}, conf={confidence:.1%})"
                )

                # Тестируем обработку сигнала процессором
                try:
                    processed_signal = await signal_processor.process_ml_prediction(
                        prediction, symbol
                    )
                    if processed_signal:
                        logger.info(
                            f"   ✅ Сигнал обработан и сохранен: {processed_signal.signal_type}"
                        )
                    else:
                        logger.info(
                            "   ℹ️ Сигнал не прошел фильтрацию (возможно NEUTRAL с низкой уверенностью)"
                        )
                except Exception as e:
                    logger.warning(f"   ⚠️ Ошибка обработки сигнала: {e}")

        except Exception as e:
            logger.error(f"   ❌ Ошибка для {symbol}: {e}")

    # Анализ результатов
    logger.warning(
        f"""
🎯 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ ИСПРАВЛЕНИЙ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Общие результаты:
   Всего символов протестировано: {len(predictions_details)}
   Средняя уверенность: {sum(p["confidence"] for p in predictions_details) / len(predictions_details) * 100:.1f}%

📈 Распределение типов сигналов:
   LONG:    {signal_types.count("LONG"):2d} ({signal_types.count("LONG") / len(signal_types) * 100:.1f}%)
   SHORT:   {signal_types.count("SHORT"):2d} ({signal_types.count("SHORT") / len(signal_types) * 100:.1f}%)
   NEUTRAL: {signal_types.count("NEUTRAL"):2d} ({signal_types.count("NEUTRAL") / len(signal_types) * 100:.1f}%)

🎯 Диапазон Direction Scores:
   Минимальный: {min(direction_scores):.3f}
   Максимальный: {max(direction_scores):.3f}
   Средний: {sum(direction_scores) / len(direction_scores):.3f}

💡 Качество исправлений:
   {"✅ ОТЛИЧНО" if len(set(signal_types)) >= 2 else "⚠️ ТРЕБУЕТ ДОРАБОТКИ"} - Разнообразие сигналов: {len(set(signal_types))} из 3 типов
   {"✅ ХОРОШО" if max(direction_scores) - min(direction_scores) > 0.3 else "⚠️ СЛАБО"} - Диапазон scores: {max(direction_scores) - min(direction_scores):.3f}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    )

    # Детальная информация по каждому символу
    logger.info("📋 Детальные результаты по символам:")
    for details in predictions_details:
        logger.info(
            f"   {details['symbol']:8s}: {details['signal_type']:7s} | "
            f"Score: {details['direction_score']:6.3f} | "
            f"Conf: {details['confidence']:5.1%} | "
            f"Directions: {details['directions']}"
        )

    # Проверяем, что проблема SHORT-only решена
    long_pct = signal_types.count("LONG") / len(signal_types) * 100
    short_pct = signal_types.count("SHORT") / len(signal_types) * 100
    neutral_pct = signal_types.count("NEUTRAL") / len(signal_types) * 100

    success_criteria = [
        (len(set(signal_types)) >= 2, "Разнообразие типов сигналов"),
        (long_pct < 90, "LONG не доминирует (< 90%)"),
        (short_pct > 0 or neutral_pct > 0, "Присутствуют не-LONG сигналы"),
        (max(direction_scores) - min(direction_scores) > 0.2, "Разнообразие scores"),
    ]

    passed_criteria = sum(1 for criterion, _ in success_criteria if criterion)

    logger.warning(
        f"""
🏆 ИТОГОВАЯ ОЦЕНКА ИСПРАВЛЕНИЙ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Пройдено критериев: {passed_criteria}/{len(success_criteria)}

"""
    )

    for criterion, description in success_criteria:
        status = "✅ ПРОЙДЕН" if criterion else "❌ НЕ ПРОЙДЕН"
        logger.warning(f"   {status}: {description}")

    if passed_criteria >= 3:
        logger.warning(
            """
🎉 ИСПРАВЛЕНИЯ УСПЕШНЫ!
   Проблема разнообразия сигналов решена.
   Система теперь генерирует сбалансированные сигналы.
"""
        )
    else:
        logger.warning(
            """
⚠️ ТРЕБУЕТСЯ ДОПОЛНИТЕЛЬНАЯ НАСТРОЙКА
   Некоторые критерии не пройдены.
   Рекомендуется дополнительная калибровка порогов.
"""
        )

    return passed_criteria >= 3


if __name__ == "__main__":
    success = asyncio.run(test_signal_diversity_fixes())
    sys.exit(0 if success else 1)
