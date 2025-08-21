#!/usr/bin/env python3
"""
Реальная конфигурация 240 признаков для UnifiedPatchTST модели.
Основано на анализе feature_engineering_production.py который генерирует 268 признаков.
Используем первые 240 наиболее важных.
"""

# Список 240 реальных признаков, генерируемых feature_engineering_production.py
PRODUCTION_FEATURES_240 = [
    # 1. Базовые OHLCV (6)
    "open", "high", "low", "close", "volume", "turnover",
    
    # 2. Returns и ratios (10)
    "returns", "returns_5", "returns_10", "returns_20",
    "high_low_ratio", "close_open_ratio", "close_position",
    "volume_ratio", "turnover_ratio", "log_returns",
    
    # 3. VWAP и price metrics (5)
    "vwap", "close_vwap_ratio", "vwap_extreme_deviation",
    "hl_spread", "hl_spread_ma",
    
    # 4. Moving Averages SMA (15)
    "sma_5", "close_sma_5_ratio", "sma_cross_5_20",
    "sma_10", "close_sma_10_ratio", "sma_cross_10_50",
    "sma_20", "close_sma_20_ratio", "sma_cross_20_50",
    "sma_50", "close_sma_50_ratio", "sma_cross_50_200",
    "sma_100", "close_sma_100_ratio",
    "sma_200", "close_sma_200_ratio",
    
    # 5. Moving Averages EMA (10)
    "ema_5", "close_ema_5_ratio",
    "ema_12", "close_ema_12_ratio",
    "ema_20", "close_ema_20_ratio",
    "ema_26", "close_ema_26_ratio",
    "ema_50", "close_ema_50_ratio",
    
    # 6. RSI indicators (8)
    "rsi", "rsi_oversold", "rsi_overbought",
    "rsi_14", "rsi_21", "rsi_30",
    "rsi_divergence_bullish", "rsi_divergence_bearish",
    
    # 7. MACD indicators (6)
    "macd", "macd_signal", "macd_diff",
    "macd_cross_up", "macd_cross_down", "macd_histogram",
    
    # 8. Bollinger Bands (10)
    "bb_upper", "bb_middle", "bb_lower", "bb_width", "bb_position",
    "bb_squeeze", "bb_breakout_upper", "bb_breakout_lower",
    "bb_breakout_strength", "bb_squeeze_duration",
    
    # 9. ATR and volatility (8)
    "atr", "atr_pct", "atr_14", "atr_21",
    "volatility_10", "volatility_20", "volatility_30",
    "volatility_regime",
    
    # 10. Stochastic (5)
    "stoch_k", "stoch_d", "stoch_oversold", "stoch_overbought",
    "stoch_cross",
    
    # 11. Volume indicators (10)
    "obv", "obv_normalized", "obv_ema", "obv_divergence", "obv_trend",
    "mfi", "mfi_oversold", "mfi_overbought",
    "cmf", "accumulation_distribution",
    
    # 12. Trend indicators (10)
    "adx", "adx_pos", "adx_neg", "adxr",
    "psar", "psar_trend", "psar_distance", "psar_distance_normalized",
    "aroon_up", "aroon_down",
    
    # 13. Oscillators (8)
    "cci", "cci_oversold", "cci_overbought",
    "williams_r", "ultimate_oscillator",
    "roc", "trix", "kama",
    
    # 14. Ichimoku (6)
    "ichimoku_conversion", "ichimoku_base",
    "ichimoku_span_a", "ichimoku_span_b",
    "ichimoku_cloud_thickness", "price_vs_cloud",
    
    # 15. Channels (8)
    "keltner_upper", "keltner_middle", "keltner_lower", "keltner_position",
    "donchian_upper", "donchian_middle", "donchian_lower", "donchian_breakout",
    
    # 16. Microstructure (15)
    "price_direction", "directed_volume", "volume_imbalance",
    "order_flow_imbalance", "ofi_persistence",
    "amihud_illiquidity", "amihud_ma",
    "kyle_lambda", "price_impact", "price_impact_log",
    "toxicity", "liquidity_score", "liquidity_rank",
    "volume_spike", "volume_spike_magnitude",
    
    # 17. Rally detection (12)
    "momentum_1h", "momentum_4h", "momentum_24h", "momentum_acceleration",
    "trend_1h", "trend_1h_strength",
    "trend_4h", "trend_4h_strength",
    "near_daily_high", "near_daily_low",
    "rally_strength", "rally_duration",
    
    # 18. Signal quality (10)
    "signal_strength", "signal_consistency",
    "indicators_consensus_long", "indicators_consensus_short",
    "indicators_count_long", "indicators_count_short",
    "divergence_count", "confirmation_score",
    "entry_quality", "risk_reward_ratio",
    
    # 19. Futures specific (14)
    "long_liquidation_price", "short_liquidation_price",
    "long_liquidation_distance_pct", "short_liquidation_distance_pct",
    "long_liquidation_risk", "short_liquidation_risk",
    "current_leverage", "optimal_leverage", "safe_leverage",
    "cascade_risk", "funding_proxy",
    "long_holding_cost_daily", "short_holding_cost_daily",
    "var_95",
    
    # 20. ML optimized features (15)
    "hurst_exponent", "fractal_dimension",
    "efficiency_ratio", "trend_quality",
    "realized_vol", "realized_vol_5m", "realized_vol_15m", "realized_vol_1h",
    "realized_vol_daily", "realized_vol_annual",
    "garch_vol", "vol_regime",
    "return_entropy", "returns_ac_1", "returns_ac_5",
    
    # 21. Temporal features (13)
    "hour", "minute", "dayofweek", "day", "month",
    "hour_sin", "hour_cos",
    "dow_sin", "dow_cos",
    "month_sin", "month_cos",
    "is_weekend", "session_overlap",
    
    # 22. Cross-asset features (10)
    "btc_correlation", "btc_beta", "idio_vol",
    "relative_strength_btc", "rs_btc_ma",
    "sector_returns", "relative_to_sector",
    "is_momentum_leader", "market_regime", "correlation_cluster",
    
    # 23. Statistical features (15)
    "rolling_mean_5", "rolling_mean_10", "rolling_mean_20",
    "rolling_std_5", "rolling_std_10", "rolling_std_20",
    "rolling_min_5", "rolling_min_10", "rolling_min_20",
    "rolling_max_5", "rolling_max_10", "rolling_max_20",
    "rolling_skew_20", "rolling_kurt_20",
    "z_score",
    
    # 24. Advanced patterns (10)
    "spring_pattern", "uptrend_structure", "downtrend_structure",
    "volatility_squeeze", "breakout_probability",
    "mean_reversion_score", "trend_continuation_prob",
    "support_level", "resistance_level", "sr_ratio",
    
    # 25. Price patterns (6)
    "doji_pattern", "hammer_pattern", "engulfing_pattern",
    "morning_star", "evening_star", "three_soldiers",
    
    # 26. Additional indicators to reach 240 (14)
    "ppo", "elder_ray_bull", "elder_ray_bear",
    "vwma_20", "close_vwma_ratio",
    "pivot", "support1", "support2", "resistance1", "resistance2",
    "dist_to_support1", "dist_to_resistance1",
    "daily_range", "position_in_daily_range"
]

