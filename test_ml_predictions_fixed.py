#!/usr/bin/env python3
"""
Тест исправления уникальности предсказаний ML модели
Проверяем что исправления в ml_signal_processor.py работают
"""

import asyncio

from core.config.config_manager import ConfigManager
from ml.ml_manager import MLManager
from ml.ml_signal_processor import MLSignalProcessor


async def test_fixed_unique_predictions():
    """Тест уникальности предсказаний после исправления"""
    print("=" * 80)
    print("ТЕСТ ИСПРАВЛЕНИЯ УНИКАЛЬНОСТИ ML ПРЕДСКАЗАНИЙ")
    print("=" * 80)

    # Инициализация компонентов
    config_manager = ConfigManager()
    config = config_manager.get_config()

    # 1. Инициализация ML Manager и Signal Processor
    print("\n1. Инициализация компонентов...")
    ml_manager = MLManager(config)
    await ml_manager.initialize()

    signal_processor = MLSignalProcessor(
        ml_manager=ml_manager,
        config=config,
        config_manager=config_manager,
    )
    await signal_processor.initialize()
    print("✓ Компоненты инициализированы")

    # 2. Тестируем process_realtime_signal для разных символов
    print("\n2. Тестирование process_realtime_signal...")
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    signals = {}

    for symbol in symbols:
        print(f"\n🔄 Генерация сигнала для {symbol}...")
        signal = await signal_processor.process_realtime_signal(
            symbol=symbol, exchange="bybit"
        )

        if signal:
            signals[symbol] = signal
            print(
                f"✅ {symbol}: {signal.signal_type.value}, conf={signal.confidence:.3f}"
            )

            # Извлекаем prediction data из extra_data
            raw_prediction = signal.extra_data.get("raw_prediction", {})
            predictions_data = raw_prediction.get("predictions", {})

            print(f"   Returns 15m: {predictions_data.get('returns_15m', 0):.6f}")
            print(f"   Returns 1h:  {predictions_data.get('returns_1h', 0):.6f}")
            print(
                f"   Direction score: {predictions_data.get('direction_score', 0):.3f}"
            )
        else:
            print(f"❌ {symbol}: Нет сигнала")

    # 3. Анализ уникальности
    print("\n3. Анализ уникальности предсказаний...")

    if len(signals) >= 2:
        # Сравниваем предсказания разных символов
        signal_items = list(signals.items())

        for i in range(len(signal_items)):
            for j in range(i + 1, len(signal_items)):
                symbol1, signal1 = signal_items[i]
                symbol2, signal2 = signal_items[j]

                # Извлекаем predictions
                pred1 = signal1.extra_data.get("raw_prediction", {}).get(
                    "predictions", {}
                )
                pred2 = signal2.extra_data.get("raw_prediction", {}).get(
                    "predictions", {}
                )

                ret1_15m = pred1.get("returns_15m", 0)
                ret2_15m = pred2.get("returns_15m", 0)

                ret1_1h = pred1.get("returns_1h", 0)
                ret2_1h = pred2.get("returns_1h", 0)

                dir1 = pred1.get("direction_score", 0)
                dir2 = pred2.get("direction_score", 0)

                print(f"\n📊 Сравнение {symbol1} vs {symbol2}:")
                print(f"   Returns 15m: {ret1_15m:.8f} vs {ret2_15m:.8f}")
                print(f"   Returns 1h:  {ret1_1h:.8f} vs {ret2_1h:.8f}")
                print(f"   Direction:   {dir1:.6f} vs {dir2:.6f}")

                # Проверяем различия
                diff_15m = abs(ret1_15m - ret2_15m)
                diff_1h = abs(ret1_1h - ret2_1h)
                diff_dir = abs(dir1 - dir2)

                if diff_15m < 1e-6 and diff_1h < 1e-6 and diff_dir < 1e-6:
                    print("   ❌ ОДИНАКОВЫЕ предсказания!")
                else:
                    print("   ✅ Предсказания РАЗЛИЧАЮТСЯ")
                    print(
                        f"      Разности: 15m={diff_15m:.8f}, 1h={diff_1h:.8f}, dir={diff_dir:.6f}"
                    )

    # 4. Тест кэширования - делаем повторный запрос для одного символа
    print("\n4. Тест кэширования - повторный запрос...")
    if "BTCUSDT" in signals:
        print("🔄 Повторный запрос для BTCUSDT (должен использовать кэш)...")
        signal_cached = await signal_processor.process_realtime_signal(
            symbol="BTCUSDT", exchange="bybit"
        )

        if signal_cached:
            # Сравниваем с оригинальным
            orig_pred = (
                signals["BTCUSDT"]
                .extra_data.get("raw_prediction", {})
                .get("predictions", {})
            )
            cached_pred = signal_cached.extra_data.get("raw_prediction", {}).get(
                "predictions", {}
            )

            orig_ret = orig_pred.get("returns_15m", 0)
            cached_ret = cached_pred.get("returns_15m", 0)

            if abs(orig_ret - cached_ret) < 1e-8:
                print("✅ Кэш работает - одинаковые результаты для одного символа")
            else:
                print(
                    f"❌ Кэш НЕ работает - разные результаты: {orig_ret:.8f} vs {cached_ret:.8f}"
                )

    # 5. Очистка кэша и повторный тест
    print("\n5. Очистка кэша и повторный тест...")
    signal_processor.prediction_cache.clear()
    print("🧹 Кэш очищен")

    print("🔄 Повторная генерация для всех символов...")
    new_signals = {}
    for symbol in symbols:
        signal = await signal_processor.process_realtime_signal(
            symbol=symbol, exchange="bybit"
        )
        if signal:
            new_signals[symbol] = signal
            raw_pred = signal.extra_data.get("raw_prediction", {}).get(
                "predictions", {}
            )
            print(f"{symbol}: returns_15m={raw_pred.get('returns_15m', 0):.6f}")

    # Cleanup
    if hasattr(signal_processor, "data_loader") and signal_processor.data_loader:
        await signal_processor.data_loader.cleanup()

    print("\n" + "=" * 80)
    print("ТЕСТ ЗАВЕРШЕН")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_fixed_unique_predictions())
