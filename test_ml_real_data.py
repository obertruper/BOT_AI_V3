#!/usr/bin/env python3
"""
Тест ML системы с реальными данными
"""

import asyncio
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Добавляем корень проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.config.config_manager import ConfigManager
from ml.ml_manager import MLManager
from ml.ml_signal_processor import MLSignalProcessor


async def test_ml_with_real_data():
    """
    Тестирует ML с реальными данными из базы
    """
    print("📊 ТЕСТ ML СИСТЕМЫ С РЕАЛЬНЫМИ ДАННЫМИ")
    print("=" * 50)

    try:
        # Инициализация
        config_manager = ConfigManager()
        config = config_manager.get_config()

        ml_manager = MLManager(config)
        await ml_manager.initialize()

        ml_processor = MLSignalProcessor(ml_manager, config, config_manager)
        await ml_processor.initialize()

        print("✅ Компоненты инициализированы")

        # Создаем синтетические реалистичные данные OHLCV
        print("\n📈 Создаем синтетические реалистичные данные:")

        # Генерируем реалистичные OHLCV данные
        np.random.seed(42)  # Для воспроизводимости

        dates = pd.date_range(start="2024-01-01", periods=200, freq="15T")

        # Генерируем случайное блуждание для цены
        base_price = 50000  # Начальная цена BTC
        returns = np.random.normal(0, 0.002, 200)  # 0.2% стандартное отклонение
        prices = base_price * np.exp(np.cumsum(returns))

        # Генерируем OHLCV
        data = []
        for i, price in enumerate(prices):
            # Добавляем внутрибарную волатильность
            noise = np.random.normal(0, price * 0.001, 4)  # 0.1% внутрибарная волатильность

            open_price = prices[i - 1] if i > 0 else price
            close_price = price

            # High и Low с некоторой логикой
            high_price = max(open_price, close_price) + abs(noise[0])
            low_price = min(open_price, close_price) - abs(noise[1])

            volume = np.random.exponential(1000000)  # Экспоненциальное распределение объема

            data.append(
                {
                    "datetime": dates[i],
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "volume": volume,
                    "symbol": "BTCUSDT",
                }
            )

        df = pd.DataFrame(data)
        df.set_index("datetime", inplace=True)

        print(f"📊 Создан DataFrame: {df.shape}")
        print(f"📈 Ценовой диапазон: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
        print("📊 Последние 5 свечей:")
        print(df[["open", "high", "low", "close", "volume"]].tail())

        # Тестируем ML Manager напрямую
        print("\n🧠 Тест ML Manager с реальными данными:")

        prediction = await ml_manager.predict(df)

        print("🎯 Результат предсказания:")
        print(f"   Signal type: {prediction['signal_type']}")
        print(f"   Confidence: {prediction['confidence']:.4f}")
        print(f"   Signal strength: {prediction['signal_strength']:.4f}")

        # Детальный анализ
        predictions_data = prediction.get("predictions", {})
        print("\n📊 Детальная информация:")
        print(f"   Returns 15m: {predictions_data.get('returns_15m', 'N/A'):.6f}")
        print(f"   Returns 1h: {predictions_data.get('returns_1h', 'N/A'):.6f}")
        print(f"   Direction score: {predictions_data.get('direction_score', 'N/A'):.4f}")

        directions = predictions_data.get("directions_by_timeframe", [])
        direction_probs = predictions_data.get("direction_probabilities", [])

        if directions:
            print(f"   Directions: {directions}")
            for i, probs in enumerate(direction_probs):
                timeframe = ["15m", "1h", "4h", "12h"][i] if i < 4 else f"{i}"
                class_names = ["LONG", "SHORT", "NEUTRAL"]
                predicted_class = np.argmax(probs)
                print(
                    f"   {timeframe}: {class_names[predicted_class]} (p={probs[predicted_class]:.3f})"
                )

        # Тестируем ML Signal Processor
        print("\n🔄 Тест ML Signal Processor:")

        signal = await ml_processor.process_market_data(
            symbol="BTCUSDT", exchange="bybit", ohlcv_data=df
        )

        if signal:
            print("✅ Сгенерирован сигнал!")
            print(f"   Type: {signal.signal_type.value}")
            print(f"   Confidence: {signal.confidence:.4f}")
            print(f"   Strength: {signal.strength:.4f}")
            print(f"   Entry price: {signal.entry_price}")
            if signal.stop_loss:
                print(f"   Stop Loss: {signal.stop_loss}")
            if signal.take_profit:
                print(f"   Take Profit: {signal.take_profit}")
        else:
            print("❌ Сигнал не сгенерирован")
            print("   Возможные причины:")
            print(f"   - Confidence {prediction['confidence']:.4f} < {ml_processor.min_confidence}")
            print(
                f"   - Signal strength {prediction['signal_strength']:.4f} < {ml_processor.min_signal_strength}"
            )

        # Тест разнообразия с разными данными
        print("\n🔄 Тест разнообразия с разными трендами:")

        trends = ["bull", "bear", "sideways"]
        signals_generated = []

        for trend in trends:
            print(f"\n📈 Тестируем {trend} тренд:")

            # Генерируем данные с разными трендами
            if trend == "bull":
                trend_returns = np.random.normal(0.001, 0.002, 200)  # Бычий тренд
            elif trend == "bear":
                trend_returns = np.random.normal(-0.001, 0.002, 200)  # Медвежий тренд
            else:
                trend_returns = np.random.normal(0, 0.001, 200)  # Боковик

            trend_prices = base_price * np.exp(np.cumsum(trend_returns))

            # Создаем новый DataFrame
            trend_data = []
            for i, price in enumerate(trend_prices):
                noise = np.random.normal(0, price * 0.001, 4)
                open_price = trend_prices[i - 1] if i > 0 else price
                close_price = price
                high_price = max(open_price, close_price) + abs(noise[0])
                low_price = min(open_price, close_price) - abs(noise[1])
                volume = np.random.exponential(1000000)

                trend_data.append(
                    {
                        "datetime": dates[i],
                        "open": open_price,
                        "high": high_price,
                        "low": low_price,
                        "close": close_price,
                        "volume": volume,
                        "symbol": "BTCUSDT",
                    }
                )

            trend_df = pd.DataFrame(trend_data)
            trend_df.set_index("datetime", inplace=True)

            # Предсказание
            trend_prediction = await ml_manager.predict(trend_df)
            signal_type = trend_prediction["signal_type"]
            confidence = trend_prediction["confidence"]

            print(f"   Результат: {signal_type} (confidence: {confidence:.3f})")
            signals_generated.append(signal_type)

        # Статистика
        print("\n📊 Статистика по трендам:")
        for trend, signal in zip(trends, signals_generated, strict=False):
            print(f"   {trend}: {signal}")

        unique_signals = set(signals_generated)
        print(f"\n📈 Разнообразие сигналов: {len(unique_signals)}/3")

        if len(unique_signals) > 1:
            print("✅ Система генерирует разнообразные сигналы для разных трендов!")
        else:
            print("⚠️  Система генерирует одинаковые сигналы для всех трендов")

        print("\n✅ Тестирование завершено!")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_ml_with_real_data())
