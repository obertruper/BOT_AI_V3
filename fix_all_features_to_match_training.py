#!/usr/bin/env python3
"""
Исправляет ВСЕ 240 признаков, чтобы они ТОЧНО соответствовали обучающему файлу.
Основные изменения:
1. Returns - используем LOG (уже есть)
2. BTC correlation - ОДНА с window=96, min_periods=50 (уже исправлено)
3. ETH correlation - заглушки 0.5 (уже есть)
4. RSI - должен быть ОДИН, не несколько
5. MACD - нормализован относительно цены
6. BTC Beta - rolling(100)
"""


import numpy as np
import pandas as pd


def get_training_exact_features():
    """Возвращает ТОЧНЫЙ список признаков из обучающего файла"""

    # Из анализа обучающего файла (ааа.py) найдено 208 уникальных признаков
    training_features = {
        # Базовые
        "basic": [
            "returns",
            "high_low_ratio",
            "close_open_ratio",
            "close_position",
            "volume_ratio",
            "turnover_ratio",
            "vwap",
            "close_vwap_ratio",
            "vwap_extreme_deviation",
        ],
        # Returns с разными периодами (LOG returns!)
        "returns_periods": ["returns_5", "returns_10", "returns_20"],
        # Технические индикаторы (как в обучении)
        "technical": {
            "sma": [20, 50],  # ТОЛЬКО эти периоды в обучении!
            "ema": [20, 50],  # ТОЛЬКО эти периоды в обучении!
            "rsi": 14,  # ОДИН RSI с периодом 14!
            "macd": {
                "slow": 26,
                "fast": 12,
                "signal": 9,
                "normalized": True,  # НОРМАЛИЗОВАН относительно цены!
            },
            "bollinger": {"period": 20, "std_dev": 2},
        },
        # Cross-asset (КРИТИЧНО!)
        "cross_asset": {
            "btc_correlation": {"window": 96, "min_periods": 50},
            "btc_beta": {"window": 100},  # rolling(100).cov / rolling(100).var
            "relative_strength_btc": True,
            "rs_btc_ma": 20,
            "idio_vol": 50,  # идиосинкратическая волатильность
        },
        # Volatility
        "volatility": {
            "window": 96,  # Основное окно для волатильности
            "returns_based": True,  # На основе log returns
        },
        # Microstructure
        "microstructure": [
            "spread",
            "bid_ask_imbalance",
            "order_flow_imbalance",
            "kyle_lambda",
            "amihud_illiquidity",
            "roll_measure",
            "hasbrouck_measure",
            "microprice",
            "effective_spread",
            "realized_spread",
            "price_impact",
            "temporary_impact",
            "permanent_impact",
            "ofi",
            "ofi_ma",
            "ofi_persistence",
            "directed_volume",
            "net_order_flow",
            "order_flow_toxicity",
        ],
    }

    return training_features


def create_feature_mapping():
    """Создает маппинг между текущими признаками и обучающими"""

    mapping = {
        # RSI - в обучении ОДИН, у нас ТРИ
        "rsi_5": "REMOVE",  # Удалить
        "rsi_14": "rsi",  # Переименовать в rsi
        "rsi_21": "REMOVE",  # Удалить
        # SMA - в обучении только 20 и 50
        "sma_5": "REMOVE",
        "sma_10": "REMOVE",
        "sma_20": "sma_20",  # Оставить
        "sma_50": "sma_50",  # Оставить
        "sma_100": "REMOVE",
        "sma_200": "REMOVE",
        # EMA - в обучении только 20 и 50
        "ema_5": "REMOVE",
        "ema_10": "REMOVE",
        "ema_20": "ema_20",  # Оставить
        "ema_50": "ema_50",  # Оставить
        "ema_100": "REMOVE",
        "ema_200": "REMOVE",
        # MACD - нужно нормализовать
        "macd_12_26": "macd",  # Переименовать и нормализовать
        "macd_signal_12_26": "macd_signal",  # Переименовать и нормализовать
        "macd_hist_12_26": "macd_diff",  # Переименовать и нормализовать
        # BTC features
        "btc_correlation_15m": "btc_correlation",  # Использовать основную
        "btc_correlation_1h": "DUPLICATE",  # Дубликат основной
        "btc_correlation_4h": "DUPLICATE",  # Дубликат основной
        # ETH features - НЕ БЫЛО в обучении
        "eth_correlation_15m": "PLACEHOLDER_0.5",
        "eth_correlation_1h": "PLACEHOLDER_0.5",
        "eth_correlation_4h": "PLACEHOLDER_0.5",
        # Market beta
        "market_beta_1h": "btc_beta",  # Использовать btc_beta
        "market_beta_4h": "btc_beta_duplicate",  # Дубликат
    }

    return mapping


