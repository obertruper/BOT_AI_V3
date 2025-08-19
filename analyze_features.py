#!/usr/bin/env python3
"""
Анализ почему признаки имеют нулевую дисперсию
"""

import asyncio
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))


async def analyze_features():
    """Детальный анализ проблем с признаками"""

    print("=" * 80)
    print("🔍 АНАЛИЗ ПРОБЛЕМ С ПРИЗНАКАМИ")
    print("=" * 80)

    from core.config.config_manager import ConfigManager
    from database.connections.postgres import AsyncPGPool
    from ml.logic.archive_old_versions.feature_engineering import FeatureEngineer

    # Получаем данные
    candles = await AsyncPGPool.fetch(
        """
        SELECT timestamp, open, high, low, close, volume
        FROM raw_market_data
        WHERE symbol = 'BTCUSDT'
        ORDER BY timestamp DESC
        LIMIT 300
    """
    )

    df = pd.DataFrame([dict(row) for row in candles])
    df = df.sort_values("timestamp")

    # Конвертируем в правильные типы
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    print(f"✅ Загружено {len(df)} свечей")
    print(
        f"   Данные: min={df['close'].min():.2f}, max={df['close'].max():.2f}, std={df['close'].std():.2f}"
    )

    # Добавляем необходимые колонки
    df["symbol"] = "BTCUSDT"
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")

    # Создаем feature engineer
    config_manager = ConfigManager()
    config = {
        "ml": config_manager.get_ml_config(),
        "system": config_manager.get_system_config(),
        "trading": config_manager.get_config("trading", {}),
    }

    fe = FeatureEngineer(config)

    # Генерируем признаки
    print("\n📊 Генерация признаков...")
    features = fe.create_features(df)

    if features is None:
        print("❌ Ошибка генерации признаков!")
        return

    print(f"✅ Сгенерировано {features.shape[1]} признаков")

    # Анализ дисперсии
    if isinstance(features, pd.DataFrame):
        features_np = features.values.astype(np.float64)
        columns = features.columns
    else:
        features_np = features.astype(np.float64)
        columns = [f"feature_{i}" for i in range(features.shape[1])]

    std_by_col = np.std(features_np, axis=0)

    # Классификация признаков
    zero_var_mask = std_by_col < 1e-6
    low_var_mask = (std_by_col >= 1e-6) & (std_by_col < 0.01)
    normal_var_mask = std_by_col >= 0.01

    zero_var_count = zero_var_mask.sum()
    low_var_count = low_var_mask.sum()
    normal_var_count = normal_var_mask.sum()

    print("\n📊 СТАТИСТИКА ДИСПЕРСИИ:")
    print(f"   Нулевая дисперсия (< 1e-6): {zero_var_count}")
    print(f"   Низкая дисперсия (1e-6 - 0.01): {low_var_count}")
    print(f"   Нормальная дисперсия (>= 0.01): {normal_var_count}")

    # Анализ проблемных признаков
    if zero_var_count > 0:
        print(f"\n❌ ПРИЗНАКИ С НУЛЕВОЙ ДИСПЕРСИЕЙ ({zero_var_count}):")
        zero_var_indices = np.where(zero_var_mask)[0]

        # Группируем по типам
        price_features = []
        ma_features = []
        rsi_features = []
        bb_features = []
        macd_features = []
        volume_features = []
        other_features = []

        for idx in zero_var_indices:
            col_name = columns[idx]
            if "ma_" in col_name or "ema_" in col_name or "wma_" in col_name:
                ma_features.append(col_name)
            elif "rsi" in col_name:
                rsi_features.append(col_name)
            elif "bb_" in col_name:
                bb_features.append(col_name)
            elif "macd" in col_name:
                macd_features.append(col_name)
            elif "volume" in col_name or "vwap" in col_name:
                volume_features.append(col_name)
            elif any(x in col_name for x in ["open", "high", "low", "close", "price"]):
                price_features.append(col_name)
            else:
                other_features.append(col_name)

        if ma_features:
            print(f"\n   📉 Moving Averages ({len(ma_features)}):")
            for feat in ma_features[:5]:
                idx = columns.index(feat) if isinstance(columns, list) else columns.get_loc(feat)
                val = features_np[:, idx][0]
                print(f"      {feat}: все значения = {val:.6f}")

        if rsi_features:
            print(f"\n   📊 RSI ({len(rsi_features)}):")
            for feat in rsi_features[:5]:
                idx = columns.index(feat) if isinstance(columns, list) else columns.get_loc(feat)
                val = features_np[:, idx][0]
                print(f"      {feat}: все значения = {val:.6f}")

        if bb_features:
            print(f"\n   📈 Bollinger Bands ({len(bb_features)}):")
            for feat in bb_features[:5]:
                idx = columns.index(feat) if isinstance(columns, list) else columns.get_loc(feat)
                val = features_np[:, idx][0]
                print(f"      {feat}: все значения = {val:.6f}")

        if macd_features:
            print(f"\n   📊 MACD ({len(macd_features)}):")
            for feat in macd_features[:5]:
                idx = columns.index(feat) if isinstance(columns, list) else columns.get_loc(feat)
                val = features_np[:, idx][0]
                print(f"      {feat}: все значения = {val:.6f}")

        if other_features:
            print(f"\n   🔧 Другие ({len(other_features)}):")
            for feat in other_features[:10]:
                idx = columns.index(feat) if isinstance(columns, list) else columns.get_loc(feat)
                val = features_np[:, idx][0]
                print(f"      {feat}: все значения = {val:.6f}")

    # Проверяем нормальные признаки
    if normal_var_count > 0:
        print(f"\n✅ ПРИЗНАКИ С НОРМАЛЬНОЙ ДИСПЕРСИЕЙ ({normal_var_count}):")
        normal_indices = np.where(normal_var_mask)[0]
        for idx in normal_indices[:10]:
            col_name = columns[idx]
            col_std = std_by_col[idx]
            col_mean = np.mean(features_np[:, idx])
            print(f"   {col_name}: mean={col_mean:.3f}, std={col_std:.3f}")

    # Проверяем конкретные индикаторы вручную
    print("\n" + "=" * 80)
    print("🔬 ПРОВЕРКА ИНДИКАТОРОВ ВРУЧНУЮ")
    print("=" * 80)

    # RSI
    print("\n1. RSI (ручной расчет):")
    close_prices = df["close"].values
    deltas = np.diff(close_prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    period = 14
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    if avg_loss != 0:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        print(f"   RSI(14) = {rsi:.2f}")
    else:
        print("   RSI: avg_loss = 0, невозможно рассчитать")

    # SMA
    print("\n2. SMA (ручной расчет):")
    for period in [5, 10, 20]:
        sma = np.mean(close_prices[-period:])
        print(f"   SMA({period}) = {sma:.2f}")

    # Проверяем ta библиотеку
    print("\n3. Проверка библиотеки ta:")
    try:
        import ta

        # RSI через ta
        rsi_indicator = ta.momentum.RSIIndicator(close=pd.Series(close_prices), window=14)
        rsi_values = rsi_indicator.rsi()
        print(f"   ta.RSI: последние 5 значений = {rsi_values.tail().values}")

        # MACD через ta
        macd = ta.trend.MACD(close=pd.Series(close_prices))
        macd_line = macd.macd()
        print(f"   ta.MACD: последние 5 значений = {macd_line.tail().values}")

    except Exception as e:
        print(f"   ❌ Ошибка библиотеки ta: {e}")

    print("\n" + "=" * 80)
    print("💡 ВЫВОДЫ")
    print("=" * 80)

    if zero_var_count > 200:
        print(
            """
⚠️ КРИТИЧЕСКАЯ ПРОБЛЕМА: Большинство индикаторов не рассчитываются!

Возможные причины:
1. Недостаточно данных для расчета индикаторов (нужно минимум 200-250 свечей)
2. Ошибки в реализации расчета индикаторов
3. Проблемы с типами данных (Decimal vs float)
4. Библиотека ta возвращает NaN для большинства индикаторов

Рекомендации:
1. Проверить минимальное количество данных для каждого индикатора
2. Добавить обработку NaN значений
3. Использовать собственную реализацию критичных индикаторов
"""
        )
    else:
        print("✅ Feature engineering работает корректно")


if __name__ == "__main__":
    asyncio.run(analyze_features())
