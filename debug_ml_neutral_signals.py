#!/usr/bin/env python3
"""
Диагностический скрипт для анализа проблемы с генерацией только NEUTRAL сигналов
"""

import asyncio
import sys
from pathlib import Path

import numpy as np
import torch

# Добавляем корень проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from data.data_loader import DataLoader
from ml.ml_manager import MLManager
from ml.ml_signal_processor import MLSignalProcessor

logger = setup_logger("ml_debug", level="INFO")


async def test_ml_pipeline():
    """
    Тестирует весь ML пайплайн для выявления проблем с NEUTRAL сигналами
    """
    print("🔍 ДИАГНОСТИКА ML СИСТЕМЫ - АНАЛИЗ NEUTRAL СИГНАЛОВ")
    print("=" * 60)

    try:
        # 1. Инициализация конфигурации
        config_manager = ConfigManager()
        config = config_manager.get_config()

        # 2. Инициализация ML Manager
        ml_manager = MLManager(config)
        await ml_manager.initialize()

        # 3. Инициализация ML Signal Processor
        ml_processor = MLSignalProcessor(ml_manager, config, config_manager)
        await ml_processor.initialize()

        # 4. Инициализация Data Loader
        data_loader = DataLoader(config)

        # 5. Получаем тестовые данные для нескольких символов
        test_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

        print(f"📊 Тестируем символы: {test_symbols}")
        print(f"📏 Минимальный confidence: {ml_processor.min_confidence}")
        print(f"📈 Минимальная сила сигнала: {ml_processor.min_signal_strength}")
        print()

        for symbol in test_symbols:
            print(f"\n🔄 Анализ {symbol}:")
            print("-" * 40)

            try:
                # Получаем исторические данные
                df = await data_loader.load_historical_data(
                    symbol=symbol,
                    interval="15m",
                    limit=200,  # 200 свечей для контекста
                    end_time=None,
                )

                if df is None or df.empty:
                    print(f"❌ Нет данных для {symbol}")
                    continue

                print(f"📈 Получено {len(df)} свечей")
                print(f"📅 Период: {df.index[0]} - {df.index[-1]}")

                # Делаем прямое предсказание через ML Manager
                print("\n🧠 Прямое предсказание ML Manager:")
                prediction = await ml_manager.predict(df)

                print(f"📊 Тип сигнала: {prediction.get('signal_type', 'UNKNOWN')}")
                print(f"📊 Confidence: {prediction.get('confidence', 0):.4f}")
                print(f"📊 Signal strength: {prediction.get('signal_strength', 0):.4f}")
                print(
                    f"📊 Direction score: {prediction.get('predictions', {}).get('direction_score', 'N/A')}"
                )

                # Анализируем raw model outputs
                predictions_data = prediction.get("predictions", {})
                returns_15m = predictions_data.get("returns_15m", 0)
                directions = predictions_data.get("directions_by_timeframe", [])
                direction_probs = predictions_data.get("direction_probabilities", [])

                print("\n🔍 Детальный анализ:")
                print(f"📈 Returns 15m: {returns_15m:.6f}")
                print(f"🎯 Directions: {directions}")

                if direction_probs:
                    for i, probs in enumerate(direction_probs):
                        timeframe = ["15m", "1h", "4h", "12h"][i] if i < 4 else f"{i}"
                        print(
                            f"📊 {timeframe}: LONG={probs[0]:.3f}, SHORT={probs[1]:.3f}, NEUTRAL={probs[2]:.3f}"
                        )

                # Тестируем ML Signal Processor
                print("\n🔄 Обработка через ML Signal Processor:")
                signal = await ml_processor.process_market_data(
                    symbol=symbol, exchange="bybit", ohlcv_data=df
                )

                if signal:
                    print(f"✅ Сгенерирован сигнал: {signal.signal_type.value}")
                    print(f"📊 Confidence: {signal.confidence:.4f}")
                    print(f"📊 Strength: {signal.strength:.4f}")
                    print(f"💰 Entry price: {signal.entry_price}")
                    if signal.stop_loss:
                        print(f"🛑 Stop Loss: {signal.stop_loss}")
                    if signal.take_profit:
                        print(f"🎯 Take Profit: {signal.take_profit}")
                else:
                    print("❌ Сигнал не сгенерирован")

                # Анализируем проблемы
                print("\n🔍 Диагностика проблем:")

                # Проверяем пороги
                conf = prediction.get("confidence", 0)
                strength = prediction.get("signal_strength", 0)

                print(
                    f"📏 Confidence check: {conf:.4f} {'≥' if conf >= ml_processor.min_confidence else '<'} {ml_processor.min_confidence} - {'✅' if conf >= ml_processor.min_confidence else '❌'}"
                )
                print(
                    f"📏 Strength check: {strength:.4f} {'≥' if strength >= ml_processor.min_signal_strength else '<'} {ml_processor.min_signal_strength} - {'✅' if strength >= ml_processor.min_signal_strength else '❌'}"
                )

                # Проверяем направления
                signal_type = prediction.get("signal_type", "NEUTRAL")
                print(
                    f"🎯 Signal type: {signal_type} ({'ТОРГОВЫЙ' if signal_type in ['LONG', 'SHORT'] else 'НЕ ТОРГОВЫЙ'})"
                )

                if signal_type == "NEUTRAL":
                    print("⚠️  ПРОБЛЕМА: Модель генерирует только NEUTRAL сигналы!")

                    # Детальный анализ направлений
                    if directions:
                        long_count = directions.count(0)
                        short_count = directions.count(1)
                        neutral_count = directions.count(2)

                        print("📊 Голосование по таймфреймам:")
                        print(f"   LONG: {long_count}/4 ({long_count / 4 * 100:.1f}%)")
                        print(
                            f"   SHORT: {short_count}/4 ({short_count / 4 * 100:.1f}%)"
                        )
                        print(
                            f"   NEUTRAL: {neutral_count}/4 ({neutral_count / 4 * 100:.1f}%)"
                        )

                        if neutral_count >= 3:
                            print("❌ Проблема: 3+ таймфреймов предсказывают NEUTRAL")
                        elif long_count < 3 and short_count < 3:
                            print(
                                "❌ Проблема: Нет явного большинства (нужно 3+ голосов)"
                            )

            except Exception as e:
                print(f"❌ Ошибка обработки {symbol}: {e}")
                logger.exception(f"Error processing {symbol}")

        # 6. Проверяем модель напрямую
        print("\n🔧 ПРЯМАЯ ПРОВЕРКА МОДЕЛИ:")
        print("-" * 40)

        if ml_manager.model is None:
            print("❌ Модель не загружена!")
            return

        # Создаем тестовый тензор
        device = ml_manager.device
        test_input = torch.randn(1, 96, 240).to(
            device
        )  # batch_size=1, context=96, features=240

        print(f"🧠 Модель: {type(ml_manager.model).__name__}")
        print(f"💻 Device: {device}")
        print(f"📊 Input shape: {test_input.shape}")

        # Прямой вызов модели
        ml_manager.model.eval()
        with torch.no_grad():
            raw_output = ml_manager.model(test_input)

        print(f"📊 Output shape: {raw_output.shape}")
        print(
            f"📊 Output range: [{raw_output.min().item():.6f}, {raw_output.max().item():.6f}]"
        )
        print(f"📊 Output mean: {raw_output.mean().item():.6f}")
        print(f"📊 Output std: {raw_output.std().item():.6f}")

        # Анализируем конкретные выходы
        output_np = raw_output.cpu().numpy()[0]

        print("\n🔍 Анализ 20 выходов модели:")
        future_returns = output_np[0:4]
        direction_logits = output_np[4:16]
        risk_metrics = output_np[16:20]

        print(f"📈 Future returns (0-3): {future_returns}")
        print(f"🎯 Direction logits (4-15): {direction_logits}")
        print(f"⚠️  Risk metrics (16-19): {risk_metrics}")

        # Анализируем направления
        direction_logits_reshaped = direction_logits.reshape(4, 3)
        print("\n🎯 Направления по таймфреймам:")

        for i, logits in enumerate(direction_logits_reshaped):
            timeframe = ["15m", "1h", "4h", "12h"][i]
            exp_logits = np.exp(logits - np.max(logits))
            probs = exp_logits / exp_logits.sum()
            predicted_class = np.argmax(probs)
            class_name = ["LONG", "SHORT", "NEUTRAL"][predicted_class]

            print(f"   {timeframe}: logits={logits} -> probs={probs} -> {class_name}")

        # 7. Рекомендации по исправлению
        print("\n💡 РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ:")
        print("-" * 40)

        # Проверяем основные проблемы
        all_neutral = all(
            np.argmax(direction_logits_reshaped[i]) == 2 for i in range(4)
        )
        small_returns = all(abs(r) < 0.001 for r in future_returns)

        if all_neutral:
            print("🔴 КРИТИЧНО: Все таймфреймы предсказывают NEUTRAL")
            print("   -> Возможная причина: модель переобучена на нейтральные примеры")
            print("   -> Решение: пересмотреть обучающие данные и class weights")

        if small_returns:
            print("🔴 КРИТИЧНО: Все предсказанные доходности близки к нулю")
            print("   -> Возможная причина: проблемы с нормализацией или scaler")
            print("   -> Решение: проверить масштабирование целевых переменных")

        # Проверяем пороги
        if ml_processor.min_confidence > 0.5:
            print("🟡 ВНИМАНИЕ: Слишком высокий порог confidence")
            print(f"   -> Текущий: {ml_processor.min_confidence}")
            print("   -> Рекомендация: снизить до 0.3-0.4 для тестирования")

        if ml_processor.min_signal_strength > 0.3:
            print("🟡 ВНИМАНИЕ: Слишком высокий порог signal_strength")
            print(f"   -> Текущий: {ml_processor.min_signal_strength}")
            print("   -> Рекомендация: снизить до 0.1-0.2 для тестирования")

        print("\n✅ Диагностика завершена!")

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        logger.exception("Critical error in ML pipeline test")


if __name__ == "__main__":
    asyncio.run(test_ml_pipeline())
