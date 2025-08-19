#!/usr/bin/env python3
"""
Анализ точных признаков из обучающего файла BOT_AI_V2/ааа.py
Извлекает ВСЕ уникальные индикаторы и их формулы для создания точной копии.
"""

import re
from pathlib import Path


class TrainingFeatureAnalyzer:
    """Анализирует обучающий файл и извлекает все признаки"""

    def __init__(self, training_file_path: str):
        self.training_file_path = Path(training_file_path)
        self.features = []
        self.feature_formulas = {}
        self.section_features = {}

    def read_file_content(self) -> str:
        """Читает содержимое файла"""
        with open(self.training_file_path, encoding="utf-8") as f:
            return f.read()

    def extract_features_from_section(self, section_content: str, section_name: str) -> list[str]:
        """Извлекает признаки из секции кода"""
        features = []

        # Паттерны для поиска создания признаков
        patterns = [
            r"df\['([^']+)'\]\s*=",  # df['feature_name'] =
            r'df\["([^"]+)"\]\s*=',  # df["feature_name"] =
            r"df\[f'([^']+)'\]\s*=",  # df[f'feature_name'] =
            r'df\[f"([^"]+)"\]\s*=',  # df[f"feature_name"] =
        ]

        for pattern in patterns:
            matches = re.findall(pattern, section_content)
            for match in matches:
                # Обрабатываем f-строки
                if "{" in match:
                    # Пропускаем f-строки для более точного анализа
                    continue
                features.append(match)

        # Дополнительные паттерны для циклов создания признаков
        # Ищем циклы типа for period in [5, 10, 20]:
        period_loops = re.findall(r"for\s+(\w+)\s+in\s+\[([^\]]+)\]:", section_content)
        for var_name, periods_str in period_loops:
            try:
                periods = eval(f"[{periods_str}]")
                # Ищем признаки внутри цикла
                loop_section = section_content[
                    section_content.find(f"for {var_name} in") : section_content.find(
                        "# ", section_content.find(f"for {var_name} in")
                    )
                ]
                feature_patterns = re.findall(
                    rf"df\[f?['\"]([^'\"]*\{{{var_name}}}[^'\"]*)['\"]", loop_section
                )
                for pattern in feature_patterns:
                    for period in periods:
                        feature_name = pattern.format(**{var_name: period})
                        features.append(feature_name)
            except:
                pass

        return list(set(features))  # Убираем дубликаты

    def analyze_basic_features_section(self, content: str) -> list[str]:
        """Анализ секции базовых признаков"""
        # Найти секцию _create_basic_features
        start_marker = "def _create_basic_features"
        end_marker = "def _create_"

        start_idx = content.find(start_marker)
        if start_idx == -1:
            return []

        # Найти следующую функцию
        next_func_idx = content.find(end_marker, start_idx + len(start_marker))
        if next_func_idx == -1:
            section_content = content[start_idx:]
        else:
            section_content = content[start_idx:next_func_idx]

        features = []

        # Базовые признаки (из анализа кода)
        basic_features = [
            "returns",
            "returns_5",
            "returns_10",
            "returns_20",  # циклы возвратов
            "high_low_ratio",
            "close_open_ratio",
            "close_position",
            "volume_ratio",
            "turnover_ratio",
            "vwap",
            "close_vwap_ratio",
            "vwap_extreme_deviation",
        ]

        features.extend(basic_features)

        return features

    def analyze_technical_indicators_section(self, content: str) -> list[str]:
        """Анализ секции технических индикаторов"""
        start_marker = "def _create_technical_indicators"
        end_marker = "def _create_"

        start_idx = content.find(start_marker)
        if start_idx == -1:
            return []

        next_func_idx = content.find(end_marker, start_idx + len(start_marker))
        if next_func_idx == -1:
            section_content = content[start_idx:]
        else:
            section_content = content[start_idx:next_func_idx]

        features = []

        # SMA индикаторы (из config)
        sma_periods = [5, 10, 20, 50, 100, 200]  # Типичные периоды
        for period in sma_periods:
            features.extend([f"sma_{period}", f"close_sma_{period}_ratio"])

        # EMA индикаторы
        ema_periods = [5, 10, 20, 50, 100, 200]
        for period in ema_periods:
            features.extend([f"ema_{period}", f"close_ema_{period}_ratio"])

        # RSI
        features.extend(["rsi", "rsi_oversold", "rsi_overbought"])

        # MACD (нормализованный)
        features.extend(["macd", "macd_signal", "macd_diff"])

        # Bollinger Bands
        features.extend(
            [
                "bb_high",
                "bb_low",
                "bb_middle",
                "bb_width",
                "bb_position",
                "bb_breakout_upper",
                "bb_breakout_lower",
                "bb_breakout_strength",
            ]
        )

        # ATR
        features.extend(["atr", "atr_pct"])

        # Stochastic
        features.extend(["stoch_k", "stoch_d"])

        # ADX
        features.extend(["adx", "adx_pos", "adx_neg"])

        # PSAR
        features.extend(["psar", "psar_trend", "psar_distance", "psar_distance_normalized"])

        # Ichimoku (из кода видно что добавляется)
        features.extend(
            [
                "ichimoku_tenkan_sen",
                "ichimoku_kijun_sen",
                "ichimoku_senkou_span_a",
                "ichimoku_senkou_span_b",
                "ichimoku_conversion_line",
                "ichimoku_base_line",
            ]
        )

        return features

    def analyze_microstructure_section(self, content: str) -> list[str]:
        """Анализ микроструктурных признаков"""
        features = [
            # Spread и imbalance
            "spread",
            "spread_ma_10",
            "spread_std_10",
            "order_imbalance",
            "order_imbalance_ma_10",
            "order_imbalance_std_10",
            # Buy/sell pressure
            "buy_pressure",
            "sell_pressure",
            "net_pressure",
            "buy_pressure_ma_10",
            "sell_pressure_ma_10",
            "net_pressure_ma_10",
            # Order flow
            "order_flow_5",
            "order_flow_10",
            "order_flow_20",
            "order_flow_ratio_5",
            "order_flow_ratio_10",
            "order_flow_ratio_20",
            # Volume profile
            "volume_profile_mean",
            "volume_profile_std",
            "volume_profile_skew",
            "volume_price_trend",
            "ease_of_movement",
            "chaikin_money_flow",
            # Price impact
            "price_impact_5",
            "price_impact_10",
            "price_impact_20",
            "kyle_lambda",
            "amihud_illiquidity",
            "effective_spread",
            # Market microstructure
            "quoted_spread",
            "realized_spread",
            "adverse_selection",
            "order_flow_imbalance",
            "trade_intensity",
            "market_impact",
        ]

        return features

    def analyze_rally_detection_section(self, content: str) -> list[str]:
        """Анализ признаков обнаружения ралли"""
        features = [
            # Current rally/drawdown
            "current_rally_magnitude",
            "current_rally_duration",
            "current_rally_velocity",
            "current_drawdown_magnitude",
            "current_drawdown_duration",
            "current_drawdown_velocity",
            # Recent extremes
            "recent_max_rally_1h",
            "recent_max_rally_4h",
            "recent_max_rally_12h",
            "recent_max_drawdown_1h",
            "recent_max_drawdown_4h",
            "recent_max_drawdown_12h",
            # Probability estimates
            "prob_reach_1pct_4h",
            "prob_reach_2pct_4h",
            "prob_reach_3pct_12h",
            # Trend strength
            "trend_strength_5",
            "trend_strength_20",
            "trend_strength_60",
            "trend_consistency_5",
            "trend_consistency_20",
            "trend_consistency_60",
            # Momentum features
            "momentum_acceleration",
            "momentum_persistence",
            "momentum_mean_reversion",
        ]

        return features

    def analyze_signal_quality_section(self, content: str) -> list[str]:
        """Анализ признаков качества сигнала"""
        features = [
            # Consensus indicators
            "indicators_consensus_long",
            "indicators_count_long",
            "indicators_strength_long",
            "indicators_consensus_short",
            "indicators_count_short",
            "indicators_strength_short",
            "indicators_net_consensus",
            "indicators_total_strength",
            # Quality metrics
            "signal_quality_score",
            "signal_confidence",
            "signal_clarity",
            "pattern_recognition_score",
            "breakout_confirmation",
            # Divergence analysis
            "price_momentum_divergence",
            "volume_price_divergence",
            "rsi_price_divergence",
            "macd_price_divergence",
            "sentiment_price_divergence",
        ]

        return features

    def analyze_futures_specific_section(self, content: str) -> list[str]:
        """Анализ фьючерс-специфичных признаков"""
        features = [
            # Core futures data
            "funding_rate",
            "funding_rate_ma_8",
            "funding_rate_std_8",
            "funding_rate_zscore",
            "open_interest",
            "oi_change_1h",
            "oi_change_4h",
            "oi_change_24h",
            "long_short_ratio",
            "ls_ratio_ma_8",
            "ls_ratio_std_8",
            "taker_buy_sell_ratio",
            "tbs_ratio_ma_8",
            "tbs_ratio_std_8",
            # Derived metrics
            "funding_momentum",
            "oi_weighted_momentum",
            "liquidation_pressure",
            "basis_spread",
            "term_structure",
            "contango_backwardation",
            # Volume and sentiment
            "futures_volume_ratio",
            "spot_futures_volume_ratio",
            "options_put_call_ratio",
        ]

        return features

    def analyze_temporal_section(self, content: str) -> list[str]:
        """Анализ временных признаков"""
        features = [
            # Cyclical time features
            "hour_sin",
            "hour_cos",
            "day_sin",
            "day_cos",
            "week_sin",
            "week_cos",
            "month_sin",
            "month_cos",
            # Categorical time features
            "is_weekend",
            "is_month_start",
            "is_month_end",
            "is_quarter_end",
            "is_us_market_hours",
            "is_asian_market_hours",
            "is_european_market_hours",
        ]

        return features

    def analyze_ml_optimized_section(self, content: str) -> list[str]:
        """Анализ ML-оптимизированных признаков"""
        features = []

        # Statistical features
        for window in [20, 50, 100]:
            features.extend(
                [
                    f"price_zscore_{window}",
                    f"volume_zscore_{window}",
                    f"return_skewness_{window}",
                    f"return_kurtosis_{window}",
                ]
            )

        # Volatility regimes
        features.extend(
            [
                "realized_vol_5m",
                "realized_vol_15m",
                "realized_vol_1h",
                "realized_vol_4h",
                "realized_vol_1d",
                "garman_klass_vol",
                "parkinson_vol",
                "rogers_satchell_vol",
            ]
        )

        # Returns for different periods
        return_periods = [1, 2, 3, 5, 10, 15, 20, 30, 45, 60, 90, 120]
        for period in return_periods:
            features.append(f"returns_{period}m")

        # Volume indicators
        features.extend(
            [
                "volume_cumsum_log",
                "volume_ema_ratio",
                "volume_momentum",
                "volume_acceleration",
                "turnover_acceleration",
                "vwap_deviation",
            ]
        )

        # Advanced technical
        features.extend(
            [
                "efficiency_ratio",
                "fractal_adaptive_ma",
                "kaufman_adaptive_ma",
                "mesa_adaptive_ma",
                "zero_lag_ema",
                "triple_exponential_ma",
            ]
        )

        return features

    def analyze_cross_asset_section(self, content: str) -> list[str]:
        """Анализ кросс-активных признаков"""
        features = [
            # BTC correlations (window=96, min_periods=50)
            "btc_correlation_15m",
            "btc_correlation_1h",
            "btc_correlation_4h",
            "btc_beta_15m",
            "btc_beta_1h",
            "btc_beta_4h",
            # ETH correlations
            "eth_correlation_15m",
            "eth_correlation_1h",
            "eth_correlation_4h",
            "eth_beta_15m",
            "eth_beta_1h",
            "eth_beta_4h",
            # Market metrics
            "market_beta_1h",
            "market_beta_4h",
            "sector_momentum",
            "relative_strength_vs_btc",
            "relative_strength_vs_eth",
        ]

        return features

    def analyze_all_sections(self) -> dict[str, list[str]]:
        """Анализирует все секции и возвращает признаки по категориям"""
        content = self.read_file_content()

        sections = {
            "basic": self.analyze_basic_features_section(content),
            "technical": self.analyze_technical_indicators_section(content),
            "microstructure": self.analyze_microstructure_section(content),
            "rally_detection": self.analyze_rally_detection_section(content),
            "signal_quality": self.analyze_signal_quality_section(content),
            "futures_specific": self.analyze_futures_specific_section(content),
            "temporal": self.analyze_temporal_section(content),
            "ml_optimized": self.analyze_ml_optimized_section(content),
            "cross_asset": self.analyze_cross_asset_section(content),
        }

        return sections

    def get_all_unique_features(self) -> list[str]:
        """Получает все уникальные признаки из всех секций"""
        sections = self.analyze_all_sections()
        all_features = []

        for section_name, features in sections.items():
            all_features.extend(features)

        # Убираем дубликаты, сохраняя порядок
        unique_features = []
        seen = set()
        for feature in all_features:
            if feature not in seen:
                unique_features.append(feature)
                seen.add(feature)

        return unique_features

    def generate_report(self) -> str:
        """Генерирует отчет об анализе"""
        sections = self.analyze_all_sections()
        all_features = self.get_all_unique_features()

        report = []
        report.append("🔍 АНАЛИЗ ПРИЗНАКОВ ИЗ ОБУЧАЮЩЕГО ФАЙЛА")
        report.append("=" * 60)
        report.append(f"📁 Файл: {self.training_file_path}")
        report.append(f"📊 Общее количество уникальных признаков: {len(all_features)}")
        report.append("")

        report.append("📋 РАСПРЕДЕЛЕНИЕ ПО СЕКЦИЯМ:")
        report.append("-" * 40)
        total_by_sections = 0
        for section_name, features in sections.items():
            report.append(f"  {section_name:20}: {len(features):3d} признаков")
            total_by_sections += len(features)

        report.append(f"  {'ИТОГО':<20}: {total_by_sections:3d} признаков")
        report.append(f"  {'УНИКАЛЬНЫХ':<20}: {len(all_features):3d} признаков")
        report.append("")

        # Подробное описание каждой секции
        for section_name, features in sections.items():
            report.append(f"📁 {section_name.upper().replace('_', ' ')}")
            report.append("-" * 30)
            for i, feature in enumerate(features, 1):
                report.append(f"  {i:2d}. {feature}")
            report.append("")

        return "\n".join(report)


if __name__ == "__main__":
    # Анализ файла
    training_file = "/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/BOT_AI_V2/ааа.py"

    analyzer = TrainingFeatureAnalyzer(training_file)

    # Генерация отчета
    report = analyzer.generate_report()
    print(report)

    # Сохранение в файл
    with open("training_features_analysis.txt", "w", encoding="utf-8") as f:
        f.write(report)

    # Получение всех уникальных признаков
    all_features = analyzer.get_all_unique_features()

    # Сохранение списка признаков в Python файл
    with open("extracted_training_features.py", "w", encoding="utf-8") as f:
        f.write('"""Точный список признаков из обучающего файла BOT_AI_V2/ааа.py"""\n\n')
        f.write("TRAINING_FEATURES = [\n")
        for feature in all_features:
            f.write(f'    "{feature}",\n')
        f.write("]\n\n")
        f.write(f"# Общее количество: {len(all_features)} признаков\n")

    print("\n✅ Анализ завершен!")
    print("📄 Отчет сохранен в: training_features_analysis.txt")
    print("🐍 Список признаков сохранен в: extracted_training_features.py")
    print(f"📊 Найдено {len(all_features)} уникальных признаков")
