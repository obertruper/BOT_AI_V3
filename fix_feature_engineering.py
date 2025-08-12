#!/usr/bin/env python3
"""
Исправление feature engineering - устранение нулевой дисперсии
"""

import asyncio
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))


async def fix_features():
    """Анализ и исправление проблем с признаками"""

    print("=" * 80)
    print("🔧 ИСПРАВЛЕНИЕ FEATURE ENGINEERING")
    print("=" * 80)

    from database.connections.postgres import AsyncPGPool

    # Получаем свежие данные
    candles = await AsyncPGPool.fetch(
        """
        SELECT timestamp, open, high, low, close, volume
        FROM raw_market_data
        WHERE symbol = 'BTCUSDT'
        ORDER BY timestamp DESC
        LIMIT 200
    """
    )

    df = pd.DataFrame([dict(row) for row in candles])
    df = df.sort_values("timestamp")

    # Конвертируем в правильные типы
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    print(f"✅ Загружено {len(df)} свечей")
    print(f"   Типы данных: {df.dtypes.to_dict()}")

    # Тестируем проблемные индикаторы
    print("\n📊 Тестирование индикаторов:")

    # 1. Log returns - проблема с типами
    print("\n1. Log Returns:")
    try:
        close_prices = df["close"].astype(float)
        log_returns_1 = np.log(close_prices / close_prices.shift(1))
        print(
            f"   ✅ log_returns_1: min={log_returns_1.min():.6f}, max={log_returns_1.max():.6f}, std={log_returns_1.std():.6f}"
        )
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

    # 2. SMA - должны иметь дисперсию
    print("\n2. Simple Moving Averages:")
    for period in [5, 10, 20]:
        sma = df["close"].rolling(window=period).mean()
        print(f"   SMA_{period}: std={sma.std():.2f}, последнее={sma.iloc[-1]:.2f}")

    # 3. RSI
    print("\n3. RSI:")
    try:
        import ta

        rsi = ta.momentum.RSIIndicator(close=df["close"], window=14).rsi()
        print(f"   RSI: min={rsi.min():.2f}, max={rsi.max():.2f}, std={rsi.std():.2f}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

    # 4. MACD
    print("\n4. MACD:")
    try:
        macd = ta.trend.MACD(close=df["close"])
        macd_line = macd.macd()
        signal_line = macd.macd_signal()
        macd_diff = macd.macd_diff()
        print(f"   MACD: std={macd_line.std():.2f}")
        print(f"   Signal: std={signal_line.std():.2f}")
        print(f"   Histogram: std={macd_diff.std():.2f}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

    # 5. Bollinger Bands
    print("\n5. Bollinger Bands:")
    try:
        bb = ta.volatility.BollingerBands(close=df["close"], window=20, window_dev=2)
        bb_upper = bb.bollinger_hband()
        bb_lower = bb.bollinger_lband()
        bb_width = bb_upper - bb_lower
        print(f"   BB Width: std={bb_width.std():.2f}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

    # Теперь проверим полный feature engineering
    print("\n" + "=" * 80)
    print("📊 ПОЛНЫЙ АНАЛИЗ FEATURE ENGINEERING")
    print("=" * 80)

    from core.config.config_manager import ConfigManager
    from ml.logic.feature_engineering_training import FeatureEngineer

    config_manager = ConfigManager()
    config = {
        "ml": config_manager.get_ml_config(),
        "system": config_manager.get_system_config(),
        "trading": config_manager.get_config("trading", {}),
    }

    fe = FeatureEngineer(config)

    # Добавляем колонку symbol
    df["symbol"] = "BTCUSDT"

    # Создаем признаки
    features = fe.create_features(df)

    if features is not None and len(features) > 0:
        print(f"\n✅ Создано {features.shape[1]} признаков")

        # Анализ дисперсии
        features_np = features.values.astype(np.float64)
        std_by_col = np.std(features_np, axis=0)

        zero_var_mask = std_by_col < 1e-6
        zero_var_count = zero_var_mask.sum()

        print("\n📊 Статистика признаков:")
        print(f"   Всего признаков: {len(std_by_col)}")
        print(f"   С нулевой дисперсией: {zero_var_count}")
        print(f"   С нормальной дисперсией: {len(std_by_col) - zero_var_count}")

        if zero_var_count > 0:
            print("\n⚠️ Признаки с нулевой дисперсией:")
            zero_var_indices = np.where(zero_var_mask)[0]
            for i in zero_var_indices[:20]:  # Первые 20
                col_name = features.columns[i]
                col_values = features_np[:, i]
                print(f"   {col_name}: все значения = {col_values[0]:.6f}")

        # Проверяем ненулевые
        nonzero_var_indices = np.where(~zero_var_mask)[0]
        if len(nonzero_var_indices) > 0:
            print("\n✅ Признаки с нормальной дисперсией:")
            for i in nonzero_var_indices[:10]:  # Первые 10
                col_name = features.columns[i]
                col_std = std_by_col[i]
                print(f"   {col_name}: std = {col_std:.6f}")

    print("\n" + "=" * 80)
    print("💡 РЕКОМЕНДАЦИИ")
    print("=" * 80)

    print(
        """
Основная проблема: большинство технических индикаторов возвращают константы.

Возможные причины:
1. Недостаточно данных для расчета индикаторов
2. Ошибки в библиотеке ta
3. Проблемы с типами данных (Decimal vs float)

Решение:
1. Убедиться что данные правильного типа (float64)
2. Проверить что достаточно исторических данных
3. Исправить расчет индикаторов
"""
    )


if __name__ == "__main__":
    asyncio.run(fix_features())
