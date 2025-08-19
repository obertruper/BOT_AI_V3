#!/usr/bin/env python3
"""
Отладка отсутствующих признаков в FeatureEngineer
"""

import numpy as np
import pandas as pd

from core.logger import setup_logger
from ml.config.features_240 import REQUIRED_FEATURES_240
from ml.logic.archive_old_versions.feature_engineering_v2 import FeatureEngineer

logger = setup_logger(__name__)


def generate_test_data(n_samples=300):
    """Генерирует тестовые OHLCV данные"""
    dates = pd.date_range(start="2024-01-01", periods=n_samples, freq="5T")

    # Генерируем реалистичные OHLCV данные
    np.random.seed(42)
    base_price = 50000
    returns = np.random.normal(0, 0.001, n_samples)
    prices = [base_price]

    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))

    prices = np.array(prices)

    # Создаем OHLCV
    df = pd.DataFrame(
        {
            "datetime": dates,
            "open": prices,
            "high": prices * (1 + np.random.uniform(0, 0.01, n_samples)),
            "low": prices * (1 - np.random.uniform(0, 0.01, n_samples)),
            "close": prices,
            "volume": np.random.uniform(100, 1000, n_samples),
            "symbol": "BTCUSDT",
        }
    )

    # Добавляем turnover
    df["turnover"] = df["close"] * df["volume"]

    return df


def debug_missing_features():
    """Отладка отсутствующих признаков"""
    logger.info("🔍 Начинаем отладку отсутствующих признаков...")

    # Генерируем тестовые данные
    test_data = generate_test_data(300)
    logger.info(f"📊 Сгенерированы тестовые данные: {len(test_data)} свечей")

    # Создаем FeatureEngineer с inference mode
    config = {"inference_mode": True}
    engineer = FeatureEngineer(config, inference_mode=True)

    # Рассчитываем признаки
    logger.info("🔧 Начинаем расчет признаков...")
    features_df = engineer.create_features(test_data, inference_mode=True)
    logger.info(f"✅ Признаки рассчитаны: {features_df.shape}")

    # Анализируем отсутствующие признаки
    feature_cols = [col for col in features_df.columns if col not in ["symbol", "datetime"]]
    available_features = set(feature_cols)
    required_features = set(REQUIRED_FEATURES_240)

    missing_features = required_features - available_features
    extra_features = available_features - required_features

    logger.info("📊 Анализ признаков:")
    logger.info(f"  🎯 Требуемых: {len(required_features)}")
    logger.info(f"  ✅ Доступных: {len(available_features)}")
    logger.info(f"  ❌ Отсутствующих: {len(missing_features)}")
    logger.info(f"  ➕ Дополнительных: {len(extra_features)}")

    # Группируем отсутствующие признаки по типам
    missing_by_type = {}
    for feature in missing_features:
        feature_type = "other"
        if feature.startswith("rsi_"):
            feature_type = "rsi"
        elif feature.startswith("sma_"):
            feature_type = "sma"
        elif feature.startswith("ema_"):
            feature_type = "ema"
        elif feature.startswith("macd_"):
            feature_type = "macd"
        elif feature.startswith("bb_"):
            feature_type = "bollinger"
        elif feature.startswith("atr_"):
            feature_type = "atr"
        elif feature.startswith("adx_"):
            feature_type = "adx"
        elif feature.startswith("cci_"):
            feature_type = "cci"
        elif feature.startswith("stoch_"):
            feature_type = "stochastic"
        elif feature.startswith("willr_"):
            feature_type = "williams"
        elif feature.startswith("mfi_"):
            feature_type = "mfi"
        elif "obv" in feature:
            feature_type = "obv"
        elif feature.startswith("returns_"):
            feature_type = "returns"
        elif feature.startswith("volatility_"):
            feature_type = "volatility"

        if feature_type not in missing_by_type:
            missing_by_type[feature_type] = []
        missing_by_type[feature_type].append(feature)

    print("\n" + "=" * 80)
    print("🔍 АНАЛИЗ ОТСУТСТВУЮЩИХ ПРИЗНАКОВ")
    print("=" * 80)

    for feature_type, features in sorted(missing_by_type.items()):
        print(f"\n📊 {feature_type.upper()} ({len(features)} отсутствующих):")
        for feature in sorted(features)[:10]:  # Показываем первые 10
            print(f"   ❌ {feature}")
        if len(features) > 10:
            print(f"   ... и еще {len(features) - 10} признаков")

    # Проверяем конкретные проблемные признаки
    problematic_features = [
        "rsi_5",
        "rsi_14",
        "rsi_21",
        "sma_5",
        "sma_10",
        "sma_20",
        "ema_5",
        "ema_10",
        "ema_20",
        "macd_12_26",
        "macd_signal_12_26",
        "macd_histogram_12_26",
        "bb_upper_20",
        "bb_middle_20",
        "bb_lower_20",
        "atr_7",
        "atr_14",
        "atr_21",
    ]

    print("\n🎯 ПРОВЕРКА КЛЮЧЕВЫХ ПРИЗНАКОВ:")
    for feature in problematic_features:
        status = "✅" if feature in available_features else "❌"
        variance_status = ""
        if feature in available_features:
            if feature in features_df.columns:
                var = features_df[feature].var()
                if pd.isna(var) or var == 0:
                    variance_status = " (⚠️ нулевая дисперсия)"
                else:
                    variance_status = f" (дисперсия: {var:.6f})"
        print(f"   {status} {feature}{variance_status}")

    return {
        "total_required": len(required_features),
        "total_available": len(available_features),
        "missing_count": len(missing_features),
        "missing_by_type": missing_by_type,
        "problematic_features": problematic_features,
    }


if __name__ == "__main__":
    result = debug_missing_features()

    print("\n" + "=" * 80)
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 80)
    print(f"🎯 Требуется признаков: {result['total_required']}")
    print(f"✅ Доступно признаков: {result['total_available']}")
    print(f"❌ Отсутствует признаков: {result['missing_count']}")
    print(
        f"📈 Процент готовности: {(result['total_required'] - result['missing_count']) / result['total_required'] * 100:.1f}%"
    )
