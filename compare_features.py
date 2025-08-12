#!/usr/bin/env python3
"""
Сравнение признаков между обучением и текущей интеграцией
"""

import asyncio
import pickle
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))


async def compare_features():
    """Сравнение генерации признаков"""

    print("=" * 70)
    print("🔍 СРАВНЕНИЕ ПРИЗНАКОВ МЕЖДУ ОБУЧЕНИЕМ И ИНТЕГРАЦИЕЙ")
    print("=" * 70)

    # 1. Загружаем scaler из обучения
    scaler_path = Path("models/saved/data_scaler.pkl")
    if not scaler_path.exists():
        print(f"❌ Scaler не найден: {scaler_path}")
        return

    with open(scaler_path, "rb") as f:
        scaler = pickle.load(f)

    print("\n📊 SCALER ИЗ ОБУЧЕНИЯ:")
    print(f"Тип: {type(scaler).__name__}")
    print(f"Количество признаков: {scaler.n_features_in_}")
    print(f"Признаки обучены: {scaler.n_samples_seen_}")

    # Статистика scaler
    if hasattr(scaler, "mean_"):
        print("\nСтатистика признаков при обучении:")
        print(f"  Mean range: [{scaler.mean_.min():.4f}, {scaler.mean_.max():.4f}]")
        print(f"  Std range: [{scaler.scale_.min():.4f}, {scaler.scale_.max():.4f}]")

        # Проверка на вырожденные признаки
        zero_std = np.where(scaler.scale_ < 1e-6)[0]
        if len(zero_std) > 0:
            print(
                f"  ⚠️ Признаки с нулевой дисперсией: {len(zero_std)} из {scaler.n_features_in_}"
            )

    # 2. Проверяем текущую генерацию признаков
    print("\n📊 ТЕКУЩАЯ ГЕНЕРАЦИЯ ПРИЗНАКОВ:")

    from core.config.config_manager import ConfigManager
    from ml.logic.feature_engineering import FeatureEngineer

    config_manager = ConfigManager()
    config = {
        "ml": config_manager.get_ml_config(),
        "system": config_manager.get_system_config(),
        "trading": config_manager.get_config("trading", {}),
    }

    feature_engineer = FeatureEngineer(config)

    # Создаем тестовые данные
    test_data = pd.DataFrame(
        {
            "timestamp": pd.date_range(end=datetime.now(), periods=100, freq="15min"),
            "open": np.random.randn(100) * 1000 + 50000,
            "high": np.random.randn(100) * 1000 + 50100,
            "low": np.random.randn(100) * 1000 + 49900,
            "close": np.random.randn(100) * 1000 + 50000,
            "volume": np.random.randn(100) * 100000 + 1000000,
            "symbol": "BTCUSDT",
        }
    )

    # Генерируем признаки
    features = feature_engineer.create_features(test_data)

    if isinstance(features, pd.DataFrame):
        # Извлекаем числовые признаки
        numeric_cols = features.select_dtypes(include=[np.number]).columns
        # Исключаем целевые переменные и метаданные
        feature_cols = [
            col
            for col in numeric_cols
            if not col.startswith(("future_", "direction_", "profit_"))
            and col not in ["id", "timestamp", "datetime", "symbol"]
        ]

        print(f"Сгенерировано признаков: {len(feature_cols)}")
        print(f"Ожидалось признаков: {scaler.n_features_in_}")

        if len(feature_cols) != scaler.n_features_in_:
            print("❌ НЕСООТВЕТСТВИЕ КОЛИЧЕСТВА ПРИЗНАКОВ!")
            print(f"   Разница: {abs(len(feature_cols) - scaler.n_features_in_)}")
        else:
            print("✅ Количество признаков совпадает")

        # Проверяем первые 10 признаков
        print("\nПервые 10 признаков:")
        for i, col in enumerate(feature_cols[:10]):
            print(f"  {i:3d}: {col}")
    else:
        print(f"❌ Неожиданный тип результата: {type(features)}")

    # 3. Проверяем список признаков из проекта обучения
    print("\n📊 ОЖИДАЕМЫЕ ПРИЗНАКИ (из обучения):")

    # Стандартный набор признаков v4.0
    expected_features = [
        # Базовые OHLCV
        "open",
        "high",
        "low",
        "close",
        "volume",
        # Returns
        "returns_1",
        "returns_2",
        "returns_3",
        "returns_5",
        "returns_10",
        "log_returns_1",
        "log_returns_2",
        "log_returns_3",
        # Volatility
        "volatility_5",
        "volatility_10",
        "volatility_20",
        "atr_14",
        "atr_20",
        "true_range",
        # Moving Averages
        "sma_5",
        "sma_10",
        "sma_20",
        "sma_50",
        "ema_5",
        "ema_10",
        "ema_20",
        "ema_50",
        # Price ratios
        "close_to_sma_5",
        "close_to_sma_10",
        "close_to_sma_20",
        "close_to_ema_5",
        "close_to_ema_10",
        "close_to_ema_20",
        # Technical Indicators
        "rsi_14",
        "rsi_20",
        "rsi_30",
        "macd",
        "macd_signal",
        "macd_diff",
        "bb_upper",
        "bb_middle",
        "bb_lower",
        "bb_width",
        "bb_position",
        "stoch_k",
        "stoch_d",
        "adx_14",
        "plus_di",
        "minus_di",
        "cci_20",
        "mfi_14",
        "obv",
        "obv_ma_10",
        "vwap",
        "close_to_vwap",
        # Volume features
        "volume_ma_5",
        "volume_ma_10",
        "volume_ratio",
        "volume_delta",
        "volume_pressure",
        # Microstructure
        "spread",
        "spread_pct",
        "high_low_ratio",
        "close_position",
        "upper_shadow",
        "lower_shadow",
        # Pattern Recognition
        "higher_high",
        "lower_low",
        "inside_bar",
        "outside_bar",
        "bullish_engulfing",
        "bearish_engulfing",
        "hammer",
        "shooting_star",
        "doji",
        # Market Regime
        "trend_strength",
        "trend_direction",
        "regime_sma_20",
        "regime_ema_20",
        # Support/Resistance
        "distance_to_resistance",
        "distance_to_support",
        "pivot_point",
        "r1",
        "r2",
        "s1",
        "s2",
        # Advanced
        "hurst_exponent",
        "fractal_dimension",
        "entropy_10",
        "entropy_20",
        "autocorr_1",
        "autocorr_5",
        "autocorr_10",
    ]

    print(f"Базовых признаков в v4.0: {len(expected_features)}")

    # Для полного набора должно быть 240 признаков с учетом лагов и дополнительных
    print("\n⚠️ ВАЖНО: Модель обучена на 240 признаках")
    print("Это включает:")
    print("  - Базовые признаки (~100)")
    print("  - Лаговые признаки (lag_1, lag_2, lag_3)")
    print("  - Rolling статистики")
    print("  - Interaction features")

    # 4. Проверка реальных данных
    print("\n📊 ПРОВЕРКА НА РЕАЛЬНЫХ ДАННЫХ:")

    from database.connections.postgres import AsyncPGPool

    # Получаем реальные данные
    candles = await AsyncPGPool.fetch(
        """
        SELECT timestamp, open, high, low, close, volume
        FROM raw_market_data
        WHERE symbol = 'BTCUSDT'
        AND timestamp > NOW() - INTERVAL '2 days'
        ORDER BY timestamp DESC
        LIMIT 200
    """
    )

    if len(candles) >= 100:
        df_real = pd.DataFrame(candles)
        df_real = df_real.sort_values("timestamp")
        df_real["symbol"] = "BTCUSDT"

        # Генерируем признаки для реальных данных
        features_real = feature_engineer.create_features(df_real)

        if isinstance(features_real, pd.DataFrame):
            numeric_cols = features_real.select_dtypes(include=[np.number]).columns
            feature_cols = [
                col
                for col in numeric_cols
                if not col.startswith(("future_", "direction_", "profit_"))
                and col not in ["id", "timestamp", "datetime", "symbol"]
            ]

            print(f"Признаков из реальных данных: {len(feature_cols)}")

            # Берем последние 96 строк
            if len(features_real) >= 96:
                features_array = features_real[feature_cols].iloc[-96:].values

                # Проверяем форму
                print(f"Форма массива признаков: {features_array.shape}")
                print("Ожидаемая форма: (96, 240)")

                # Если не хватает признаков, дополняем
                if features_array.shape[1] < 240:
                    print(f"⚠️ Не хватает {240 - features_array.shape[1]} признаков")
                    print("Дополняем нулями...")
                    padding = np.zeros((96, 240 - features_array.shape[1]))
                    features_array = np.hstack([features_array, padding])
                elif features_array.shape[1] > 240:
                    print(f"⚠️ Лишние {features_array.shape[1] - 240} признаков")
                    print("Обрезаем до 240...")
                    features_array = features_array[:, :240]

                # Нормализуем
                try:
                    features_normalized = scaler.transform(features_array)
                    print("\n✅ Нормализация успешна")
                    print("После нормализации:")
                    print(f"  Mean: {features_normalized.mean():.4f}")
                    print(f"  Std: {features_normalized.std():.4f}")
                    print(f"  Min: {features_normalized.min():.4f}")
                    print(f"  Max: {features_normalized.max():.4f}")

                    # Проверка на NaN/Inf
                    nan_count = np.isnan(features_normalized).sum()
                    inf_count = np.isinf(features_normalized).sum()
                    if nan_count > 0:
                        print(f"  ⚠️ NaN значений: {nan_count}")
                    if inf_count > 0:
                        print(f"  ⚠️ Inf значений: {inf_count}")

                except Exception as e:
                    print(f"❌ Ошибка нормализации: {e}")

    await AsyncPGPool.close()

    print("\n" + "=" * 70)
    print("📝 ИТОГОВЫЕ РЕКОМЕНДАЦИИ:")
    print("=" * 70)
    print(
        """
ПРОБЛЕМА: Несоответствие признаков между обучением и интеграцией

РЕШЕНИЕ:
1. Скопировать feature_engineering.py из проекта обучения
2. Убедиться что генерируется ровно 240 признаков
3. Использовать тот же порядок признаков
4. Проверить версии библиотек (pandas, numpy, ta)

АЛЬТЕРНАТИВА:
Если не удается восстановить точные признаки, нужно переобучить модель
с текущим feature_engineering из BOT_AI_V3
    """
    )


if __name__ == "__main__":
    asyncio.run(compare_features())
