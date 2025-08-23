#!/usr/bin/env python3
"""
Тестирование компонентов ML визуализации
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

print("🔍 Тестирование ML визуализации...")

# Проверка импортов
try:
    print("📦 Проверка импорта библиотек визуализации...")
    import matplotlib

    print(f"  ✅ matplotlib {matplotlib.__version__}")

    import plotly

    print(f"  ✅ plotly {plotly.__version__}")

    import seaborn

    print(f"  ✅ seaborn {seaborn.__version__}")

except ImportError as e:
    print(f"  ❌ Ошибка импорта: {e}")
    print("  Установите: pip install matplotlib plotly seaborn")
    sys.exit(1)

# Проверка модулей
try:
    print("\n📦 Проверка импорта модулей системы...")

    from visualize_ml_predictions import create_predictions_chart

    print("  ✅ visualize_ml_predictions")

    from web.api.endpoints.ml_visualization import router

    print("  ✅ ml_visualization API endpoints")

    from database.connections.postgres import AsyncPGPool

    print("  ✅ Database connection")

except ImportError as e:
    print(f"  ❌ Ошибка импорта модуля: {e}")
    sys.exit(1)


# Простой тест создания графика
async def test_visualization():
    print("\n🎨 Тест создания графиков...")

    from datetime import datetime

    import numpy as np
    import pandas as pd

    # Создаем тестовые данные
    dates = pd.date_range(end=datetime.now(), periods=100, freq="15min")
    test_df = pd.DataFrame(
        {
            "open": np.random.randn(100).cumsum() + 100,
            "high": np.random.randn(100).cumsum() + 101,
            "low": np.random.randn(100).cumsum() + 99,
            "close": np.random.randn(100).cumsum() + 100,
            "volume": np.random.randint(1000, 10000, 100),
        },
        index=dates,
    )

    # Тестовое предсказание
    test_prediction = {
        "signal_type": "LONG",
        "confidence": 0.75,
        "signal_strength": 0.543,
        "predictions": {
            "direction_probabilities": [
                [0.2, 0.3, 0.5],
                [0.15, 0.25, 0.6],
                [0.25, 0.35, 0.4],
                [0.3, 0.3, 0.4],
            ],
            "returns_15m": 0.0023,
            "returns_1h": 0.0045,
            "returns_4h": 0.0067,
            "returns_12h": 0.0089,
        },
        "stop_loss_pct": 0.02,
        "take_profit_pct": 0.04,
        "risk_level": "medium",
    }

    try:
        # Импортируем функции визуализации
        from visualize_ml_predictions import create_market_data_analysis, create_predictions_chart

        # Создаем графики
        print("  📊 Создание интерактивного графика...")
        chart_file = create_predictions_chart("TEST_SYMBOL", test_prediction, test_df)
        if chart_file:
            print(f"    ✅ График создан: {chart_file}")

        print("  📈 Создание анализа рыночных данных...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        market_file = create_market_data_analysis("TEST_SYMBOL", test_df, timestamp)
        if market_file:
            print(f"    ✅ Анализ создан: {market_file}")

        print("\n✅ Все тесты пройдены успешно!")

        # Проверяем созданные файлы
        charts_dir = Path("data/charts")
        if charts_dir.exists():
            files = list(charts_dir.glob("*TEST_SYMBOL*"))
            print(f"\n📁 Создано файлов: {len(files)}")
            for f in files[-5:]:  # Показываем последние 5
                size_kb = f.stat().st_size / 1024
                print(f"  - {f.name} ({size_kb:.1f} KB)")

    except Exception as e:
        print(f"  ❌ Ошибка создания графиков: {e}")
        import traceback

        traceback.print_exc()


# Тест базы данных
async def test_database():
    print("\n💾 Тест подключения к БД...")
    try:
        result = await AsyncPGPool.fetch("SELECT version()")
        if result:
            print(f"  ✅ PostgreSQL подключен: {result[0]['version'][:30]}...")

        # Проверяем наличие данных
        count = await AsyncPGPool.fetch("SELECT COUNT(*) as cnt FROM raw_market_data")
        if count:
            print(f"  📊 Записей в raw_market_data: {count[0]['cnt']}")
    except Exception as e:
        print(f"  ❌ Ошибка БД: {e}")


# Основная функция
async def main():
    print("=" * 60)
    print("ML VISUALIZATION SYSTEM TEST")
    print("=" * 60)

    await test_visualization()
    await test_database()

    print("\n" + "=" * 60)
    print("✨ Тестирование завершено!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
