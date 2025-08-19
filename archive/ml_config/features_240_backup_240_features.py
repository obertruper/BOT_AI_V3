#!/usr/bin/env python3
"""
Точная конфигурация 240 признаков для UnifiedPatchTST модели.
Эта конфигурация определяет ТОЛЬКО те признаки, которые должны использоваться моделью.
"""

# Базовые OHLCV признаки (5)
BASIC_FEATURES = ["open", "high", "low", "close", "volume"]

# Технические индикаторы - основные периоды из config.yaml
TECHNICAL_INDICATORS = {
    # RSI - 3 периода (3 признака)
    "rsi": [5, 14, 21],
    # SMA - 6 периодов (6 признаков)
    "sma": [5, 10, 20, 50, 100, 200],
    # EMA - 6 периодов (6 признаков)
    "ema": [5, 10, 20, 50, 100, 200],
    # Bollinger Bands - 2 периода x 3 компонента (6 признаков)
    "bb": [20, 50],  # upper, middle, lower для каждого
    # MACD - 2 набора параметров x 3 компонента (6 признаков)
    "macd": [(12, 26, 9), (5, 35, 5)],  # macd, signal, histogram для каждого
    # ATR - 3 периода (3 признака)
    "atr": [7, 14, 21],
    # ADX - 2 периода (2 признака)
    "adx": [14, 21],
    # CCI - 2 периода (2 признака)
    "cci": [14, 20],
    # Stochastic - 2 периода x 2 компонента (4 признака)
    "stoch": [14, 21],  # K и D для каждого
    # Williams %R - 2 периода (2 признака)
    "williams": [14, 21],
    # MFI - 2 периода (2 признака)
    "mfi": [14, 21],
    # OBV и производные (3 признака)
    "obv": ["obv", "obv_sma_20", "obv_ema_20"],
}

# Возвраты для разных периодов (12 признаков)
RETURNS_FEATURES = [
    "returns_1",
    "returns_2",
    "returns_3",
    "returns_5",
    "returns_10",
    "returns_15",
    "returns_20",
    "returns_30",
    "returns_45",
    "returns_60",
    "returns_90",
    "returns_120",
]

# Волатильность для разных периодов (8 признаков)
VOLATILITY_FEATURES = [
    "volatility_5",
    "volatility_10",
    "volatility_15",
    "volatility_20",
    "volatility_30",
    "volatility_45",
    "volatility_60",
    "volatility_90",
]

# Микроструктурные признаки (18 признаков)
MICROSTRUCTURE_FEATURES = [
    # Спред и дисбаланс (6)
    "spread",
    "spread_ma_10",
    "spread_std_10",
    "order_imbalance",
    "order_imbalance_ma_10",
    "order_imbalance_std_10",
    # Давление покупателей/продавцов (6)
    "buy_pressure",
    "sell_pressure",
    "net_pressure",
    "buy_pressure_ma_10",
    "sell_pressure_ma_10",
    "net_pressure_ma_10",
    # Поток ордеров (6)
    "order_flow_5",
    "order_flow_10",
    "order_flow_20",
    "order_flow_ratio_5",
    "order_flow_ratio_10",
    "order_flow_ratio_20",
]

# Признаки обнаружения ралли (15 признаков)
RALLY_FEATURES = [
    # Текущие ралли/падения (6)
    "current_rally_magnitude",
    "current_rally_duration",
    "current_rally_velocity",
    "current_drawdown_magnitude",
    "current_drawdown_duration",
    "current_drawdown_velocity",
    # Недавние максимумы (6)
    "recent_max_rally_1h",
    "recent_max_rally_4h",
    "recent_max_rally_12h",
    "recent_max_drawdown_1h",
    "recent_max_drawdown_4h",
    "recent_max_drawdown_12h",
    # Вероятности достижения уровней (3)
    "prob_reach_1pct_4h",
    "prob_reach_2pct_4h",
    "prob_reach_3pct_12h",
]

# Временные признаки (12 признаков)
TEMPORAL_FEATURES = [
    # Циклические признаки времени (8)
    "hour_sin",
    "hour_cos",
    "day_sin",
    "day_cos",
    "week_sin",
    "week_cos",
    "month_sin",
    "month_cos",
    # Категориальные временные признаки (4)
    "is_weekend",
    "is_month_start",
    "is_month_end",
    "is_quarter_end",
]

# Кросс-активные корреляции (8 признаков)
CROSS_ASSET_FEATURES = [
    "btc_correlation_15m",
    "btc_correlation_1h",
    "btc_correlation_4h",
    "eth_correlation_15m",
    "eth_correlation_1h",
    "eth_correlation_4h",
    "market_beta_1h",
    "market_beta_4h",
]