# Проверка что ровно 240 признаков
assert len(PRODUCTION_FEATURES_240) == 240, f"Expected 240 features, got {len(PRODUCTION_FEATURES_240)}"
assert len(set(PRODUCTION_FEATURES_240)) == 240, "Duplicate features found!"

# Для обратной совместимости
PRODUCTION_FEATURES = PRODUCTION_FEATURES_240
REQUIRED_FEATURES_231 = PRODUCTION_FEATURES_240[:231]  # Если где-то используется 231

# Критические формулы из обучения
CRITICAL_FORMULAS = {
    "returns": "np.log(close / close.shift(1))",
    "volatility": "returns.rolling(window).std()",
    "rsi": "ta.momentum.RSIIndicator(close, window).rsi()",
    "bollinger_bands": "ta.volatility.BollingerBands(close, window)",
    "macd": "ta.trend.MACD(close, window_fast, window_slow, window_sign)",
    "volume_ratio": "volume / volume.rolling(20).mean()",
    "high_low_ratio": "high / low",
    "atr": "ta.volatility.AverageTrueRange(high, low, close, window).average_true_range()",
    "vwap": "(close * volume).cumsum() / volume.cumsum()",
    "obv": "ta.volume.OnBalanceVolumeIndicator(close, volume).on_balance_volume()"
}

if __name__ == "__main__":
    print(f"✅ Production features config with {len(PRODUCTION_FEATURES_240)} real features")
    print(f"📊 First 10 features: {PRODUCTION_FEATURES_240[:10]}")
    print(f"📊 Last 10 features: {PRODUCTION_FEATURES_240[-10:]}")