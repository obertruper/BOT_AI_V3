#!/usr/bin/env python3
"""
Тест уникальности ML предсказаний
Проверяет что модель генерирует разные предсказания для разных символов
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()


async def test_ml_uniqueness():
    """Тестируем уникальность предсказаний"""

    print("=" * 60)
    print("🔍 ТЕСТ УНИКАЛЬНОСТИ ML ПРЕДСКАЗАНИЙ")
    print("=" * 60)

    # Инициализация
    from core.config.config_manager import ConfigManager
    from ml.ml_manager import MLManager
    from ml.ml_signal_processor import MLSignalProcessor

    config_manager = ConfigManager("config/system.yaml")
    await config_manager.initialize()

    config = config_manager.get_config()

    # Создаем ML manager
    ml_manager = MLManager(config)
    await ml_manager.initialize()  # Инициализируем модель!

    # Создаем processor с правильными параметрами
    processor = MLSignalProcessor(config_manager, config)
    processor.ml_manager = ml_manager  # Устанавливаем ml_manager

    # Тестируем несколько символов
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
    predictions = {}
    features_hashes = {}

    print("\n📊 Генерация предсказаний для разных символов:")
    print("-" * 50)

    for symbol in symbols:
        try:
            # Получаем данные
            ohlcv_df = await processor._fetch_latest_ohlcv(symbol, "bybit", 7200)

            if ohlcv_df is None or len(ohlcv_df) < 96:
                print(f"❌ {symbol}: недостаточно данных")
                continue

            # Рассчитываем признаки
            (
                features_array,
                metadata,
            ) = await processor.indicator_calculator.prepare_ml_input(
                symbol=symbol, ohlcv_df=ohlcv_df, lookback=96
            )

            # Сохраняем хеш признаков для проверки уникальности
            features_hash = hash(features_array.tobytes())
            features_hashes[symbol] = features_hash

            # Получаем предсказание
            prediction = await processor.ml_manager.predict(features_array)
            predictions[symbol] = prediction

            # Выводим результат
            print(f"\n✅ {symbol}:")
            print(f"   • Features shape: {features_array.shape}")
            print(f"   • Features hash: {features_hash}")
            print(f"   • Signal type: {prediction.get('signal_type')}")
            print(f"   • Confidence: {prediction.get('confidence', 0):.4f}")
            print(
                f"   • Returns 15m: {prediction.get('predictions', {}).get('returns_15m', 0):.6f}"
            )
            print(f"   • Returns 1h: {prediction.get('predictions', {}).get('returns_1h', 0):.6f}")

            # Проверяем первые несколько значений features
            print(f"   • First 5 features: {features_array[0, -1, :5]}")
            print(f"   • Last close price: {ohlcv_df['close'].iloc[-1]:.2f}")

        except Exception as e:
            print(f"❌ {symbol}: ошибка - {e}")

    # Анализ уникальности
    print("\n" + "=" * 60)
    print("📈 АНАЛИЗ УНИКАЛЬНОСТИ:")
    print("-" * 50)

    # Проверка уникальности хешей признаков
    unique_hashes = len(set(features_hashes.values())) if features_hashes else 0
    print("\n1. Уникальность входных данных:")
    print(f"   • Всего символов: {len(features_hashes)}")
    print(f"   • Уникальных наборов признаков: {unique_hashes}")

    if len(features_hashes) > 0:
        if unique_hashes == len(features_hashes):
            print("   ✅ Все входные данные уникальны")
        else:
            print("   ❌ ПРОБЛЕМА: входные данные дублируются!")

    # Проверка уникальности предсказаний
    print("\n2. Уникальность предсказаний:")

    all_different = True  # Инициализируем переменную

    if len(predictions) < 2:
        print("   ⚠️ Недостаточно предсказаний для анализа")
    else:
        # Сравниваем предсказания попарно
        symbols_list = list(predictions.keys())
        all_different = True

        for i in range(len(symbols_list)):
            for j in range(i + 1, len(symbols_list)):
                sym1, sym2 = symbols_list[i], symbols_list[j]
                pred1 = predictions[sym1]
                pred2 = predictions[sym2]

                # Сравниваем ключевые метрики
                same_type = pred1.get("signal_type") == pred2.get("signal_type")
                same_conf = abs(pred1.get("confidence", 0) - pred2.get("confidence", 0)) < 0.0001

                ret1_15m = pred1.get("predictions", {}).get("returns_15m", 0)
                ret2_15m = pred2.get("predictions", {}).get("returns_15m", 0)
                same_returns = abs(ret1_15m - ret2_15m) < 0.000001

                if same_type and same_conf and same_returns:
                    print(f"   ❌ {sym1} и {sym2} имеют одинаковые предсказания!")
                    all_different = False

        if all_different:
            print("   ✅ Все предсказания уникальны")

    # Проверка временных меток
    print("\n3. Временные метки предсказаний:")
    for symbol, pred in predictions.items():
        timestamp = pred.get("timestamp", "N/A")
        print(f"   • {symbol}: {timestamp}")

    print("\n" + "=" * 60)

    # Итоговый вывод
    if unique_hashes == len(features_hashes) and all_different:
        print("✅ ТЕСТ ПРОЙДЕН: ML генерирует уникальные предсказания")
    else:
        print("❌ ТЕСТ ПРОВАЛЕН: Обнаружены дублирующиеся предсказания")
        print("\n🔧 Рекомендации:")
        if unique_hashes != len(features_hashes):
            print("   1. Проверить загрузку данных - возможно загружаются одинаковые данные")
        if not all_different:
            print("   2. Проверить модель - возможно проблема с инференсом")
            print("   3. Проверить кеширование - возможно кеш не учитывает символ")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_ml_uniqueness())
