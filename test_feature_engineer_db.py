#!/usr/bin/env python3
"""
Тест FeatureEngineer на данных из базы данных
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


async def test_feature_engineer_with_db_data():
    """Тест FeatureEngineer на реальных данных из БД"""

    print("=" * 60)
    print("ТЕСТ FEATURE ENGINEER НА ДАННЫХ ИЗ БД")
    print("=" * 60)

    try:
        # Импорт FeatureEngineer
        from ml.logic.feature_engineering import FeatureEngineer

        print("✅ FeatureEngineer импортирован")

        # Подключение к БД
        from sqlalchemy import desc, select

        from database.connections import get_async_db
        from database.models.market_data import RawMarketData

        print("✅ Подключение к БД установлено")

        # Получаем данные из БД
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
                    "datetime": row.datetime,
                    "open": float(row.open),
                    "high": float(row.high),
                    "low": float(row.low),
                    "close": float(row.close),
                    "volume": float(row.volume),
                    "symbol": row.symbol,
                }
            )

        # Сортируем по времени (от старых к новым)
        data_list.reverse()
        df = pd.DataFrame(data_list)

        print(f"✅ DataFrame создан: {df.shape}")
        print(
            f"   Временной период: {df['datetime'].iloc[0]} - {df['datetime'].iloc[-1]}"
        )
        print("   Пример данных:")
        print(df[["datetime", "open", "high", "low", "close", "volume"]].head(3))

        # Добавляем недостающие поля
        if "turnover" not in df.columns:
            df["turnover"] = df["close"] * df["volume"]

        # Тестируем FeatureEngineer
        fe = FeatureEngineer({})
        print("✅ FeatureEngineer создан")

        # Генерируем признаки
        print("🔄 Генерация признаков...")
        features = await fe.create_features(df)

        print(f"✅ Признаки сгенерированы: {features.shape}")
        print(f"   Количество признаков: {features.shape[1]}")
        print(f"   Названия признаков: {len(fe.get_feature_names())}")

        # Проверяем качество признаков
        nan_count = np.isnan(features).sum()
        inf_count = np.isinf(features).sum()

        print(f"   NaN значений: {nan_count}")
        print(f"   Inf значений: {inf_count}")
        print(f"   Диапазон значений: [{np.min(features):.3f}, {np.max(features):.3f}]")

        # Показываем несколько примеров признаков
        feature_names = fe.get_feature_names()
        print("\n📊 Примеры признаков (последняя точка):")
        last_features = features[-1]
        for i, name in enumerate(feature_names[:10]):  # Первые 10
            print(f"   {name}: {last_features[i]:.4f}")

        if len(feature_names) > 10:
            print(f"   ... и еще {len(feature_names) - 10} признаков")

        # Тест на разных размерах данных
        print("\n🔍 Тест на разных размерах данных:")
        for test_size in [50, 100, 200, 300]:
            if len(df) >= test_size:
                test_df = df.tail(test_size).copy()
                test_features = await fe.create_features(test_df)
                print(f"   {test_size} свечей → {test_features.shape[1]} признаков")
            else:
                print(f"   {test_size} свечей → недостаточно данных")

        print("\n✅ Тест FeatureEngineer успешно завершен!")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_feature_engineer_with_db_data())