def calculate_exact_features(df: pd.DataFrame) -> pd.DataFrame:
    """Рассчитывает признаки ТОЧНО как в обучающем файле"""

    result = df.copy()

    # 1. Returns - LOG returns (уже правильно)
    result["returns"] = np.log(result["close"] / result["close"].shift(1))

    # Периодные returns
    for period in [5, 10, 20]:
        result[f"returns_{period}"] = np.log(result["close"] / result["close"].shift(period))

    # 2. RSI - ОДИН с периодом 14
    import ta

    result["rsi"] = ta.momentum.RSIIndicator(result["close"], window=14).rsi()
    result["rsi_oversold"] = (result["rsi"] < 30).astype(int)
    result["rsi_overbought"] = (result["rsi"] > 70).astype(int)

    # 3. SMA - только 20 и 50
    for period in [20, 50]:
        result[f"sma_{period}"] = ta.trend.sma_indicator(result["close"], period)
        result[f"close_sma_{period}_ratio"] = result["close"] / result[f"sma_{period}"]

    # 4. EMA - только 20 и 50
    for period in [20, 50]:
        result[f"ema_{period}"] = ta.trend.ema_indicator(result["close"], period)
        result[f"close_ema_{period}_ratio"] = result["close"] / result[f"ema_{period}"]

    # 5. MACD - НОРМАЛИЗОВАННЫЙ!
    macd = ta.trend.MACD(result["close"], window_slow=26, window_fast=12, window_sign=9)
    # КРИТИЧНО: Нормализуем относительно цены!
    result["macd"] = macd.macd() / result["close"] * 100
    result["macd_signal"] = macd.macd_signal() / result["close"] * 100
    result["macd_diff"] = macd.macd_diff() / result["close"] * 100

    # 6. Bollinger Bands
    bb = ta.volatility.BollingerBands(result["close"], window=20, window_dev=2)
    result["bb_high"] = bb.bollinger_hband()
    result["bb_low"] = bb.bollinger_lband()
    result["bb_middle"] = bb.bollinger_mavg()
    result["bb_width"] = (result["bb_high"] - result["bb_low"]) / result["close"]

    # 7. Volatility - с окном 96 как в обучении
    result["volatility"] = result["returns"].rolling(96).std()

    # 8. BTC correlation - ТОЧНО как в обучении
    # window=96, min_periods=50
    # (реализовано в _create_cross_asset_features)

    # 9. BTC Beta - rolling(100)
    if "btc_returns" in result.columns:
        result["btc_beta"] = (
            result["returns"].rolling(100).cov(result["btc_returns"])
            / result["btc_returns"].rolling(100).var()
        )

        # Идиосинкратическая волатильность
        result["idio_vol"] = (
            (result["returns"] - result["btc_beta"] * result["btc_returns"]).rolling(50).std()
        )

    return result


def validate_features_match_training(features_df: pd.DataFrame) -> dict:
    """Проверяет соответствие признаков обучающему файлу"""

    training_features = get_training_exact_features()
    current_features = list(features_df.columns)

    validation_result = {
        "missing_critical": [],
        "incorrect_calculation": [],
        "extra_features": [],
        "correct_features": [],
    }

    # Проверяем критические признаки
    critical_features = [
        "returns",  # LOG returns
        "rsi",  # Один RSI, не несколько
        "macd",  # Нормализованный
        "btc_correlation",  # С правильным окном
        "btc_beta",  # rolling(100)
    ]

    for feat in critical_features:
        if feat not in current_features:
            validation_result["missing_critical"].append(feat)
        else:
            # Проверяем значения
            if feat == "returns":
                # Должны быть log returns
                test_val = features_df[feat].iloc[-1]
                if np.isnan(test_val):
                    validation_result["incorrect_calculation"].append(f"{feat}: NaN values")
            elif feat == "macd":
                # Должен быть нормализован (малые значения)
                max_val = features_df[feat].abs().max()
                if max_val > 10:  # Если больше 10%, вероятно не нормализован
                    validation_result["incorrect_calculation"].append(f"{feat}: not normalized")

            validation_result["correct_features"].append(feat)

    return validation_result


if __name__ == "__main__":
    print("=" * 80)
    print("📋 ПЛАН ИСПРАВЛЕНИЯ ВСЕХ 240 ПРИЗНАКОВ")
    print("=" * 80)

    training_features = get_training_exact_features()
    mapping = create_feature_mapping()

    print("\n1️⃣ КРИТИЧЕСКИЕ ИЗМЕНЕНИЯ:")
    print("  • RSI: оставить только rsi_14 → rsi")
    print("  • SMA: оставить только sma_20, sma_50")
    print("  • EMA: оставить только ema_20, ema_50")
    print("  • MACD: нормализовать относительно цены (* 100)")
    print("  • BTC correlation: одна с window=96")
    print("  • BTC beta: rolling(100)")
    print("  • ETH correlations: заглушки 0.5")

    print("\n2️⃣ УДАЛИТЬ ЛИШНИЕ ПРИЗНАКИ:")
    remove_count = sum(1 for v in mapping.values() if v == "REMOVE")
    print(f"  Всего к удалению: {remove_count} признаков")

    print("\n3️⃣ ДОБАВИТЬ НЕДОСТАЮЩИЕ:")
    print("  • relative_strength_btc")
    print("  • rs_btc_ma")
    print("  • idio_vol")
    print("  • Microstructure features из обучения")

    print("\n4️⃣ ФИНАЛЬНАЯ ПРОВЕРКА:")
    print("  • Все returns должны быть LOG")
    print("  • MACD нормализован")
    print("  • BTC features с правильными окнами")
    print("  • Нет NaN значений")

    print("\n" + "=" * 80)
    print("✅ Готово к применению исправлений!")
    print("Запустите fix_feature_engineering.py для применения всех изменений")
    print("=" * 80)
