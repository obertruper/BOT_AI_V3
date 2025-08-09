#!/usr/bin/env python3
"""
Финальный тест исправленной ML системы
"""

import asyncio
import sys

sys.path.append("/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3")

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from data.data_loader import DataLoader
from ml.ml_manager import MLManager

logger = setup_logger("test_final_ml_fix")


async def test_ml_uniqueness():
    """Тестирует уникальность ML предсказаний"""

    logger.info("🧪 ФИНАЛЬНЫЙ ТЕСТ ИСПРАВЛЕННОЙ ML СИСТЕМЫ")
    logger.info("=" * 50)

    data_loader = DataLoader()
    config_manager = ConfigManager()
    ml_manager = MLManager(config_manager.get_ml_config())

    try:
        await data_loader.initialize()
        await ml_manager.initialize()

        test_symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
        predictions = []

        logger.info("Генерируем предсказания для разных символов...")

        for symbol in test_symbols:
            logger.info(f"\n📊 Тестирование {symbol}:")

            # Загружаем данные
            data = await data_loader.get_data_for_ml(symbol, limit=100)

            if data is None or len(data) < 96:
                logger.warning(f"Недостаточно данных для {symbol}")
                continue

            # Получаем предсказание
            prediction = await ml_manager.predict(data)
            predictions.append((symbol, prediction))

            # Выводим детальную информацию
            logger.info(f"  Тип сигнала: {prediction.get('signal_type')}")
            logger.info(f"  Сила сигнала: {prediction.get('signal_strength', 0):.6f}")
            logger.info(
                f"  Направление score: {prediction.get('predictions', {}).get('direction_score', 0):.6f}"
            )
            logger.info("  Future returns:")
            returns = prediction.get("predictions", {})
            logger.info(f"    15m: {returns.get('returns_15m', 0):.6f}")
            logger.info(f"    1h:  {returns.get('returns_1h', 0):.6f}")
            logger.info(f"    4h:  {returns.get('returns_4h', 0):.6f}")
            logger.info(f"    12h: {returns.get('returns_12h', 0):.6f}")

        # Анализ результатов
        logger.info("\n📈 АНАЛИЗ РЕЗУЛЬТАТОВ:")

        if len(predictions) < 2:
            logger.error("❌ Недостаточно предсказаний для анализа")
            return False

        # Проверяем различия
        signal_types = [p[1].get("signal_type") for p in predictions]
        signal_strengths = [p[1].get("signal_strength", 0) for p in predictions]
        direction_scores = [
            p[1].get("predictions", {}).get("direction_score", 0) for p in predictions
        ]

        unique_types = len(set(signal_types))
        strength_std = max(signal_strengths) - min(signal_strengths)
        direction_std = max(direction_scores) - min(direction_scores)

        logger.info(f"Уникальных типов сигналов: {unique_types}/{len(predictions)}")
        logger.info(f"Разброс силы сигналов: {strength_std:.6f}")
        logger.info(f"Разброс direction scores: {direction_std:.6f}")

        # Выводы
        success = True
        if unique_types == 1:
            logger.warning("⚠️ Все символы получают одинаковый тип сигнала")
        else:
            logger.info("✅ Типы сигналов различаются между символами")

        if strength_std < 0.001:
            logger.warning("⚠️ Сила сигналов практически идентична")
        else:
            logger.info("✅ Сила сигналов различается между символами")

        if direction_std < 0.001:
            logger.warning("⚠️ Direction scores практически идентичны")
            success = False
        else:
            logger.info("✅ Direction scores различаются между символами")

        return success

    except Exception as e:
        logger.error(f"❌ Ошибка тестирования: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        await data_loader.cleanup()


if __name__ == "__main__":
    success = asyncio.run(test_ml_uniqueness())
    if success:
        print("\n🎉 УСПЕХ! ML система исправлена и генерирует уникальные предсказания")
    else:
        print("\n⚠️ Остаются проблемы с уникальностью предсказаний")
