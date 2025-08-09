#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование исправленной ML логики
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd

from ml.ml_manager import MLManager


async def test_fixed_ml_logic():
    """Тест исправленной ML логики с разными сценариями"""

    print("🧪 === ТЕСТИРОВАНИЕ ИСПРАВЛЕННОЙ ML ЛОГИКИ ===")

    # Базовая конфигурация
    config = {"ml": {"model": {"device": "auto"}, "model_directory": "models/saved"}}

    # Создаем ML Manager
    ml_manager = MLManager(config)
    await ml_manager.initialize()

    print("✅ ML Manager инициализирован")

    # === ТЕСТ 1: Разные сценарии направлений ===
    print("\n🎯 === ТЕСТ 1: Различные сценарии направлений ===")

    # Создаем тестовые данные
    dates = pd.date_range(start="2024-01-01", periods=120, freq="15min")
    test_scenarios = [
        {
            "name": "Растущий тренд",
            "price_trend": 0.002,
            "volatility": 0.01,
        },  # 0.2% рост за свечу
        {
            "name": "Падающий тренд",
            "price_trend": -0.002,  # 0.2% падение за свечу
            "volatility": 0.01,
        },
        {
            "name": "Боковое движение",
            "price_trend": 0.0,
            "volatility": 0.005,
        },  # Нет тренда
        {
            "name": "Высокая волатильность",
            "price_trend": 0.0,
            "volatility": 0.03,  # 3% волатильность
        },
    ]

    for scenario in test_scenarios:
        print(f"\n📊 Сценарий: {scenario['name']}")

        # Генерируем данные для сценария
        base_price = 50000.0
        prices = [base_price]

        np.random.seed(42)  # Для воспроизводимости
        for i in range(1, len(dates)):
            # Добавляем тренд + случайность
            trend_change = scenario["price_trend"]
            random_change = np.random.normal(0, scenario["volatility"])
            total_change = trend_change + random_change

            new_price = prices[-1] * (1 + total_change)
            prices.append(new_price)

        # Создаем OHLCV данные
        test_data = []
        for i, (date, close) in enumerate(zip(dates, prices)):
            high = close * (1 + abs(np.random.normal(0, 0.003)))
            low = close * (1 - abs(np.random.normal(0, 0.003)))
            open_price = prices[i - 1] if i > 0 else close
            volume = np.random.uniform(100, 1000)

            test_data.append(
                {
                    "datetime": date,
                    "open": open_price,
                    "high": max(high, close, open_price),
                    "low": min(low, close, open_price),
                    "close": close,
                    "volume": volume,
                    "symbol": "BTCUSDT",
                }
            )

        test_df = pd.DataFrame(test_data)

        # Получаем предсказание
        try:
            prediction = await ml_manager.predict(test_df)

            print(f"   Результат: {prediction['signal_type']}")
            print(f"   Сила сигнала: {prediction['signal_strength']:.3f}")
            print(f"   Уверенность: {prediction['confidence']:.3f}")
            print(f"   Вероятность успеха: {prediction['success_probability']:.1%}")
            print(
                f"   Взвешенное направление: {prediction['predictions']['direction_score']:.3f}"
            )

        except Exception as e:
            print(f"   ❌ Ошибка: {e}")

    # === ТЕСТ 2: Проверка различных входных данных ===
    print("\n🎯 === ТЕСТ 2: Различные входные данные ===")

    # Генерируем 5 разных наборов данных
    for test_num in range(1, 6):
        print(f"\n📊 Тест #{test_num}")

        # Используем разные seed для разнообразия
        np.random.seed(test_num * 10)

        # Создаем случайные OHLCV данные
        base_price = 45000 + test_num * 2000  # Разные базовые цены
        prices = [base_price]

        for i in range(1, 120):
            change = np.random.normal(0, 0.015)  # 1.5% волатильность
            new_price = prices[-1] * (1 + change)
            prices.append(new_price)

        test_data = []
        for i, (date, close) in enumerate(zip(dates, prices)):
            high = close * (1 + abs(np.random.normal(0, 0.004)))
            low = close * (1 - abs(np.random.normal(0, 0.004)))
            open_price = prices[i - 1] if i > 0 else close
            volume = np.random.uniform(50, 1500)

            test_data.append(
                {
                    "datetime": date,
                    "open": open_price,
                    "high": max(high, close, open_price),
                    "low": min(low, close, open_price),
                    "close": close,
                    "volume": volume,
                    "symbol": "BTCUSDT",
                }
            )

        test_df = pd.DataFrame(test_data)

        try:
            prediction = await ml_manager.predict(test_df)

            print(f"   Сигнал: {prediction['signal_type']}")
            print(f"   Сила: {prediction['signal_strength']:.3f}")
            print(f"   Уверенность: {prediction['confidence']:.3f}")
            print(f"   Направление: {prediction['predictions']['direction_score']:.3f}")

        except Exception as e:
            print(f"   ❌ Ошибка: {e}")

    # === ТЕСТ 3: Статистика разнообразия ===
    print("\n🎯 === ТЕСТ 3: Статистика разнообразия сигналов ===")

    signals = []
    signal_types = []
    directions = []

    # Генерируем 20 разных предсказаний
    for i in range(20):
        np.random.seed(i * 7)  # Разные семена для разнообразия

        # Создаем случайные данные
        base_price = 40000 + i * 1000
        prices = [base_price]

        for j in range(1, 120):
            change = np.random.normal(0, 0.01 + i * 0.001)  # Увеличиваем волатильность
            new_price = prices[-1] * (1 + change)
            prices.append(new_price)

        test_data = []
        for j, (date, close) in enumerate(zip(dates, prices)):
            high = close * (1 + abs(np.random.normal(0, 0.003 + i * 0.0001)))
            low = close * (1 - abs(np.random.normal(0, 0.003 + i * 0.0001)))
            open_price = prices[j - 1] if j > 0 else close
            volume = np.random.uniform(100 + i * 10, 1000 + i * 50)

            test_data.append(
                {
                    "datetime": date,
                    "open": open_price,
                    "high": max(high, close, open_price),
                    "low": min(low, close, open_price),
                    "close": close,
                    "volume": volume,
                    "symbol": "BTCUSDT",
                }
            )

        test_df = pd.DataFrame(test_data)

        try:
            prediction = await ml_manager.predict(test_df)
            signals.append(prediction)
            signal_types.append(prediction["signal_type"])
            directions.append(prediction["predictions"]["direction_score"])

        except Exception as e:
            print(f"   ❌ Ошибка в тесте {i}: {e}")

    # Анализируем разнообразие
    unique_signals = set(signal_types)
    print("\n📊 Результаты анализа разнообразия:")
    print(f"   Всего протестировано: {len(signals)}")
    print(f"   Уникальных типов сигналов: {len(unique_signals)}")
    print(f"   Типы сигналов: {unique_signals}")

    # Подсчитываем количество каждого типа
    from collections import Counter

    signal_counts = Counter(signal_types)
    for signal_type, count in signal_counts.items():
        percentage = (count / len(signals)) * 100
        print(f"   {signal_type}: {count} ({percentage:.1f}%)")

    # Анализируем разброс направлений
    if directions:
        directions_array = np.array(directions)
        print("\n📊 Статистика направлений:")
        print(f"   Min: {directions_array.min():.3f}")
        print(f"   Max: {directions_array.max():.3f}")
        print(f"   Mean: {directions_array.mean():.3f}")
        print(f"   Std: {directions_array.std():.3f}")
        print(
            f"   Уникальных значений: {len(np.unique(np.round(directions_array, 3)))}"
        )

    # === ЗАКЛЮЧЕНИЕ ===
    print("\n🎉 === ЗАКЛЮЧЕНИЕ ===")

    if len(unique_signals) > 1:
        print("✅ ИСПРАВЛЕНИЕ УСПЕШНО!")
        print("   Модель теперь генерирует разнообразные сигналы")
        print("   Проблема с одинаковыми предсказаниями решена")
    else:
        print("❌ ПРОБЛЕМА НЕ РЕШЕНА!")
        print("   Модель все еще дает одинаковые сигналы")
        print("   Требуется дополнительная диагностика")

    if directions and np.std(directions) > 0.1:
        print("✅ Направления имеют хорошее разнообразие")
    else:
        print("⚠️  Направления все еще имеют низкое разнообразие")


if __name__ == "__main__":
    asyncio.run(test_fixed_ml_logic())
