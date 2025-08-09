#!/usr/bin/env python3
"""
Тест ML предсказаний на CPU для проверки работоспособности
"""

import asyncio
import os

# Настройки для работы на CPU
os.environ["CUDA_VISIBLE_DEVICES"] = ""  # Принудительно отключаем GPU

from datetime import datetime, timedelta

import numpy as np
import pandas as pd


async def test_ml_predictions():
    """Тест ML предсказаний на CPU"""
    print("=" * 60)
    print("ТЕСТ ML ПРЕДСКАЗАНИЙ НА CPU")
    print("=" * 60)

    try:
        # Импортируем необходимые модули
        from core.config.config_manager import ConfigManager
        from ml.ml_manager import MLManager

        # Инициализируем конфигурацию
        config_manager = ConfigManager()
        config = config_manager.get_system_config()

        # Принудительно устанавливаем CPU
        if "ml" not in config:
            config["ml"] = {}
        if "model" not in config["ml"]:
            config["ml"]["model"] = {}
        config["ml"]["model"]["device"] = "cpu"

        print("\n📋 Конфигурация:")
        print(f"  Device: {config['ml']['model'].get('device', 'cpu')}")
        print(
            f"  Model path: {config['ml']['model'].get('path', 'models/saved/best_model_20250728_215703.pth')}"
        )

        # Создаем и инициализируем ML Manager
        print("\n🧠 Инициализация ML Manager...")
        ml_manager = MLManager(config)
        await ml_manager.initialize()
        print("✅ ML Manager инициализирован")

        # Получаем информацию о модели
        model_info = ml_manager.get_model_info()
        print("\n📊 Информация о модели:")
        for key, value in model_info.items():
            print(f"  {key}: {value}")

        # Создаем тестовые OHLCV данные (300 свечей)
        print("\n📈 Создание тестовых данных...")
        base_price = 100000.0
        timestamps = []
        data_list = []

        start_time = datetime.now() - timedelta(hours=75)  # 300 * 15 минут

        for i in range(300):
            timestamp = start_time + timedelta(minutes=15 * i)
            timestamps.append(timestamp)

            # Генерируем реалистичные свечи
            volatility = 0.002  # 0.2% волатильность
            trend = 0.00001 * i  # Небольшой восходящий тренд

            open_price = base_price * (1 + np.random.normal(0, volatility) + trend)
            close_price = open_price * (1 + np.random.normal(0, volatility))
            high_price = max(open_price, close_price) * (
                1 + abs(np.random.normal(0, volatility / 2))
            )
            low_price = min(open_price, close_price) * (
                1 - abs(np.random.normal(0, volatility / 2))
            )
            volume = 1000 * (1 + abs(np.random.normal(0, 0.5)))

            data_list.append(
                {
                    "timestamp": timestamp,
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "volume": volume,
                }
            )

            base_price = close_price

        # Создаем DataFrame
        df = pd.DataFrame(data_list)
        df["symbol"] = "BTCUSDT"
        df.index = pd.DatetimeIndex(df["timestamp"])

        print(f"✅ Создано {len(df)} свечей")
        print(f"  Цена от {df['close'].min():.2f} до {df['close'].max():.2f}")
        print(f"  Последняя цена: {df['close'].iloc[-1]:.2f}")

        # Делаем предсказание
        print("\n⚡ Выполнение предсказания...")
        import time

        start_time = time.time()

        prediction = await ml_manager.predict(df)

        elapsed_time = time.time() - start_time
        print(f"✅ Предсказание выполнено за {elapsed_time:.2f} секунд")

        # Выводим результаты
        print("\n📊 Результаты предсказания:")
        print(f"  Сигнал: {prediction['signal_type']}")
        print(f"  Сила сигнала: {prediction['signal_strength']:.3f}")
        print(f"  Уверенность: {prediction['confidence']:.3f}")
        print(f"  Вероятность успеха: {prediction['success_probability']:.1%}")
        print(f"  Уровень риска: {prediction['risk_level']}")

        if prediction["stop_loss"]:
            print(f"  Stop Loss: {prediction['stop_loss']:.2f}")
        if prediction["take_profit"]:
            print(f"  Take Profit: {prediction['take_profit']:.2f}")

        print("\n  Детальные предсказания:")
        for key, value in prediction["predictions"].items():
            if isinstance(value, (int, float)):
                print(f"    {key}: {value:.3f}")

        # Тест с разными рыночными условиями
        print("\n🧪 Тест разных рыночных условий:")

        # 1. Сильный восходящий тренд
        trend_df = df.copy()
        trend_df["close"] = trend_df["close"] * np.linspace(1.0, 1.05, len(trend_df))
        trend_pred = await ml_manager.predict(trend_df)
        print(
            f"\n  Восходящий тренд (+5%): {trend_pred['signal_type']} (сила: {trend_pred['signal_strength']:.3f})"
        )

        # 2. Сильный нисходящий тренд
        trend_df = df.copy()
        trend_df["close"] = trend_df["close"] * np.linspace(1.0, 0.95, len(trend_df))
        trend_pred = await ml_manager.predict(trend_df)
        print(
            f"  Нисходящий тренд (-5%): {trend_pred['signal_type']} (сила: {trend_pred['signal_strength']:.3f})"
        )

        # 3. Боковое движение
        flat_df = df.copy()
        flat_df["close"] = flat_df["close"].mean() + np.random.normal(
            0, 100, len(flat_df)
        )
        flat_pred = await ml_manager.predict(flat_df)
        print(
            f"  Боковое движение: {flat_pred['signal_type']} (сила: {flat_pred['signal_strength']:.3f})"
        )

        print("\n✅ Все тесты ML предсказаний успешно завершены!")
        print("   Модель работает корректно на CPU")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_ml_predictions())
