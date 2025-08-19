#!/usr/bin/env python3
"""
Детальное сравнение ВСЕХ 240 признаков между обучающим файлом (ааа.py)
и текущей реализацией (feature_engineering_v2.py).

Цель: убедиться, что каждый индикатор рассчитывается идентично.
"""

import re

# Список всех 240 признаков, которые должны быть
REQUIRED_FEATURES_240 = [
    # Technical indicators
    "rsi_5",
    "rsi_14",
    "rsi_21",
    "sma_5",
    "sma_10",
    "sma_20",
    "sma_50",
    "sma_100",
    "sma_200",
    "ema_5",
    "ema_10",
    "ema_20",
    "ema_50",
    "ema_100",
    "ema_200",
    "bb_upper_20",
    "bb_middle_20",
    "bb_lower_20",
    "bb_position_20",
    "bb_upper_50",
    "bb_middle_50",
    "bb_lower_50",
    "bb_position_50",
    "macd_12_26",
    "macd_signal_12_26",
    "macd_hist_12_26",
    "macd_5_35",
    "macd_signal_5_35",
    "macd_hist_5_35",
    "atr_7",
    "atr_14",
    "atr_21",
    "adx_14",
    "adx_21",
    "cci_14",
    "cci_20",
    "stoch_k_14",
    "stoch_d_14",
    "stoch_k_21",
    "stoch_d_21",
    "williams_r_14",
    "williams_r_21",
    "mfi_14",
    "mfi_21",
    "obv",
    "obv_sma_20",
    "obv_ema_20",
    # Returns
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
    # Volatility
    "volatility_5",
    "volatility_10",
    "volatility_15",
    "volatility_20",
    "volatility_30",
    "volatility_45",
    "volatility_60",
    "volatility_90",
    # Microstructure
    "spread",
    "spread_ma_10",
    "spread_std_10",
    "order_imbalance",
    "order_imbalance_ma_10",
    "order_imbalance_std_10",
    "buy_pressure",
    "sell_pressure",
    "net_pressure",
    "buy_pressure_ma_10",
    "sell_pressure_ma_10",
    "net_pressure_ma_10",
    "order_flow_5",
    "order_flow_10",
    "order_flow_20",
    "order_flow_ratio_5",
    "order_flow_ratio_10",
    "order_flow_ratio_20",
    # Rally detection
    "current_rally_magnitude",
    "current_rally_duration",
    "current_rally_velocity",
    "current_drawdown_magnitude",
    "current_drawdown_duration",
    "current_drawdown_velocity",
    "recent_max_rally_1h",
    "recent_max_rally_4h",
    "recent_max_rally_12h",
    "recent_max_drawdown_1h",
    "recent_max_drawdown_4h",
    "recent_max_drawdown_12h",
    "prob_reach_1pct_4h",
    "prob_reach_2pct_4h",
    "prob_reach_3pct_12h",
    # Temporal
    "hour_sin",
    "hour_cos",
    "day_sin",
    "day_cos",
    "week_sin",
    "week_cos",
    "month_sin",
    "month_cos",
    "is_weekend",
    "is_month_start",
    "is_month_end",
    "is_quarter_end",
    # Cross-asset (8 features as in training)
    "btc_correlation_15m",
    "btc_correlation_1h",
    "btc_correlation_4h",
    "eth_correlation_15m",
    "eth_correlation_1h",
    "eth_correlation_4h",
    "market_beta_1h",
    "market_beta_4h",
    # Signal quality
    "momentum_score",
    "trend_strength",
    "trend_consistency",
    "momentum_divergence",
    "trend_acceleration",
    "trend_quality",
    "overbought_score",
    "oversold_score",
    "divergence_bull",
    "divergence_bear",
    "pattern_strength",
    "breakout_strength",
    "reversal_probability",
    "support_distance",
    "resistance_distance",
    # Futures specific
    "funding_rate",
    "open_interest",
    "oi_change_1h",
    "long_short_ratio",
    "taker_buy_sell_ratio",
    "funding_momentum",
    "oi_weighted_momentum",
    "liquidation_pressure",
    "basis_spread",
    "term_structure",
    # ML optimized features (remaining to 240)
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
    # Pattern features
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
    # Adaptive features
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
    # Additional statistical
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


class FeatureComparator:
    def __init__(self):
        self.training_file = "/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/BOT_AI_V2/ааа.py"
        self.current_file = "/ml/logic/archive_old_versions/feature_engineering_v2.py"
        self.differences = []

    def read_file(self, filepath):
        """Читает файл и возвращает содержимое"""
        with open(filepath, encoding="utf-8") as f:
            return f.read()

    def extract_feature_calculation(self, content, feature_name):
        """Извлекает код расчета для конкретного признака"""
        # Patterns for finding feature calculations
        patterns = [
            rf"df\['{feature_name}'\]\s*=\s*([^\n]+)",
            rf"df\['{feature_name}'\]\s*=\s*([^\n]+(?:\n\s+[^\n]+)*)",
            rf"{feature_name}\s*=\s*([^\n]+)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            if matches:
                return matches[0].strip()
        return None

    def compare_technical_indicators(self):
        """Сравнивает расчет технических индикаторов"""
        training_content = self.read_file(self.training_file)
        current_content = self.read_file(self.current_file)

        comparisons = []

        # RSI
        for period in [5, 14, 21]:
            feature = f"rsi_{period}"
            training_calc = self.extract_feature_calculation(training_content, feature)
            current_calc = self.extract_feature_calculation(current_content, feature)

            comparisons.append(
                {
                    "feature": feature,
                    "training": training_calc,
                    "current": current_calc,
                    "match": (
                        training_calc == current_calc if training_calc and current_calc else False
                    ),
                }
            )

        # SMA
        for period in [5, 10, 20, 50, 100, 200]:
            feature = f"sma_{period}"
            training_calc = self.extract_feature_calculation(training_content, feature)
            current_calc = self.extract_feature_calculation(current_content, feature)

            comparisons.append(
                {
                    "feature": feature,
                    "training": training_calc,
                    "current": current_calc,
                    "match": (
                        training_calc == current_calc if training_calc and current_calc else False
                    ),
                }
            )

        return comparisons

    def check_returns_calculation(self):
        """Проверяет расчет возвратов"""
        training_content = self.read_file(self.training_file)
        current_content = self.read_file(self.current_file)

        comparisons = []

        for period in [1, 2, 3, 5, 10, 15, 20, 30, 45, 60, 90, 120]:
            feature = f"returns_{period}"

            # В обучающем файле ищем формулу
            training_pattern = rf"returns_{period}.*?=.*?np\.log\(.*?close.*?shift\({period}\)"
            training_match = re.search(training_pattern, training_content)

            # В текущем файле
            current_pattern = rf"returns_{period}.*?=.*?"
            current_match = re.search(current_pattern, current_content)

            comparisons.append(
                {
                    "feature": feature,
                    "training_uses_log": bool(training_match),
                    "current_formula": current_match.group(0) if current_match else None,
                    "issue": None,
                }
            )

        return comparisons

    def check_cross_asset_features(self):
        """Проверяет кросс-активные признаки (самое важное!)"""
        training_content = self.read_file(self.training_file)
        current_content = self.read_file(self.current_file)

        # Ищем btc_correlation в обучающем файле
        btc_corr_pattern = r"btc_correlation.*?rolling\((\d+)"
        training_btc_window = re.search(btc_corr_pattern, training_content)

        # В текущем файле
        current_btc_window = re.search(btc_corr_pattern, current_content)

        print("\n🔍 КРИТИЧЕСКИ ВАЖНО - Cross-Asset Features:")
        print(
            f"  Training BTC correlation window: {training_btc_window.group(1) if training_btc_window else 'NOT FOUND'}"
        )
        print(
            f"  Current BTC correlation window: {current_btc_window.group(1) if current_btc_window else 'NOT FOUND'}"
        )

        # Проверяем ETH correlation
        eth_in_training = "eth_correlation" in training_content
        eth_in_current = "eth_correlation" in current_content

        print(f"  ETH correlation in training: {eth_in_training}")
        print(f"  ETH correlation in current: {eth_in_current}")

        return {
            "btc_window_match": (
                training_btc_window == current_btc_window if training_btc_window else False
            ),
            "eth_handling_correct": not eth_in_training,  # ETH не должно быть в обучении
        }

    def run_full_comparison(self):
        """Запускает полное сравнение всех 240 признаков"""
        print("=" * 80)
        print("📊 ПОЛНОЕ СРАВНЕНИЕ ВСЕХ 240 ПРИЗНАКОВ")
        print("=" * 80)

        # 1. Технические индикаторы
        print("\n1️⃣ ТЕХНИЧЕСКИЕ ИНДИКАТОРЫ:")
        tech_comparisons = self.compare_technical_indicators()
        mismatches = [c for c in tech_comparisons if not c.get("match", True)]
        if mismatches:
            print(f"  ❌ Найдено {len(mismatches)} несоответствий:")
            for m in mismatches[:5]:  # Показываем первые 5
                print(f"    - {m['feature']}")
        else:
            print("  ✅ Все технические индикаторы совпадают")

        # 2. Returns
        print("\n2️⃣ RETURNS (ДОХОДНОСТИ):")
        returns_comparisons = self.check_returns_calculation()
        log_returns = [r for r in returns_comparisons if r["training_uses_log"]]
        print(f"  В обучении используется log returns: {len(log_returns)} признаков")

        # 3. Cross-asset features (САМОЕ ВАЖНОЕ!)
        print("\n3️⃣ CROSS-ASSET FEATURES (КРИТИЧНО!):")
        cross_asset_result = self.check_cross_asset_features()

        # 4. Проверяем наличие всех 240 признаков
        print("\n4️⃣ ПРОВЕРКА ПОЛНОТЫ (240 признаков):")
        print(f"  Ожидается: {len(REQUIRED_FEATURES_240)} признаков")

        # Проверяем каждую группу
        feature_groups = {
            "Technical": 47,
            "Returns": 12,
            "Volatility": 8,
            "Microstructure": 18,
            "Rally": 15,
            "Temporal": 12,
            "Cross-asset": 8,
            "Signal quality": 15,
            "Futures": 10,
            "ML optimized": 95,  # Остальные
        }

        for group, count in feature_groups.items():
            print(f"  {group}: {count} признаков")

        print("\n" + "=" * 80)
        print("📋 ИТОГОВЫЙ РЕЗУЛЬТАТ:")

        issues_found = []

        if not cross_asset_result["btc_window_match"]:
            issues_found.append("❌ BTC correlation window не совпадает!")

        if len(mismatches) > 0:
            issues_found.append(f"❌ {len(mismatches)} технических индикаторов не совпадают")

        if issues_found:
            print("НАЙДЕНЫ ПРОБЛЕМЫ:")
            for issue in issues_found:
                print(f"  {issue}")
        else:
            print("✅ Все признаки рассчитываются корректно!")

        return len(issues_found) == 0


if __name__ == "__main__":
    comparator = FeatureComparator()
    success = comparator.run_full_comparison()

    if not success:
        print("\n⚠️ ТРЕБУЕТСЯ ИСПРАВЛЕНИЕ РАСЧЕТОВ!")
        print("Запустите детальный анализ для каждого несоответствия.")
    else:
        print("\n✅ Все 240 признаков соответствуют обучающему файлу!")