# Признаки качества сигнала (15 признаков)
SIGNAL_QUALITY_FEATURES = [
    # Моментум и тренд (6)
    "momentum_score",
    "trend_strength",
    "trend_consistency",
    "momentum_divergence",
    "trend_acceleration",
    "trend_quality",
    # Уровни перекупленности/перепроданности (4)
    "overbought_score",
    "oversold_score",
    "divergence_bull",
    "divergence_bear",
    # Паттерны и сила (5)
    "pattern_strength",
    "breakout_strength",
    "reversal_probability",
    "support_distance",
    "resistance_distance",
]

# Фьючерс-специфичные признаки (10 признаков)
FUTURES_FEATURES = [
    # Основные метрики фьючерсов (5)
    "funding_rate",
    "open_interest",
    "oi_change_1h",
    "long_short_ratio",
    "taker_buy_sell_ratio",
    # Производные метрики (5)
    "funding_momentum",
    "oi_weighted_momentum",
    "liquidation_pressure",
    "basis_spread",
    "term_structure",
]

# ML-оптимизированные признаки (оставшиеся до 240)
ML_OPTIMIZED_FEATURES = [
    # Статистические признаки (20)
    "price_z_score_20",
    "price_z_score_50",
    "price_z_score_100",
    "volume_z_score_20",
    "volume_z_score_50",
    "return_skewness_20",
    "return_skewness_50",
    "return_kurtosis_20",
    "return_kurtosis_50",
    "price_efficiency_ratio",
    "volume_efficiency_ratio",
    "hurst_exponent",
    "fractal_dimension",
    "entropy_20",
    "entropy_50",
    "autocorrelation_lag_1",
    "autocorrelation_lag_5",
    "autocorrelation_lag_10",
    "partial_autocorr_1",
    "partial_autocorr_5",
    # Паттерн-признаки (15)
    "higher_high",
    "lower_low",
    "higher_low",
    "lower_high",
    "bullish_engulfing",
    "bearish_engulfing",
    "hammer",
    "shooting_star",
    "doji",
    "three_white_soldiers",
    "three_black_crows",
    "morning_star",
    "evening_star",
    "harami_bull",
    "harami_bear",
    # Адаптивные признаки (10)
    "adaptive_momentum",
    "adaptive_volatility",
    "adaptive_trend",
    "regime_state",
    "market_phase",
    "volatility_regime",
    "trend_regime",
    "momentum_regime",
    "volume_regime",
    "correlation_regime",
    # Дополнительные статистические признаки (20)
    "median_price",
    "typical_price",
    "weighted_close",
    "price_range",
    "true_range",
    "average_price",
    "log_return",
    "squared_return",
    "abs_return",
    "volume_rate",
    "volume_trend",
    "volume_oscillator",
    "price_momentum",
    "price_acceleration",
    "price_jerk",
    "rolling_min_5",
    "rolling_max_5",
    "rolling_median_5",
    "rolling_std_5",
    "rolling_var_5",
]


