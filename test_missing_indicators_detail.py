#!/usr/bin/env python3
"""
Детальный анализ отсутствующих индикаторов из REQUIRED_FEATURES_240
"""

import logging

import numpy as np
import pandas as pd

from ml.config.features_240 import REQUIRED_FEATURES_240
from ml.logic.feature_engineering_v2 import FeatureEngineer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_missing_indicators():
    """Тестирует отсутствующие индикаторы"""

    # Создаем тестовые данные
    import datetime

    # Генерируем тестовые OHLCV данные
    dates = pd.date_range(
        start=datetime.datetime.now() - datetime.timedelta(days=30),
        end=datetime.datetime.now(),
        freq="15min",
    )

    np.random.seed(42)  # Для воспроизводимости
    price_base = 50000

    ohlcv_data = []
    for i, date in enumerate(dates):
        price_change = np.random.normal(0, 0.02)  # 2% волатильность
        price = price_base * (1 + price_change * i / 1000)

        high = price * (1 + abs(np.random.normal(0, 0.005)))
        low = price * (1 - abs(np.random.normal(0, 0.005)))
        open_price = price + np.random.normal(0, price * 0.001)
        close_price = price + np.random.normal(0, price * 0.001)
        volume = np.random.uniform(100, 1000)

        ohlcv_data.append(
            [int(date.timestamp() * 1000), open_price, high, low, close_price, volume]
        )

    ohlcv = ohlcv_data

    # Создаем DataFrame
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["datetime"] = df["timestamp"]  # Добавляем колонку datetime
    df["symbol"] = "BTCUSDT"  # Добавляем колонку symbol
    df["turnover"] = df["volume"] * df["close"]  # Добавляем turnover

    # Инициализируем feature engineer
    config = {"features": {}}
    feature_engineer = FeatureEngineer(config=config, inference_mode=True)

    # Создаем признаки
    logger.info("🔧 Создаем признаки...")
    df_features = feature_engineer.create_features(df.copy())

    print(f"📊 Всего созданных признаков: {len(df_features.columns)}")

    # Анализируем отсутствующие признаки
    missing_features = []
    zero_variance_features = []
    available_features = set(df_features.columns)

    for feature in REQUIRED_FEATURES_240:
        if feature not in available_features:
            missing_features.append(feature)
        elif df_features[feature].var() == 0 or df_features[feature].isna().all():
            zero_variance_features.append(feature)

    print("\n" + "=" * 80)
    print("🔍 ДЕТАЛЬНЫЙ АНАЛИЗ ОТСУТСТВУЮЩИХ ПРИЗНАКОВ")
    print("=" * 80)

    if missing_features:
        print(f"\n❌ ПОЛНОСТЬЮ ОТСУТСТВУЮЩИЕ ПРИЗНАКИ ({len(missing_features)}):")
        for i, feature in enumerate(missing_features[:20]):  # Показываем первые 20
            print(f"   {i + 1:2d}. {feature}")
        if len(missing_features) > 20:
            print(f"   ... и еще {len(missing_features) - 20} признаков")

    if zero_variance_features:
        print(f"\n⚠️ ПРИЗНАКИ С НУЛЕВОЙ ДИСПЕРСИЕЙ ({len(zero_variance_features)}):")
        for i, feature in enumerate(zero_variance_features[:20]):  # Показываем первые 20
            print(f"   {i + 1:2d}. {feature}")
        if len(zero_variance_features) > 20:
            print(f"   ... и еще {len(zero_variance_features) - 20} признаков")

    # Анализируем конкретные группы отсутствующих признаков
    macd_missing = [f for f in missing_features + zero_variance_features if "macd" in f]
    stoch_missing = [f for f in missing_features + zero_variance_features if "stoch" in f]
    williams_missing = [f for f in missing_features + zero_variance_features if "williams" in f]
    adx_missing = [f for f in missing_features + zero_variance_features if "adx" in f]
    mfi_missing = [f for f in missing_features + zero_variance_features if "mfi" in f]

    print("\n📈 АНАЛИЗ ПО ГРУППАМ ИНДИКАТОРОВ:")
    print(f"   🔸 MACD проблемы: {macd_missing}")
    print(f"   🔸 Stochastic проблемы: {stoch_missing}")
    print(f"   🔸 Williams %R проблемы: {williams_missing}")
    print(f"   🔸 ADX проблемы: {adx_missing}")
    print(f"   🔸 MFI проблемы: {mfi_missing}")

    # Проверяем что есть в DataFrame
    print("\n🔧 ДОСТУПНЫЕ ПОХОЖИЕ ПРИЗНАКИ:")
    for prefix in ["macd", "stoch", "williams", "adx", "mfi"]:
        similar = [col for col in df_features.columns if prefix in col.lower()]
        print(f"   🔸 {prefix.upper()}: {similar[:5]}...")  # Показываем первые 5

    return {
        "total_features": len(df_features.columns),
        "missing_features": missing_features,
        "zero_variance_features": zero_variance_features,
        "required_total": len(REQUIRED_FEATURES_240),
    }


if __name__ == "__main__":
    result = test_missing_indicators()

    print("\n" + "=" * 80)
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 80)
    print(f"✅ Всего создано признаков: {result['total_features']}")
    print(f"🎯 Требуется признаков: {result['required_total']}")
    print(f"❌ Полностью отсутствует: {len(result['missing_features'])}")
    print(f"⚠️ С нулевой дисперсией: {len(result['zero_variance_features'])}")
    print(
        f"📈 Процент готовности: {((result['required_total'] - len(result['missing_features']) - len(result['zero_variance_features'])) / result['required_total']) * 100:.1f}%"
    )
