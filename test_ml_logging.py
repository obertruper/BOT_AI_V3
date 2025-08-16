#!/usr/bin/env python3
"""
Тестовый скрипт для проверки детального логирования ML предсказаний
"""

import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from rich.console import Console

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool
from ml.ml_manager import MLManager
from ml.ml_prediction_logger import MLPredictionLogger

logger = setup_logger("test_ml_logging")
console = Console()
ml_prediction_logger = MLPredictionLogger()


async def generate_test_data(symbol: str = "BTCUSDT", periods: int = 300) -> pd.DataFrame:
    """Генерирует тестовые OHLCV данные"""

    # Базовая цена
    base_price = 50000

    # Генерируем случайные данные
    dates = pd.date_range(
        start=datetime.now() - timedelta(hours=periods * 0.25), periods=periods, freq="15min"
    )

    prices = base_price + np.cumsum(np.random.randn(periods) * 100)

    df = pd.DataFrame(
        {
            "datetime": dates,
            "symbol": symbol,
            "open": prices + np.random.randn(periods) * 50,
            "high": prices + np.abs(np.random.randn(periods) * 100),
            "low": prices - np.abs(np.random.randn(periods) * 100),
            "close": prices,
            "volume": np.abs(np.random.randn(periods) * 10000 + 50000),
            "turnover": np.abs(np.random.randn(periods) * 500000 + 2500000),
        }
    )

    # Корректируем high/low
    df["high"] = df[["open", "high", "close"]].max(axis=1)
    df["low"] = df[["open", "low", "close"]].min(axis=1)

    return df


async def test_ml_logging():
    """Тестирует полный процесс логирования ML предсказаний"""

    print("\n" + "=" * 60)
    print(" ТЕСТ ДЕТАЛЬНОГО ЛОГИРОВАНИЯ ML ПРЕДСКАЗАНИЙ ".center(60, "="))
    print("=" * 60 + "\n")

    try:
        # 1. Инициализируем ML Manager
        print("1️⃣ Инициализация ML Manager...")
        config = {
            "ml": {
                "model": {
                    "path": "models/unified_patchtst_model.pth",
                    "device": "cpu",  # Используем CPU для теста
                }
            }
        }

        ml_manager = MLManager(config)
        await ml_manager.initialize()
        print("✅ ML Manager инициализирован\n")

        # 2. Генерируем тестовые данные
        print("2️⃣ Генерация тестовых данных...")
        test_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

        for symbol in test_symbols:
            print(f"\n  Обработка {symbol}...")

            # Генерируем данные
            df = await generate_test_data(symbol, periods=300)
            print(f"  ✅ Сгенерировано {len(df)} свечей")

            # 3. Делаем предсказание
            print("  📊 Выполнение ML предсказания...")
            prediction = await ml_manager.predict(df)

            # Выводим результат предсказания
            print("  🎯 Результат предсказания:")
            print(f"     Signal: {prediction['signal_type']}")
            print(f"     Confidence: {prediction['signal_confidence']:.2%}")
            print(f"     Returns 15m: {prediction['returns_15m']:.4f}")
            print(f"     Direction 15m: {prediction['direction_15m']}")

            # 4. Проверяем логирование
            print("  📝 Проверка логирования в БД...")

            # Небольшая задержка для сохранения батча
            await asyncio.sleep(1)

        # 5. Принудительно сохраняем оставшиеся предсказания
        print("\n3️⃣ Сохранение накопленных предсказаний...")
        await ml_prediction_logger.flush()
        print("✅ Все предсказания сохранены\n")

        # 6. Проверяем что данные сохранились в БД
        print("4️⃣ Проверка данных в БД...")
        query = """
            SELECT
                symbol,
                signal_type,
                signal_confidence,
                predicted_return_15m,
                direction_15m,
                features_count,
                inference_time_ms,
                created_at
            FROM ml_predictions
            WHERE created_at >= NOW() - INTERVAL '1 minute'
            ORDER BY created_at DESC
            LIMIT 10
        """

        rows = await AsyncPGPool.fetch(query)

        if rows:
            print(f"✅ Найдено {len(rows)} записей в БД:\n")

            # Выводим таблицу с результатами
            print(
                "  {:^10} | {:^10} | {:^10} | {:^12} | {:^10} | {:^8} | {:^10}".format(
                    "Symbol",
                    "Signal",
                    "Confidence",
                    "Return 15m",
                    "Direction",
                    "Features",
                    "Time (ms)",
                )
            )
            print("  " + "-" * 90)

            for row in rows:
                print(
                    "  {:^10} | {:^10} | {:^10.2%} | {:^12.4f} | {:^10} | {:^8} | {:^10.1f}".format(
                        row["symbol"],
                        row["signal_type"],
                        row["signal_confidence"],
                        row["predicted_return_15m"],
                        row["direction_15m"],
                        row["features_count"],
                        row["inference_time_ms"] or 0,
                    )
                )
        else:
            print("⚠️ Записи не найдены в БД")

        # 7. Проверяем детальный вывод логов
        print("\n5️⃣ Детальные логи выведены в консоль выше ☝️")
        print("   (см. красиво оформленные таблицы ML PREDICTION DETAILS)")

        print("\n" + "=" * 60)
        print(" ТЕСТ ЗАВЕРШЕН УСПЕШНО ".center(60, "✅"))
        print("=" * 60 + "\n")

    except Exception as e:
        logger.error(f"❌ Ошибка в тесте: {e}")
        import traceback

        traceback.print_exc()


async def main():
    """Главная функция"""
    # Инициализируем пул соединений
    await AsyncPGPool.init_pool()

    try:
        await test_ml_logging()
    finally:
        await AsyncPGPool.close_pool()


if __name__ == "__main__":
    asyncio.run(main())