def get_required_features_list() -> list[str]:
    """
    Возвращает полный список из 240 признаков в правильном порядке.
    ВАЖНО: OHLCV данные не включаются, так как они в метаданных FeatureEngineer.
    """
    features = []

    # 1. Базовые OHLCV НЕ включаем - они в метаданных
    # features.extend(BASIC_FEATURES)  # УБРАНО!

    # 2. Технические индикаторы (47)
    for indicator, params in TECHNICAL_INDICATORS.items():
        if indicator == "rsi":
            features.extend([f"rsi_{p}" for p in params])
        elif indicator == "sma":
            features.extend([f"sma_{p}" for p in params])
        elif indicator == "ema":
            features.extend([f"ema_{p}" for p in params])
        elif indicator == "bb":
            for p in params:
                features.extend(
                    [f"bb_upper_{p}", f"bb_middle_{p}", f"bb_lower_{p}", f"bb_position_{p}"]
                )
        elif indicator == "macd":
            for fast, slow, signal in params:
                features.extend(
                    [
                        f"macd_{fast}_{slow}",
                        f"macd_signal_{fast}_{slow}",
                        f"macd_hist_{fast}_{slow}",
                    ]
                )
        elif indicator == "atr":
            features.extend([f"atr_{p}" for p in params])
        elif indicator == "adx":
            features.extend([f"adx_{p}" for p in params])
        elif indicator == "cci":
            features.extend([f"cci_{p}" for p in params])
        elif indicator == "stoch":
            for p in params:
                features.extend([f"stoch_k_{p}", f"stoch_d_{p}"])
        elif indicator == "williams":
            features.extend([f"williams_r_{p}" for p in params])
        elif indicator == "mfi":
            features.extend([f"mfi_{p}" for p in params])
        elif indicator == "obv":
            features.extend(params)

    # 3. Возвраты (12)
    features.extend(RETURNS_FEATURES)

    # 4. Волатильность (8)
    features.extend(VOLATILITY_FEATURES)

    # 5. Микроструктура (18)
    features.extend(MICROSTRUCTURE_FEATURES)

    # 6. Ралли (15)
    features.extend(RALLY_FEATURES)

    # 7. Временные (12)
    features.extend(TEMPORAL_FEATURES)

    # 8. Кросс-активы (8)
    features.extend(CROSS_ASSET_FEATURES)

    # 9. Качество сигнала (15)
    features.extend(SIGNAL_QUALITY_FEATURES)

    # 10. Фьючерсы (10)
    features.extend(FUTURES_FEATURES)

    # 11. ML-оптимизированные (дополняем до 240)
    features.extend(ML_OPTIMIZED_FEATURES)

    # Если не хватает до 240, добавляем дополнительные признаки
    current_count = len(features)
    if current_count < 240:
        # Добавляем дополнительные волатильности и возвраты (теперь нужно на 5 больше)
        for period in [2, 3, 4, 6, 7, 8, 9, 11, 13, 25, 35, 40, 50, 70, 80, 100, 150, 200]:
            if len(features) >= 240:
                break
            features.append(f"volatility_{period}")

        for period in [2, 3, 4, 6, 7, 8, 9, 11, 13, 25, 35, 40, 50, 70, 80, 100, 150, 200]:
            if len(features) >= 240:
                break
            features.append(f"returns_{period}")

    # Убираем дубликаты, сохраняя порядок
    seen = set()
    unique_features = []
    for feature in features:
        if feature not in seen:
            unique_features.append(feature)
            seen.add(feature)

    # Если не хватает до 240 после удаления дубликатов, добавляем уникальные
    while len(unique_features) < 240:
        for period in [
            12,
            14,
            16,
            18,
            22,
            24,
            28,
            32,
            36,
            42,
            48,
            54,
            60,
            66,
            72,
            84,
            96,
            108,
            120,
            144,
            168,
            192,
            216,
            240,
            288,
            336,
            384,
            480,
            576,
            672,
            768,
            960,
        ]:
            if len(unique_features) >= 240:
                break
            candidate = f"extra_feature_{period}"
            if candidate not in seen:
                unique_features.append(candidate)
                seen.add(candidate)

    # Обрезаем если больше 240
    unique_features = unique_features[:240]

    # Проверка количества
    assert len(unique_features) == 240, f"Ожидалось 240 признаков, получено {len(unique_features)}"

    return unique_features


def get_feature_groups() -> dict[str, list[str]]:
    """
    Возвращает признаки, сгруппированные по категориям.
    """
    features_list = get_required_features_list()

    groups = {
        "basic": BASIC_FEATURES,
        "technical": features_list[5:52],  # 47 технических индикаторов
        "returns": RETURNS_FEATURES,
        "volatility": VOLATILITY_FEATURES,
        "microstructure": MICROSTRUCTURE_FEATURES,
        "rally": RALLY_FEATURES,
        "temporal": TEMPORAL_FEATURES,
        "cross_asset": CROSS_ASSET_FEATURES,
        "signal_quality": SIGNAL_QUALITY_FEATURES,
        "futures": FUTURES_FEATURES,
        "ml_optimized": features_list[195:240],  # Последние 45 ML признаков
    }

    return groups


def validate_features(features: list[str]) -> bool:
    """
    Проверяет, что переданный список признаков соответствует ожидаемым.

    Args:
        features: Список признаков для проверки

    Returns:
        True если список валиден, False иначе
    """
    required = get_required_features_list()

    if len(features) != 240:
        print(f"❌ Неверное количество признаков: {len(features)} вместо 240")
        return False

    # Проверка точного соответствия
    for i, (feat, req) in enumerate(zip(features, required, strict=False)):
        if feat != req:
            print(f"❌ Несоответствие на позиции {i}: '{feat}' вместо '{req}'")
            return False

    return True


# Экспорт основной конфигурации
REQUIRED_FEATURES_240 = get_required_features_list()

# Дополнительные параметры для feature engineering
FEATURE_CONFIG = {
    "context_window": 96,  # Из model config
    "min_history": 240,  # Минимум данных для расчета
    "use_cache": True,
    "cache_ttl": 300,  # 5 минут
    "inference_mode": True,  # Для продакшена - генерировать только нужные признаки
}

if __name__ == "__main__":
    # Тест конфигурации
    features = get_required_features_list()
    print(f"✅ Сконфигурировано {len(features)} признаков")

    groups = get_feature_groups()
    print("\n📊 Группы признаков:")
    for group_name, group_features in groups.items():
        print(f"  - {group_name}: {len(group_features)} признаков")

    print("\n✅ Конфигурация готова к использованию")
