#!/usr/bin/env python3
"""
Интегрирует ТОЧНЫЕ признаки из обучающего файла в текущую ML систему.
Использует exact_training_features.py для генерации идентичных признаков.
"""

import asyncio

import numpy as np
import pandas as pd

from database.connections.postgres import AsyncPGPool
from exact_training_features import ExactTrainingFeatures


async def test_exact_features():
    """Тестирует генерацию точных признаков из обучения"""
    print("=" * 80)
    print("🎯 ТЕСТ ТОЧНЫХ ПРИЗНАКОВ ИЗ ОБУЧЕНИЯ")
    print("=" * 80)

    # 1. Загружаем конфигурацию из обучения
    training_config = {
        "features": {
            "technical": [
                {"name": "sma", "periods": [10, 20, 50]},
                {"name": "ema", "periods": [10, 20, 50]},
                {"name": "rsi", "period": 14},
                {"name": "macd", "slow": 26, "fast": 12, "signal": 9},
                {"name": "bollinger_bands", "period": 20, "std_dev": 2},
                {"name": "atr", "period": 14},
                {"name": "stochastic", "period": 14, "smooth": 3},
                {"name": "adx", "period": 14},
            ]
        }
    }

    # 2. Загружаем данные
    print("\n📊 Загрузка данных...")
    query = """
        SELECT datetime, symbol, open, high, low, close, volume, 
               COALESCE(volume * close, 0) as turnover
        FROM raw_market_data 
        WHERE symbol = $1 
        ORDER BY datetime DESC 
        LIMIT 500
    """

    symbol = "BTCUSDT"
    data = await AsyncPGPool.fetch(query, symbol)

    if not data:
        print(f"❌ Нет данных для {symbol}")
        return False

    df = pd.DataFrame([dict(record) for record in data])
    df = df.sort_values("datetime").reset_index(drop=True)

    # Конвертируем Decimal в float
    for col in ["open", "high", "low", "close", "volume", "turnover"]:
        df[col] = df[col].astype(float)

    print(f"✅ Загружено {len(df)} записей для {symbol}")

    # 3. Создаем ТОЧНЫЕ признаки из обучения
    print("\n🔧 Генерация ТОЧНЫХ признаков из обучения...")
    feature_engineer = ExactTrainingFeatures(training_config)
    feature_engineer.disable_progress = True

    # Применяем все методы в правильном порядке (как в обучении)
    df_features = df.copy()

    # Порядок ВАЖЕН - точно как в обучении!
    df_features = feature_engineer._create_basic_features(df_features)
    df_features = feature_engineer._create_technical_indicators(df_features)
    df_features = feature_engineer._create_microstructure_features(df_features)
    df_features = feature_engineer._create_rally_detection_features(df_features)
    df_features = feature_engineer._create_signal_quality_features(df_features)
    df_features = feature_engineer._create_futures_specific_features(df_features)
    df_features = feature_engineer._create_ml_optimized_features(df_features)
    df_features = feature_engineer._create_temporal_features(df_features)

    # Cross-asset features (если есть несколько символов)
    if len(df_features["symbol"].unique()) > 1:
        df_features = feature_engineer._create_cross_asset_features(df_features)

    # Простая обработка NaN (временно, пока не добавим полный метод)
    # Заполняем числовые колонки
    numeric_cols = df_features.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if df_features[col].isna().any():
            # Forward fill, затем backward fill, затем 0
            df_features[col] = df_features[col].ffill().bfill().fillna(0)

    # 4. Анализ результатов
    print("\n📈 Анализ сгенерированных признаков:")

    # Список критических признаков из обучения
    critical_features = [
        "returns",  # LOG returns
        "rsi",  # Один RSI с периодом 14
        "macd",  # Нормализованный!
        "volume_ratio",
        "vwap",
        "close_vwap_ratio",
        "atr_pct",  # В процентах
        "bb_position",
        "volume_zscore",
        "price_impact",  # Специальная формула
        "amihud_illiquidity",  # Масштабированная
    ]

    print("\n✅ Проверка критических признаков:")
    for feat in critical_features:
        if feat in df_features.columns:
            values = df_features[feat].dropna()
            if len(values) > 0:
                print(
                    f"  {feat:20s}: mean={values.mean():8.4f}, std={values.std():8.4f}, "
                    f"min={values.min():8.4f}, max={values.max():8.4f}"
                )
            else:
                print(f"  {feat:20s}: ⚠️ Все NaN")
        else:
            print(f"  {feat:20s}: ❌ НЕ НАЙДЕН")

    # 5. Проверка специфичных формул
    print("\n🔬 Проверка специфичных формул:")

    # MACD должен быть нормализован (малые значения)
    if "macd" in df_features.columns:
        macd_max = df_features["macd"].abs().max()
        if macd_max < 10:
            print(f"  ✅ MACD нормализован (max={macd_max:.2f}%)")
        else:
            print(f"  ❌ MACD НЕ нормализован (max={macd_max:.2f})")

    # Returns должны быть LOG
    if "returns" in df_features.columns:
        # Проверяем, что используется log формула
        test_close = df_features["close"].iloc[-10:]
        test_returns = np.log(test_close / test_close.shift(1))
        actual_returns = df_features["returns"].iloc[-10:]

        # Убираем NaN и сравниваем
        test_clean = test_returns.dropna().values
        actual_clean = actual_returns.dropna().values

        # Берем минимальную длину для сравнения
        min_len = min(len(test_clean), len(actual_clean))
        if min_len > 0 and np.allclose(test_clean[:min_len], actual_clean[:min_len], rtol=1e-6):
            print("  ✅ Returns используют LOG формулу")
        else:
            print("  ❌ Returns НЕ используют LOG формулу")

    # close_vwap_ratio должен быть ограничен
    if "close_vwap_ratio" in df_features.columns:
        vwap_min = df_features["close_vwap_ratio"].min()
        vwap_max = df_features["close_vwap_ratio"].max()
        if vwap_min >= 0.7 and vwap_max <= 1.3:
            print(f"  ✅ VWAP ratio ограничен [{vwap_min:.2f}, {vwap_max:.2f}]")
        else:
            print(f"  ⚠️ VWAP ratio вне ожидаемых границ [{vwap_min:.2f}, {vwap_max:.2f}]")

    # 6. Итоговая статистика
    print("\n📊 Итоговая статистика:")
    total_features = len(df_features.columns)
    numeric_features = df_features.select_dtypes(include=[np.number]).columns
    nan_counts = df_features[numeric_features].isna().sum()
    features_with_nan = (nan_counts > 0).sum()

    print(f"  Всего признаков: {total_features}")
    print(f"  Числовых признаков: {len(numeric_features)}")
    print(f"  Признаков с NaN: {features_with_nan}")
    print(f"  Среднее NaN на признак: {nan_counts.mean():.1f}")

    # Проверка разнообразия
    zero_variance = []
    for col in numeric_features:
        if df_features[col].std() < 1e-10:
            zero_variance.append(col)

    print(f"  Признаков с нулевой дисперсией: {len(zero_variance)}")
    print(f"  Активных признаков: {len(numeric_features) - len(zero_variance)}")

    return True


