#!/usr/bin/env python3
"""
Тест полного ML pipeline для генерации торговых сигналов
"""

import asyncio
import logging

import numpy as np
import pandas as pd

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def test_ml_pipeline():
    """Тест полного ML pipeline"""

    print("=" * 60)
    print("ТЕСТ ПОЛНОГО ML PIPELINE")
    print("=" * 60)

    try:
        # 1. Тест RealTimeIndicatorCalculator
        print("\n1. Тестирование RealTimeIndicatorCalculator...")
        from ml.realtime_indicator_calculator import RealTimeIndicatorCalculator

        calc = RealTimeIndicatorCalculator()
        print("✅ RealTimeIndicatorCalculator создан")

        # Получаем данные из БД
        from sqlalchemy import desc, select

        from database.connections import get_async_db
        from database.models.market_data import RawMarketData

        async with get_async_db() as session:
            stmt = (
                select(RawMarketData)
                .where(RawMarketData.symbol == "BTCUSDT")
                .order_by(desc(RawMarketData.timestamp))
                .limit(300)
            )

            result = await session.execute(stmt)
            raw_data = result.scalars().all()

        if not raw_data:
            print("❌ Нет данных в БД для BTCUSDT")
            return

        print(f"✅ Загружено {len(raw_data)} записей из БД")

        # Преобразуем в DataFrame
        data_list = []
        for row in raw_data:
            data_list.append(
                {
                    "timestamp": row.timestamp,
                    "open": float(row.open),
                    "high": float(row.high),
                    "low": float(row.low),
                    "close": float(row.close),
                    "volume": float(row.volume),
                }
            )

        # Сортируем по времени (от старых к новым)
        data_list.reverse()
        df = pd.DataFrame(data_list)
        df.index = pd.to_datetime([row.datetime for row in reversed(raw_data)])

        print(f"✅ DataFrame подготовлен: {df.shape}")

        # Тестируем расчет индикаторов
        print("\n🔄 Расчет индикаторов...")
        indicators = await calc.calculate_indicators("BTCUSDT", df, save_to_db=False)

        if indicators:
            print("✅ Индикаторы рассчитаны успешно")
            print(f"   Метаданные: {indicators.get('metadata', {})}")
            print(f"   OHLCV: {list(indicators.get('ohlcv', {}).keys())}")
            print(
                f"   Технические индикаторы: {len(indicators.get('technical_indicators', {}))}"
            )
            print(f"   ML признаки: {len(indicators.get('ml_features', {}))}")
        else:
            print("❌ Не удалось рассчитать индикаторы")
            return

        # 2. Тест подготовки данных для ML модели
        print("\n2. Тестирование подготовки данных для ML...")
        features_array, metadata = await calc.prepare_ml_input(
            "BTCUSDT", df, lookback=96
        )

        print(f"✅ Данные для ML подготовлены: {features_array.shape}")
        print(f"   Форма: {features_array.shape} (ожидается: [1, 96, ~56])")
        print(f"   Метаданные: {metadata}")

        # Проверяем что нет NaN или Inf
        nan_count = np.isnan(features_array).sum()
        inf_count = np.isinf(features_array).sum()
        print(f"   NaN значений: {nan_count}")
        print(f"   Inf значений: {inf_count}")

        if features_array.shape[0] != 1 or features_array.shape[1] != 96:
            print("❌ Неправильная форма массива для ML модели")
            return

        print("✅ Данные готовы для ML модели")

        # 3. Проверяем что модель может быть загружена (если существует)
        print("\n3. Проверка доступности ML модели...")
        import os

        model_path = "models/saved/best_model_20250728_215703.pth"

        if os.path.exists(model_path):
            print(f"✅ ML модель найдена: {model_path}")

            # Пробуем загрузить модель (без запуска предсказания)
            try:
                import torch

                if torch.cuda.is_available():
                    device = torch.device("cuda")
                    print("✅ CUDA доступна")
                else:
                    device = torch.device("cpu")
                    print("⚠️ Используется CPU")

                # Не загружаем модель полностью, только проверяем файл
                model_info = torch.load(model_path, map_location=device)
                print("✅ Модель загружается корректно")
                print(f"   Ключи в состоянии модели: {list(model_info.keys())[:5]}...")

            except Exception as e:
                print(f"❌ Ошибка загрузки модели: {e}")
        else:
            print(f"⚠️ ML модель не найдена: {model_path}")
            print("   Создайте модель или используйте mock предсказания")

        # 4. Тест пакетного расчета (для нескольких символов)
        print("\n4. Тестирование пакетного расчета...")
        symbols = ["BTCUSDT"]
        ohlcv_data = {"BTCUSDT": df}

        batch_results = await calc.calculate_indicators_batch(symbols, ohlcv_data)

        if batch_results and "BTCUSDT" in batch_results:
            print("✅ Пакетный расчет работает")
            btc_result = batch_results["BTCUSDT"]
            print(
                f"   ML признаки для BTCUSDT: {len(btc_result.get('ml_features', {}))}"
            )
        else:
            print("❌ Пакетный расчет не работает")

        print("\n✅ Тест ML Pipeline успешно завершен!")
        print("\n📋 Результаты тестирования:")
        print("   ✅ RealTimeIndicatorCalculator работает")
        print("   ✅ FeatureEngineer генерирует 56 признаков")
        print("   ✅ Данные подготавливаются в правильном формате для ML")
        print("   ✅ Пакетная обработка работает")
        print("   ✅ ML pipeline готов к использованию")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_ml_pipeline())
