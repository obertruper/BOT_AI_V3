"""
Feature Engineering из проекта обучения модели
Генерирует ровно 240 признаков в правильном порядке
"""

import warnings
from typing import Dict, List, Union

import numpy as np
import pandas as pd
import ta

warnings.filterwarnings("ignore")

from core.logger import setup_logger


class FeatureEngineer:
    """Создание признаков для модели прогнозирования - точная версия из обучения"""

    def __init__(self, config: Dict):
        self.config = config
        self.logger = setup_logger("FeatureEngineer")

        # Список всех 240 признаков в правильном порядке (как при обучении)
        self.feature_names = self._get_feature_names()

    def _get_feature_names(self) -> List[str]:
        """Возвращает список всех 240 признаков в правильном порядке"""
        features = []

        # 1. Price features (10)
        features.extend(["open", "high", "low", "close", "volume"])
        features.extend(["hl_ratio", "oc_ratio", "hlc3", "ohlc4", "vwap"])

        # 2. Returns (20)
        for period in [1, 2, 3, 5, 10, 15, 20, 30]:
            features.append(f"returns_{period}")
        for period in [1, 2, 3, 5, 10, 15]:
            features.append(f"log_returns_{period}")

        # 3. Moving Averages (25)
        for period in [5, 10, 20, 50, 100]:
            features.append(f"sma_{period}")
        for period in [5, 10, 20, 50, 100]:
            features.append(f"ema_{period}")
        for period in [5, 10, 20, 50, 100]:
            features.append(f"wma_{period}")
        for period in [5, 10, 20, 50, 100]:
            features.append(f"hma_{period}")

        # 4. Volatility indicators (20)
        for period in [5, 10, 20, 30]:
            features.append(f"std_{period}")
        for period in [7, 14, 21]:
            features.append(f"atr_{period}")
        features.extend(
            [
                "bb_upper_20",
                "bb_middle_20",
                "bb_lower_20",
                "bb_width_20",
                "bb_position_20",
            ]
        )
        features.extend(["kc_upper_20", "kc_middle_20", "kc_lower_20", "kc_width_20"])
        features.extend(["dc_upper_20", "dc_lower_20", "dc_middle_20", "dc_width_20"])

        # 5. Momentum indicators (33)
        for period in [7, 14, 21, 28]:
            features.append(f"rsi_{period}")
        features.extend(["stoch_k_14", "stoch_d_14", "stoch_k_21", "stoch_d_21"])
        features.extend(["macd", "macd_signal", "macd_diff"])
        for period in [10, 14, 20]:
            features.append(f"cci_{period}")
        for period in [10, 14]:
            features.append(f"williams_r_{period}")
        for period in [5, 10, 20]:
            features.append(f"roc_{period}")
        for period in [10, 14]:
            features.append(f"mfi_{period}")
        for period in [10, 14, 20]:
            features.append(f"adx_{period}")
        for period in [14, 20]:
            features.append(f"plus_di_{period}")
            features.append(f"minus_di_{period}")

        # Добавляем недостающие momentum индикаторы
        features.extend(["ultimate_oscillator", "awesome_oscillator", "ppo"])

        # 6. Volume indicators (20)
        for period in [5, 10, 20]:
            features.append(f"volume_sma_{period}")
        features.extend(["obv", "obv_ma_10", "obv_ma_20"])
        features.extend(["ad_line", "ad_oscillator"])
        features.extend(["cmf_20", "cmf_10"])
        features.extend(["fi_13", "fi_50"])
        features.extend(["eom_14", "eom_20"])
        features.extend(["vpt", "nvi", "pvi"])
        features.extend(["volume_ratio_5", "volume_ratio_10"])

        # 7. Trend indicators (20)
        features.extend(["adx_trend_14", "adx_trend_20"])
        features.extend(["aroon_up_25", "aroon_down_25", "aroon_oscillator_25"])
        features.extend(["psar_up", "psar_down", "psar_indicator"])
        features.extend(["ichimoku_a", "ichimoku_b", "ichimoku_base", "ichimoku_conv"])
        features.extend(["trix_15", "trix_signal_15"])
        features.extend(["vi_plus_14", "vi_minus_14"])
        features.extend(["mass_index_25", "kst", "kst_signal", "tsi"])

        # 8. Market microstructure (20)
        features.extend(["spread", "spread_pct", "bid_ask_imbalance"])
        features.extend(["high_low_spread", "close_position"])
        features.extend(["upper_shadow", "lower_shadow", "body_size"])
        features.extend(["is_bullish", "is_bearish", "is_doji"])
        features.extend(["gap", "gap_pct"])
        features.extend(["intraday_return", "overnight_return"])
        features.extend(["volume_price_trend", "volume_weighted_price"])
        features.extend(["typical_price", "weighted_close"])

        # 9. Pattern recognition (20)
        features.extend(
            ["hammer", "inverted_hammer", "bullish_engulfing", "bearish_engulfing"]
        )
        features.extend(
            [
                "morning_star",
                "evening_star",
                "three_white_soldiers",
                "three_black_crows",
            ]
        )
        features.extend(["doji_star", "shooting_star", "hanging_man", "harami"])
        features.extend(["piercing_line", "dark_cloud", "spinning_top", "marubozu"])
        features.extend(["inside_bar", "outside_bar", "pin_bar", "fakey"])

        # 10. Statistical features (20)
        for period in [10, 20]:
            features.append(f"skew_{period}")
            features.append(f"kurtosis_{period}")
        for period in [10, 20, 50]:
            features.append(f"percentile_rank_{period}")
        for period in [10, 20]:
            features.append(f"zscore_{period}")
        features.extend(["entropy_10", "entropy_20"])
        features.extend(["hurst_exponent", "fractal_dimension"])
        features.extend(["autocorr_1", "autocorr_5", "autocorr_10"])
        features.extend(["partial_autocorr_1", "partial_autocorr_5"])

        # 11. Support/Resistance (10)
        features.extend(["pivot_point", "r1", "r2", "s1", "s2"])
        features.extend(["distance_to_high_20", "distance_to_low_20"])
        features.extend(["distance_to_high_50", "distance_to_low_50"])
        features.extend(["breakout_indicator"])

        # 12. Interaction features (20)
        features.extend(["volume_price_corr_20", "volume_return_corr_20"])
        features.extend(["high_low_corr_20", "open_close_corr_20"])
        features.extend(["rsi_volume_interaction", "macd_volume_interaction"])
        features.extend(["bb_squeeze", "kc_squeeze"])
        features.extend(["trend_strength_adx", "trend_strength_aroon"])
        features.extend(["momentum_strength", "volatility_regime"])
        features.extend(["volume_trend", "price_trend"])
        features.extend(["mean_reversion_indicator", "trend_following_indicator"])
        features.extend(["risk_on_indicator", "risk_off_indicator"])
        features.extend(["market_regime", "volatility_regime_change"])

        # 13. Lag features (20)
        for lag in [1, 2, 3, 5, 10]:
            features.append(f"close_lag_{lag}")
        for lag in [1, 2, 3, 5, 10]:
            features.append(f"volume_lag_{lag}")
        for lag in [1, 2, 3]:
            features.append(f"returns_lag_{lag}")
        for lag in [1, 2]:
            features.append(f"rsi_lag_{lag}")
        for lag in [1, 2]:
            features.append(f"macd_lag_{lag}")
        for lag in [1]:
            features.append(f"bb_position_lag_{lag}")
            features.append(f"volume_ratio_lag_{lag}")

        # Должно быть ровно 240 признаков
        assert len(features) == 240, f"Expected 240 features, got {len(features)}"
        return features

    def create_features(
        self, df: Union[pd.DataFrame, np.ndarray]
    ) -> Union[pd.DataFrame, np.ndarray]:
        """
        Создание всех 240 признаков для модели

        Args:
            df: DataFrame с OHLCV данными или numpy array

        Returns:
            DataFrame или array с 240 признаками
        """
        # Если это уже numpy array - возвращаем как есть
        if isinstance(df, np.ndarray):
            self.logger.debug(f"Получен numpy array shape: {df.shape}")
            if df.shape[1] == 240:
                return df
            else:
                self.logger.warning(f"Array has {df.shape[1]} features, expected 240")
                # Дополняем или обрезаем до 240
                if df.shape[1] < 240:
                    padding = np.zeros((df.shape[0], 240 - df.shape[1]))
                    return np.hstack([df, padding])
                else:
                    return df[:, :240]

        # Работаем с DataFrame
        data = df.copy()

        # Сортируем по времени
        if "timestamp" in data.columns:
            data = data.sort_values("timestamp")
        elif "datetime" in data.columns:
            data = data.sort_values("datetime")

        data = data.reset_index(drop=True)

        # Проверяем обязательные колонки
        required_cols = ["open", "high", "low", "close", "volume"]
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        # Создаем DataFrame для признаков
        features = pd.DataFrame(index=data.index)

        try:
            # 1. Price features (10)
            features["open"] = data["open"]
            features["high"] = data["high"]
            features["low"] = data["low"]
            features["close"] = data["close"]
            features["volume"] = data["volume"]
            features["hl_ratio"] = self._safe_divide(data["high"], data["low"])
            features["oc_ratio"] = self._safe_divide(data["open"], data["close"])
            features["hlc3"] = (data["high"] + data["low"] + data["close"]) / 3
            features["ohlc4"] = (
                data["open"] + data["high"] + data["low"] + data["close"]
            ) / 4
            features["vwap"] = self._calculate_vwap(data)

            # 2. Returns (20)
            for period in [1, 2, 3, 5, 10, 15, 20, 30]:
                features[f"returns_{period}"] = data["close"].pct_change(period)
            for period in [1, 2, 3, 5, 10, 15]:
                features[f"log_returns_{period}"] = np.log(
                    data["close"] / data["close"].shift(period)
                )

            # 3. Moving Averages (20)
            for period in [5, 10, 20, 50, 100]:
                features[f"sma_{period}"] = ta.trend.sma_indicator(
                    data["close"], window=period
                )
            for period in [5, 10, 20, 50, 100]:
                features[f"ema_{period}"] = ta.trend.ema_indicator(
                    data["close"], window=period
                )
            for period in [5, 10, 20, 50, 100]:
                features[f"wma_{period}"] = ta.trend.wma_indicator(
                    data["close"], window=period
                )
            # Hull MA - аппроксимация
            for period in [5, 10, 20, 50, 100]:
                wma_half = ta.trend.wma_indicator(data["close"], window=period // 2)
                wma_full = ta.trend.wma_indicator(data["close"], window=period)
                features[f"hma_{period}"] = ta.trend.wma_indicator(
                    2 * wma_half - wma_full, window=int(np.sqrt(period))
                )

            # 4. Volatility indicators (20)
            for period in [5, 10, 20, 30]:
                features[f"std_{period}"] = data["close"].rolling(period).std()

            for period in [7, 14, 21]:
                features[f"atr_{period}"] = ta.volatility.average_true_range(
                    data["high"], data["low"], data["close"], window=period
                )

            # Bollinger Bands
            bb = ta.volatility.BollingerBands(
                close=data["close"], window=20, window_dev=2
            )
            features["bb_upper_20"] = bb.bollinger_hband()
            features["bb_middle_20"] = bb.bollinger_mavg()
            features["bb_lower_20"] = bb.bollinger_lband()
            features["bb_width_20"] = bb.bollinger_wband()
            features["bb_position_20"] = bb.bollinger_pband()

            # Keltner Channel
            kc = ta.volatility.KeltnerChannel(
                high=data["high"], low=data["low"], close=data["close"], window=20
            )
            features["kc_upper_20"] = kc.keltner_channel_hband()
            features["kc_middle_20"] = kc.keltner_channel_mband()
            features["kc_lower_20"] = kc.keltner_channel_lband()
            features["kc_width_20"] = kc.keltner_channel_wband()

            # Donchian Channel
            dc = ta.volatility.DonchianChannel(
                high=data["high"], low=data["low"], close=data["close"], window=20
            )
            features["dc_upper_20"] = dc.donchian_channel_hband()
            features["dc_lower_20"] = dc.donchian_channel_lband()
            features["dc_middle_20"] = dc.donchian_channel_mband()
            features["dc_width_20"] = dc.donchian_channel_wband()

            # 5. Momentum indicators (33)
            for period in [7, 14, 21, 28]:
                features[f"rsi_{period}"] = ta.momentum.rsi(
                    data["close"], window=period
                )

            # Stochastic
            stoch_14 = ta.momentum.StochasticOscillator(
                high=data["high"], low=data["low"], close=data["close"], window=14
            )
            features["stoch_k_14"] = stoch_14.stoch()
            features["stoch_d_14"] = stoch_14.stoch_signal()

            stoch_21 = ta.momentum.StochasticOscillator(
                high=data["high"], low=data["low"], close=data["close"], window=21
            )
            features["stoch_k_21"] = stoch_21.stoch()
            features["stoch_d_21"] = stoch_21.stoch_signal()

            # MACD
            macd = ta.trend.MACD(data["close"])
            features["macd"] = macd.macd()
            features["macd_signal"] = macd.macd_signal()
            features["macd_diff"] = macd.macd_diff()

            # CCI
            for period in [10, 14, 20]:
                features[f"cci_{period}"] = ta.trend.cci(
                    data["high"], data["low"], data["close"], window=period
                )

            # Williams %R
            for period in [10, 14]:
                features[f"williams_r_{period}"] = ta.momentum.williams_r(
                    data["high"], data["low"], data["close"], lbp=period
                )

            # ROC
            for period in [5, 10, 20]:
                features[f"roc_{period}"] = ta.momentum.roc(
                    data["close"], window=period
                )

            # MFI
            for period in [10, 14]:
                features[f"mfi_{period}"] = ta.volume.money_flow_index(
                    data["high"],
                    data["low"],
                    data["close"],
                    data["volume"],
                    window=period,
                )

            # ADX
            for period in [10, 14, 20]:
                adx = ta.trend.ADXIndicator(
                    data["high"], data["low"], data["close"], window=period
                )
                features[f"adx_{period}"] = adx.adx()

            # DI
            for period in [14, 20]:
                adx = ta.trend.ADXIndicator(
                    data["high"], data["low"], data["close"], window=period
                )
                features[f"plus_di_{period}"] = adx.adx_pos()
                features[f"minus_di_{period}"] = adx.adx_neg()

            # Добавляем недостающие momentum индикаторы
            features["ultimate_oscillator"] = ta.momentum.ultimate_oscillator(
                data["high"], data["low"], data["close"]
            )
            features["awesome_oscillator"] = ta.momentum.awesome_oscillator(
                data["high"], data["low"]
            )
            features["ppo"] = ta.momentum.ppo(data["close"])

            # 6. Volume indicators (20)
            for period in [5, 10, 20]:
                features[f"volume_sma_{period}"] = data["volume"].rolling(period).mean()

            # OBV
            features["obv"] = ta.volume.on_balance_volume(data["close"], data["volume"])
            features["obv_ma_10"] = features["obv"].rolling(10).mean()
            features["obv_ma_20"] = features["obv"].rolling(20).mean()

            # A/D Line
            features["ad_line"] = ta.volume.acc_dist_index(
                data["high"], data["low"], data["close"], data["volume"]
            )
            features["ad_oscillator"] = (
                features["ad_line"] - features["ad_line"].rolling(10).mean()
            )

            # CMF
            features["cmf_20"] = ta.volume.chaikin_money_flow(
                data["high"], data["low"], data["close"], data["volume"], window=20
            )
            features["cmf_10"] = ta.volume.chaikin_money_flow(
                data["high"], data["low"], data["close"], data["volume"], window=10
            )

            # Force Index
            features["fi_13"] = ta.volume.force_index(
                data["close"], data["volume"], window=13
            )
            features["fi_50"] = ta.volume.force_index(
                data["close"], data["volume"], window=50
            )

            # EOM
            features["eom_14"] = ta.volume.ease_of_movement(
                data["high"], data["low"], data["volume"], window=14
            )
            features["eom_20"] = ta.volume.ease_of_movement(
                data["high"], data["low"], data["volume"], window=20
            )

            # VPT
            features["vpt"] = ta.volume.volume_price_trend(
                data["close"], data["volume"]
            )

            # NVI/PVI
            features["nvi"] = ta.volume.negative_volume_index(
                data["close"], data["volume"]
            )
            features["pvi"] = self._calculate_pvi(data)

            # Volume ratios
            features["volume_ratio_5"] = self._safe_divide(
                data["volume"], data["volume"].rolling(5).mean()
            )
            features["volume_ratio_10"] = self._safe_divide(
                data["volume"], data["volume"].rolling(10).mean()
            )

            # 7. Trend indicators (20)
            adx_14 = ta.trend.ADXIndicator(
                data["high"], data["low"], data["close"], window=14
            )
            adx_20 = ta.trend.ADXIndicator(
                data["high"], data["low"], data["close"], window=20
            )
            features["adx_trend_14"] = adx_14.adx()
            features["adx_trend_20"] = adx_20.adx()

            # Aroon
            aroon = ta.trend.AroonIndicator(data["high"], data["low"], window=25)
            features["aroon_up_25"] = aroon.aroon_up()
            features["aroon_down_25"] = aroon.aroon_down()
            features["aroon_oscillator_25"] = (
                features["aroon_up_25"] - features["aroon_down_25"]
            )

            # PSAR
            psar = ta.trend.PSARIndicator(data["high"], data["low"], data["close"])
            features["psar_up"] = psar.psar_up()
            features["psar_down"] = psar.psar_down()
            features["psar_indicator"] = psar.psar_up_indicator().astype(int)

            # Ichimoku
            ichimoku = ta.trend.IchimokuIndicator(data["high"], data["low"])
            features["ichimoku_a"] = ichimoku.ichimoku_a()
            features["ichimoku_b"] = ichimoku.ichimoku_b()
            features["ichimoku_base"] = ichimoku.ichimoku_base_line()
            features["ichimoku_conv"] = ichimoku.ichimoku_conversion_line()

            # TRIX
            features["trix_15"] = ta.trend.trix(data["close"], window=15)
            features["trix_signal_15"] = features["trix_15"].rolling(9).mean()

            # Vortex
            vi = ta.trend.VortexIndicator(
                data["high"], data["low"], data["close"], window=14
            )
            features["vi_plus_14"] = vi.vortex_indicator_pos()
            features["vi_minus_14"] = vi.vortex_indicator_neg()

            # Mass Index
            features["mass_index_25"] = ta.trend.mass_index(
                data["high"], data["low"], window_fast=9, window_slow=25
            )

            # KST
            kst = ta.trend.KSTIndicator(data["close"])
            features["kst"] = kst.kst()
            features["kst_signal"] = kst.kst_sig()

            # TSI
            features["tsi"] = ta.momentum.tsi(data["close"])

            # 8. Market microstructure (20)
            features["spread"] = data["high"] - data["low"]
            features["spread_pct"] = self._safe_divide(
                features["spread"], data["close"]
            )
            features["bid_ask_imbalance"] = self._safe_divide(
                data["close"] - data["open"], features["spread"]
            )
            features["high_low_spread"] = self._safe_divide(
                data["high"] - data["low"], data["close"]
            )
            features["close_position"] = self._safe_divide(
                data["close"] - data["low"], data["high"] - data["low"]
            )

            # Shadows
            features["upper_shadow"] = self._safe_divide(
                data["high"] - np.maximum(data["open"], data["close"]),
                features["spread"],
            )
            features["lower_shadow"] = self._safe_divide(
                np.minimum(data["open"], data["close"]) - data["low"],
                features["spread"],
            )
            features["body_size"] = np.abs(data["close"] - data["open"])

            # Candle patterns
            features["is_bullish"] = (data["close"] > data["open"]).astype(int)
            features["is_bearish"] = (data["close"] < data["open"]).astype(int)
            features["is_doji"] = (
                np.abs(data["close"] - data["open"]) < 0.001 * data["close"]
            ).astype(int)

            # Gaps
            features["gap"] = data["open"] - data["close"].shift(1)
            features["gap_pct"] = self._safe_divide(
                features["gap"], data["close"].shift(1)
            )

            # Returns
            features["intraday_return"] = self._safe_divide(
                data["close"] - data["open"], data["open"]
            )
            features["overnight_return"] = self._safe_divide(
                data["open"] - data["close"].shift(1), data["close"].shift(1)
            )

            # Volume weighted
            features["volume_price_trend"] = (
                data["close"].pct_change() * data["volume"]
            ).cumsum()
            features["volume_weighted_price"] = self._safe_divide(
                (data["close"] * data["volume"]).cumsum(), data["volume"].cumsum()
            )
            features["typical_price"] = (data["high"] + data["low"] + data["close"]) / 3
            features["weighted_close"] = (
                data["high"] + data["low"] + 2 * data["close"]
            ) / 4

            # 9. Pattern recognition (20) - Simplified patterns
            self._add_pattern_features(data, features)

            # 10. Statistical features (20)
            for period in [10, 20]:
                features[f"skew_{period}"] = data["close"].rolling(period).skew()
                features[f"kurtosis_{period}"] = data["close"].rolling(period).kurt()

            for period in [10, 20, 50]:
                features[f"percentile_rank_{period}"] = (
                    data["close"].rolling(period).rank(pct=True)
                )

            for period in [10, 20]:
                mean = data["close"].rolling(period).mean()
                std = data["close"].rolling(period).std()
                features[f"zscore_{period}"] = self._safe_divide(
                    data["close"] - mean, std
                )

            # Entropy
            features["entropy_10"] = self._calculate_entropy(data["close"], 10)
            features["entropy_20"] = self._calculate_entropy(data["close"], 20)

            # Fractal
            features["hurst_exponent"] = self._calculate_hurst(data["close"])
            features["fractal_dimension"] = 2 - features["hurst_exponent"]

            # Autocorrelation
            for lag in [1, 5, 10]:
                features[f"autocorr_{lag}"] = (
                    data["close"].rolling(20).apply(lambda x: x.autocorr(lag=lag))
                )

            for lag in [1, 5]:
                features[f"partial_autocorr_{lag}"] = self._calculate_partial_autocorr(
                    data["close"], lag
                )

            # 11. Support/Resistance (10)
            features["pivot_point"] = (data["high"] + data["low"] + data["close"]) / 3
            features["r1"] = 2 * features["pivot_point"] - data["low"]
            features["r2"] = features["pivot_point"] + (data["high"] - data["low"])
            features["s1"] = 2 * features["pivot_point"] - data["high"]
            features["s2"] = features["pivot_point"] - (data["high"] - data["low"])

            features["distance_to_high_20"] = self._safe_divide(
                data["high"].rolling(20).max() - data["close"], data["close"]
            )
            features["distance_to_low_20"] = self._safe_divide(
                data["close"] - data["low"].rolling(20).min(), data["close"]
            )
            features["distance_to_high_50"] = self._safe_divide(
                data["high"].rolling(50).max() - data["close"], data["close"]
            )
            features["distance_to_low_50"] = self._safe_divide(
                data["close"] - data["low"].rolling(50).min(), data["close"]
            )

            features["breakout_indicator"] = (
                (data["close"] > data["high"].rolling(20).max().shift(1))
                | (data["close"] < data["low"].rolling(20).min().shift(1))
            ).astype(int)

            # 12. Interaction features (20)
            features["volume_price_corr_20"] = (
                data["close"].rolling(20).corr(data["volume"])
            )
            features["volume_return_corr_20"] = (
                data["close"].pct_change().rolling(20).corr(data["volume"].pct_change())
            )
            features["high_low_corr_20"] = data["high"].rolling(20).corr(data["low"])
            features["open_close_corr_20"] = (
                data["open"].rolling(20).corr(data["close"])
            )

            features["rsi_volume_interaction"] = (
                features["rsi_14"] * features["volume_ratio_5"]
            )
            features["macd_volume_interaction"] = (
                features["macd"] * features["volume_ratio_5"]
            )

            features["bb_squeeze"] = (
                features["bb_upper_20"] - features["bb_lower_20"]
            ) / features["bb_middle_20"]
            features["kc_squeeze"] = (
                features["kc_upper_20"] - features["kc_lower_20"]
            ) / features["kc_middle_20"]

            features["trend_strength_adx"] = features["adx_14"] * np.sign(
                features["macd"]
            )
            features["trend_strength_aroon"] = features["aroon_oscillator_25"] / 100

            features["momentum_strength"] = features["rsi_14"] * features["roc_10"]
            features["volatility_regime"] = (
                features["std_20"] > features["std_20"].rolling(50).mean()
            ).astype(int)

            features["volume_trend"] = np.sign(
                features["volume_sma_5"] - features["volume_sma_20"]
            )
            features["price_trend"] = np.sign(features["sma_10"] - features["sma_50"])

            features["mean_reversion_indicator"] = features["zscore_20"]
            features["trend_following_indicator"] = (
                features["macd_diff"] * features["adx_14"]
            )

            features["risk_on_indicator"] = features["rsi_14"] * (
                1 - features["volatility_regime"]
            )
            features["risk_off_indicator"] = (100 - features["rsi_14"]) * features[
                "volatility_regime"
            ]

            features["market_regime"] = self._determine_market_regime(features)
            features["volatility_regime_change"] = features["volatility_regime"].diff()

            # 13. Lag features (20)
            for lag in [1, 2, 3, 5, 10]:
                features[f"close_lag_{lag}"] = data["close"].shift(lag)

            for lag in [1, 2, 3, 5, 10]:
                features[f"volume_lag_{lag}"] = data["volume"].shift(lag)

            for lag in [1, 2, 3]:
                features[f"returns_lag_{lag}"] = features["returns_1"].shift(lag)

            for lag in [1, 2]:
                features[f"rsi_lag_{lag}"] = features["rsi_14"].shift(lag)

            for lag in [1, 2]:
                features[f"macd_lag_{lag}"] = features["macd"].shift(lag)

            features["bb_position_lag_1"] = features["bb_position_20"].shift(1)
            features["volume_ratio_lag_1"] = features["volume_ratio_5"].shift(1)

        except Exception as e:
            self.logger.error(f"Error creating features: {e}")
            # Заполняем недостающие признаки нулями
            for name in self.feature_names:
                if name not in features.columns:
                    features[name] = 0

        # Берем только нужные признаки в правильном порядке
        final_features = features[self.feature_names].copy()

        # Заполняем NaN и Inf
        final_features = final_features.replace([np.inf, -np.inf], 0)
        final_features = final_features.fillna(method="ffill").fillna(0)

        self.logger.info(f"Created {len(final_features.columns)} features")

        return final_features

    def _safe_divide(self, numerator, denominator, fill_value=0):
        """Безопасное деление"""
        with np.errstate(divide="ignore", invalid="ignore"):
            result = numerator / denominator
            result = result.replace([np.inf, -np.inf], fill_value)
            result = result.fillna(fill_value)
            return result

    def _calculate_vwap(self, data):
        """Расчет VWAP"""
        typical_price = (data["high"] + data["low"] + data["close"]) / 3
        cumulative_tpv = (typical_price * data["volume"]).cumsum()
        cumulative_volume = data["volume"].cumsum()
        return self._safe_divide(cumulative_tpv, cumulative_volume)

    def _calculate_pvi(self, data):
        """Расчет Positive Volume Index"""
        pvi = pd.Series(index=data.index, dtype=float)
        pvi.iloc[0] = 1000

        for i in range(1, len(data)):
            if data["volume"].iloc[i] > data["volume"].iloc[i - 1]:
                pvi.iloc[i] = pvi.iloc[i - 1] * (1 + data["close"].pct_change().iloc[i])
            else:
                pvi.iloc[i] = pvi.iloc[i - 1]

        return pvi

    def _add_pattern_features(self, data, features):
        """Добавление паттернов свечей"""
        # Simplified pattern detection
        body = data["close"] - data["open"]
        body_size = np.abs(body)
        upper_shadow = data["high"] - np.maximum(data["open"], data["close"])
        lower_shadow = np.minimum(data["open"], data["close"]) - data["low"]

        # Hammer
        features["hammer"] = (
            (lower_shadow > 2 * body_size)
            & (upper_shadow < 0.1 * body_size)
            & (body > 0)
        ).astype(int)

        # Inverted hammer
        features["inverted_hammer"] = (
            (upper_shadow > 2 * body_size)
            & (lower_shadow < 0.1 * body_size)
            & (body > 0)
        ).astype(int)

        # Engulfing patterns
        prev_body = body.shift(1)
        features["bullish_engulfing"] = (
            (body > 0) & (prev_body < 0) & (body > np.abs(prev_body))
        ).astype(int)

        features["bearish_engulfing"] = (
            (body < 0) & (prev_body > 0) & (np.abs(body) > prev_body)
        ).astype(int)

        # Star patterns (simplified)
        features["morning_star"] = (
            (body.shift(2) < 0)
            & (np.abs(body.shift(1)) < 0.1 * np.abs(body.shift(2)))
            & (body > 0)
        ).astype(int)

        features["evening_star"] = (
            (body.shift(2) > 0)
            & (np.abs(body.shift(1)) < 0.1 * body.shift(2))
            & (body < 0)
        ).astype(int)

        # Soldiers and crows
        features["three_white_soldiers"] = (
            (body > 0) & (body.shift(1) > 0) & (body.shift(2) > 0)
        ).astype(int)

        features["three_black_crows"] = (
            (body < 0) & (body.shift(1) < 0) & (body.shift(2) < 0)
        ).astype(int)

        # Doji variations
        features["doji_star"] = (body_size < 0.001 * data["close"]).astype(int)

        # Shooting star
        features["shooting_star"] = (
            (upper_shadow > 2 * body_size)
            & (lower_shadow < 0.1 * body_size)
            & (body < 0)
        ).astype(int)

        # Hanging man
        features["hanging_man"] = (
            (lower_shadow > 2 * body_size)
            & (upper_shadow < 0.1 * body_size)
            & (body < 0)
        ).astype(int)

        # Harami
        features["harami"] = (
            (np.abs(body) < np.abs(prev_body))
            & (data["open"] < data["close"].shift(1))
            & (data["close"] > data["open"].shift(1))
        ).astype(int)

        # Piercing line
        features["piercing_line"] = (
            (body > 0)
            & (prev_body < 0)
            & (data["open"] < data["low"].shift(1))
            & (data["close"] > data["open"].shift(1) + prev_body / 2)
        ).astype(int)

        # Dark cloud
        features["dark_cloud"] = (
            (body < 0)
            & (prev_body > 0)
            & (data["open"] > data["high"].shift(1))
            & (data["close"] < data["close"].shift(1) - prev_body / 2)
        ).astype(int)

        # Simple patterns
        features["spinning_top"] = (
            (body_size < 0.1 * (data["high"] - data["low"]))
            & (upper_shadow > body_size)
            & (lower_shadow > body_size)
        ).astype(int)

        features["marubozu"] = (
            (upper_shadow < 0.01 * body_size) & (lower_shadow < 0.01 * body_size)
        ).astype(int)

        # Bar patterns
        features["inside_bar"] = (
            (data["high"] < data["high"].shift(1))
            & (data["low"] > data["low"].shift(1))
        ).astype(int)

        features["outside_bar"] = (
            (data["high"] > data["high"].shift(1))
            & (data["low"] < data["low"].shift(1))
        ).astype(int)

        # Pin bar
        features["pin_bar"] = (
            (upper_shadow > 2 * body_size) | (lower_shadow > 2 * body_size)
        ).astype(int)

        # Fakey pattern (simplified)
        features["fakey"] = (
            features["inside_bar"].shift(1) & features["outside_bar"]
        ).astype(int)

    def _calculate_entropy(self, series, window):
        """Расчет энтропии"""

        def entropy(x):
            if len(x) < 2:
                return 0
            hist, _ = np.histogram(x, bins=10)
            hist = hist[hist > 0]
            if len(hist) == 0:
                return 0
            probs = hist / hist.sum()
            return -np.sum(probs * np.log(probs + 1e-10))

        return series.rolling(window).apply(entropy)

    def _calculate_hurst(self, series, max_lag=20):
        """Расчет экспоненты Херста"""

        def hurst_exp(x):
            if len(x) < max_lag:
                return 0.5

            lags = range(2, min(max_lag, len(x)))
            tau = []

            for lag in lags:
                differences = x[lag:] - x[:-lag]
                tau.append(np.std(differences))

            if len(tau) < 2:
                return 0.5

            poly = np.polyfit(np.log(list(lags)), np.log(tau), 1)
            return poly[0]

        return series.rolling(50).apply(hurst_exp)

    def _calculate_partial_autocorr(self, series, lag):
        """Расчет частичной автокорреляции"""

        def partial_autocorr(x):
            if len(x) < lag + 2:
                return 0
            try:
                from statsmodels.tsa.stattools import pacf

                return pacf(x, nlags=lag)[lag]
            except:
                return 0

        return series.rolling(20).apply(partial_autocorr)

    def _determine_market_regime(self, features):
        """Определение рыночного режима"""
        # Simple market regime: 0=ranging, 1=trending up, -1=trending down
        trend = np.sign(features["sma_10"] - features["sma_50"])
        volatility = features["volatility_regime"]
        adx = features["adx_14"]

        regime = pd.Series(0, index=features.index)
        regime[(trend > 0) & (adx > 25)] = 1  # Trending up
        regime[(trend < 0) & (adx > 25)] = -1  # Trending down
        regime[adx <= 25] = 0  # Ranging

        return regime
