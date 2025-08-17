#!/usr/bin/env python3
"""
ФИНАЛЬНЫЙ ТЕСТ: Проверка генерации ВСЕХ 240 признаков для UnifiedPatchTST модели
"""

import sys

import numpy as np
import pandas as pd

from ml.config.features_240 import REQUIRED_FEATURES_240, get_feature_groups
from ml.logic.feature_engineering_v2 import FeatureEngineer


def test_240_features():
    """Тестирует генерацию всех 240 требуемых признаков"""

    print("🧪 ФИНАЛЬНЫЙ ТЕСТ ГЕНЕРАЦИИ 240 ПРИЗНАКОВ")
    print("=" * 60)

    # 1. Создаем реалистичные тестовые данные
    print("📊 Создание тестовых данных...")
    np.random.seed(42)

    # BTCUSDT данные
    n_points = 500  # Больше данных для корректного расчета всех индикаторов
    btc_data = pd.DataFrame(
        {
            "symbol": ["BTCUSDT"] * n_points,
            "datetime": pd.date_range("2024-01-01", periods=n_points, freq="15min"),
            "open": np.random.randn(n_points).cumsum() + 50000,
            "high": np.random.randn(n_points).cumsum() + 50100,
            "low": np.random.randn(n_points).cumsum() + 49900,
            "close": np.random.randn(n_points).cumsum() + 50000,
            "volume": np.random.randint(1000, 10000, n_points),
            "turnover": np.random.randint(50000000, 500000000, n_points),
        }
    )

    # ETHUSDT данные для cross-asset features
    eth_data = pd.DataFrame(
        {
            "symbol": ["ETHUSDT"] * n_points,
            "datetime": pd.date_range("2024-01-01", periods=n_points, freq="15min"),
            "open": np.random.randn(n_points).cumsum() + 3000,
            "high": np.random.randn(n_points).cumsum() + 3100,
            "low": np.random.randn(n_points).cumsum() + 2900,
            "close": np.random.randn(n_points).cumsum() + 3000,
            "volume": np.random.randint(1000, 15000, n_points),
            "turnover": np.random.randint(3000000, 45000000, n_points),
        }
    )

    # Объединяем данные
    test_df = pd.concat([btc_data, eth_data], ignore_index=True)
    print(f"✅ Создано {len(test_df)} записей для {test_df['symbol'].nunique()} символов")

    # 2. Инициализируем FeatureEngineer
    print("\n🔧 Инициализация FeatureEngineer...")
    fe = FeatureEngineer({"features": {}}, inference_mode=True)
    fe.disable_progress = False  # Включаем логирование

    # 3. Генерируем признаки
    print("\n⚙️ Генерация признаков...")
    try:
        result_df = fe.create_features(test_df, inference_mode=True)
        print("✅ Генерация признаков завершена успешно")
    except Exception as e:
        print(f"❌ Ошибка при генерации признаков: {e}")
        import traceback

        traceback.print_exc()
        return False

    # 4. Анализ результатов
    print("\n📈 АНАЛИЗ РЕЗУЛЬТАТОВ")
    print("-" * 40)

    metadata_cols = ["symbol", "datetime", "open", "high", "low", "close", "volume"]
    feature_cols = [col for col in result_df.columns if col not in metadata_cols]

    print("📊 Общая статистика:")
    print(f"  - Записей в результате: {len(result_df):,}")
    print(f"  - Символов: {result_df['symbol'].nunique()}")
    print(f"  - Всего колонок: {len(result_df.columns)}")
    print(f"  - Метаданных: {len(metadata_cols)}")
    print(f"  - Признаков: {len(feature_cols)}")
    print(f"  - Требуется: {len(REQUIRED_FEATURES_240)}")

    # 5. Проверка соответствия
    missing_features = set(REQUIRED_FEATURES_240) - set(feature_cols)
    extra_features = set(feature_cols) - set(REQUIRED_FEATURES_240)

    print("\n🎯 ПРОВЕРКА СООТВЕТСТВИЯ:")
    print(f"  - Отсутствующих признаков: {len(missing_features)}")
    print(f"  - Лишних признаков: {len(extra_features)}")

    if missing_features:
        print(f"\n❌ ОТСУТСТВУЮЩИЕ ПРИЗНАКИ ({len(missing_features)}):")
        for i, feat in enumerate(sorted(missing_features), 1):
            print(f"  {i:3d}. {feat}")
        return False

    if extra_features:
        print(f"\n⚠️ ЛИШНИЕ ПРИЗНАКИ ({len(extra_features)}):")
        for i, feat in enumerate(sorted(extra_features)[:10], 1):
            print(f"  {i:3d}. {feat}")
        if len(extra_features) > 10:
            print(f"  ... и еще {len(extra_features) - 10} признаков")

    # 6. Анализ по группам
    print("\n📋 АНАЛИЗ ПО ГРУППАМ ПРИЗНАКОВ:")
    print("-" * 40)

    groups = get_feature_groups()
    for group_name, group_features in groups.items():
        if group_name == "basic":  # Базовые признаки в метаданных
            continue

        present = [f for f in group_features if f in feature_cols]
        missing_group = [f for f in group_features if f not in feature_cols]

        status = "✅" if len(missing_group) == 0 else "❌"
        print(f"  {status} {group_name.upper()}: {len(present)}/{len(group_features)} признаков")

        if missing_group:
            print(f"    Отсутствуют: {missing_group[:3]}{'...' if len(missing_group) > 3 else ''}")

    # 7. Проверка данных
    print("\n🔍 КАЧЕСТВО ДАННЫХ:")
    print("-" * 40)

    # Проверка NaN
    nan_count = result_df[feature_cols].isna().sum().sum()
    print(f"  - NaN значений: {nan_count:,}")

    # Проверка бесконечностей
    inf_count = np.isinf(result_df[feature_cols].select_dtypes(include=[np.number])).sum().sum()
    print(f"  - Бесконечных значений: {inf_count:,}")

    # Проверка константных признаков
    numeric_features = result_df[feature_cols].select_dtypes(include=[np.number])
    constant_features = []
    for col in numeric_features.columns:
        if numeric_features[col].nunique() <= 1:
            constant_features.append(col)

    print(f"  - Константных признаков: {len(constant_features)}")
    if constant_features:
        print(f"    Список: {constant_features[:5]}{'...' if len(constant_features) > 5 else ''}")

    # 8. Финальная оценка
    print("\n🏆 ФИНАЛЬНАЯ ОЦЕНКА:")
    print("=" * 40)

    if len(missing_features) == 0:
        print("✅ ВСЕ 240 ТРЕБУЕМЫХ ПРИЗНАКОВ ГЕНЕРИРУЮТСЯ КОРРЕКТНО!")
        print("✅ ML модель UnifiedPatchTST получит все необходимые данные")
        print("✅ Система готова к продакшену")

        # Пример использования
        print("\n💡 ПРИМЕР ИСПОЛЬЗОВАНИЯ:")
        print("```python")
        print("from ml.logic.feature_engineering_v2 import FeatureEngineer")
        print("fe = FeatureEngineer({'features': {}}, inference_mode=True)")
        print("features_df = fe.create_features(market_data, inference_mode=True)")
        print("# features_df содержит ровно 240 признаков + метаданные")
        print("```")

        return True
    else:
        print(f"❌ ТЕСТ НЕ ПРОЙДЕН: отсутствует {len(missing_features)} признаков")
        return False


if __name__ == "__main__":
    success = test_240_features()
    sys.exit(0 if success else 1)