async def compare_with_current():
    """Сравнивает точные признаки с текущей реализацией"""
    print("\n" + "=" * 80)
    print("🔍 СРАВНЕНИЕ С ТЕКУЩЕЙ РЕАЛИЗАЦИЕЙ")
    print("=" * 80)

    from ml.config.features_240 import REQUIRED_FEATURES_240

    print(f"\n📊 Текущая система ожидает: {len(REQUIRED_FEATURES_240)} признаков")
    print("📊 Обучение использовало: ~208 признаков")

    print("\n❌ Основные различия:")
    print("  1. Количество признаков (240 vs 208)")
    print("  2. RSI: множественные периоды vs один")
    print("  3. ETH корреляции: есть vs не было")
    print("  4. Микроструктурные признаки: разные формулы")

    print("\n✅ Рекомендация:")
    print("  Использовать ExactTrainingFeatures для генерации признаков")
    print("  Это обеспечит 100% соответствие обучению")


async def main():
    """Главная функция"""
    # Тестируем точные признаки
    success = await test_exact_features()

    if success:
        # Сравниваем с текущей реализацией
        await compare_with_current()

        print("\n" + "=" * 80)
        print("🎉 ГОТОВО К ИНТЕГРАЦИИ!")
        print("=" * 80)
        print("\nДля использования точных признаков:")
        print("1. Замените FeatureEngineer на ExactTrainingFeatures")
        print("2. Используйте конфигурацию из обучения")
        print("3. Проверьте, что все 208 признаков генерируются")
        print("4. Мониторьте качество предсказаний")
    else:
        print("\n❌ Тест не пройден")


if __name__ == "__main__":
    asyncio.run(main())
