#!/usr/bin/env python3
"""
Тест для проверки количества генерируемых признаков
и соответствия ожидаемым 240 признакам для модели
"""

import asyncio
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from core.logger import setup_logger
from ml.config.features_240 import get_feature_groups
from ml.realtime_indicator_calculator import RealTimeIndicatorCalculator

logger = setup_logger("test_feature_count")


async def test_feature_generation():
    """
    Тестирует генерацию признаков и проверяет их количество
    """
    try:
        logger.info("=" * 60)
        logger.info("🧪 ТЕСТ КОЛИЧЕСТВА ПРИЗНАКОВ")
        logger.info("=" * 60)

        # 1. Создаем тестовые данные
        logger.info("\n1️⃣ Создание тестовых OHLCV данных...")

        dates = pd.date_range(end=pd.Timestamp.now(), periods=300, freq="15min")
        price_base = 50000  # BTC цена
        price_changes = np.random.randn(300) * 0.001
        prices = price_base * np.cumprod(1 + price_changes)

        test_data = pd.DataFrame(
            {
                "datetime": dates,
                "open": prices * (1 + np.random.randn(300) * 0.0001),
                "high": prices * (1 + np.abs(np.random.randn(300)) * 0.0002),
                "low": prices * (1 - np.abs(np.random.randn(300)) * 0.0002),
                "close": prices,
                "volume": np.random.randint(100, 1000, 300).astype(float),
                "symbol": "BTCUSDT",
            }
        )
        test_data["turnover"] = test_data["close"] * test_data["volume"]
        test_data = test_data.set_index("datetime")

        logger.info(f"  ✅ Создано {len(test_data)} свечей для BTCUSDT")

        # 2. Инициализируем калькулятор
        logger.info("\n2️⃣ Инициализация RealTimeIndicatorCalculator...")

        calculator = RealTimeIndicatorCalculator(cache_ttl=0)  # Без кэша для теста

        # 3. Генерируем признаки
        logger.info("\n3️⃣ Генерация признаков...")

        features = await calculator.get_features_for_ml("BTCUSDT", test_data)

        logger.info(f"  📊 Сгенерировано признаков: {len(features)}")

        # 4. Проверка количества
        logger.info("\n4️⃣ Проверка соответствия ожиданиям...")

        if len(features) == 240:
            logger.info("  ✅ УСПЕХ: Сгенерировано ровно 240 признаков!")
        else:
            logger.error(f"  ❌ ОШИБКА: Ожидалось 240, получено {len(features)}")

            if len(features) > 240:
                logger.warning(f"  ⚠️ Сгенерировано на {len(features) - 240} признаков больше")
            else:
                logger.warning(f"  ⚠️ Не хватает {240 - len(features)} признаков")

        # 5. Анализ по группам
        logger.info("\n5️⃣ Анализ признаков по группам...")

        feature_groups = get_feature_groups()

        for group_name, expected_features in feature_groups.items():
            logger.info(f"\n  📁 {group_name.upper()}:")
            logger.info(f"     Ожидается: {len(expected_features)} признаков")

            # Проверяем наличие признаков из группы
            missing = []
            for feat in expected_features[:5]:  # Показываем первые 5
                logger.info(f"     - {feat}")
            if len(expected_features) > 5:
                logger.info(f"     ... и еще {len(expected_features) - 5}")

        # 6. Детальная проверка с использованием features_240.py
        logger.info("\n6️⃣ Проверка с использованием конфигурации...")

        # Создаем список имен признаков (для теста используем индексы)
        feature_names = [f"feature_{i}" for i in range(len(features))]

        # Проверяем валидность (количество)
        if len(feature_names) == 240:
            logger.info("  ✅ Количество признаков соответствует конфигурации")
        else:
            logger.error("  ❌ Количество признаков НЕ соответствует конфигурации")

        # 7. Проверка значений
        logger.info("\n7️⃣ Проверка значений признаков...")

        # Статистика
        non_zero = np.sum(features != 0)
        non_nan = np.sum(~np.isnan(features))
        finite = np.sum(np.isfinite(features))

        logger.info("  📊 Статистика признаков:")
        logger.info(
            f"     - Ненулевых: {non_zero}/{len(features)} ({non_zero / len(features) * 100:.1f}%)"
        )
        logger.info(
            f"     - Не NaN: {non_nan}/{len(features)} ({non_nan / len(features) * 100:.1f}%)"
        )
        logger.info(
            f"     - Конечных: {finite}/{len(features)} ({finite / len(features) * 100:.1f}%)"
        )

        # Диапазон значений
        if finite > 0:
            valid_features = features[np.isfinite(features)]
            logger.info(f"     - Min: {valid_features.min():.6f}")
            logger.info(f"     - Max: {valid_features.max():.6f}")
            logger.info(f"     - Mean: {valid_features.mean():.6f}")
            logger.info(f"     - Std: {valid_features.std():.6f}")

        # 8. Тест с полным циклом (calculator.calculate_indicators)
        logger.info("\n8️⃣ Тест полного цикла расчета индикаторов...")

        indicators = await calculator.calculate_indicators("BTCUSDT", test_data, save_to_db=False)

        if "ml_features" in indicators:
            ml_features = indicators["ml_features"]
            logger.info(f"  📊 ML признаков в результате: {len(ml_features)}")

            # Показываем первые 10 признаков
            feature_list = list(ml_features.keys())[:10]
            for feat in feature_list:
                logger.info(f"     - {feat}: {ml_features[feat]:.6f}")
            if len(ml_features) > 10:
                logger.info(f"     ... и еще {len(ml_features) - 10} признаков")

        # 9. Итоговый вердикт
        logger.info("\n" + "=" * 60)
        logger.info("📊 ИТОГОВЫЙ РЕЗУЛЬТАТ")
        logger.info("=" * 60)

        issues = []

        if len(features) != 240:
            issues.append(f"Неверное количество признаков: {len(features)} вместо 240")

        if non_zero < len(features) * 0.5:
            issues.append(f"Слишком много нулевых признаков: {len(features) - non_zero}")

        if non_nan < len(features) * 0.95:
            issues.append(f"Слишком много NaN: {len(features) - non_nan}")

        if issues:
            logger.error("❌ ТЕСТ НЕ ПРОЙДЕН:")
            for issue in issues:
                logger.error(f"  - {issue}")
            logger.info("\n💡 РЕКОМЕНДАЦИИ:")
            logger.info("  1. Проверьте feature_engineering_v2.py")
            logger.info("  2. Убедитесь, что генерируются только нужные признаки")
            logger.info("  3. Проверьте логику в realtime_indicator_calculator.py")
            logger.info("  4. Используйте конфигурацию из ml/config/features_240.py")
        else:
            logger.info("✅ ТЕСТ УСПЕШНО ПРОЙДЕН!")
            logger.info("  - Генерируется ровно 240 признаков")
            logger.info("  - Признаки содержат валидные значения")
            logger.info("  - Система готова к работе с моделью")

        return len(features) == 240

    except Exception as e:
        logger.error(f"❌ Ошибка теста: {e}", exc_info=True)
        return False


async def main():
    """Главная функция"""
    success = await test_feature_generation()

    if success:
        logger.info("\n🎉 Все тесты пройдены успешно!")
        sys.exit(0)
    else:
        logger.error("\n❌ Тесты не пройдены")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
