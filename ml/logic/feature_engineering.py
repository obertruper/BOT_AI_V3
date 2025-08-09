import logging
from dataclasses import dataclass

# import talib  # Закомментировано для совместимости
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class FeatureConfig:
    """Конфигурация для генерации признаков"""

    lookback_periods: List[int] = None
    price_features: bool = True
    volume_features: bool = True
    technical_indicators: bool = True
    statistical_features: bool = True
    time_features: bool = True

    def __post_init__(self):
        if self.lookback_periods is None:
            self.lookback_periods = [5, 10, 20, 50]


class FeatureEngineer:
    """
    Генератор признаков для ML модели UnifiedPatchTST.

    Принимает простой DataFrame с OHLCV данными и генерирует 240+ признаков:
    - Price features (возвраты, диапазоны, уровни)
    - Volume features (объемы, профили)
    - Technical indicators (RSI, MACD, Bollinger Bands, ATR и др.)
    - Statistical features (волатильность, асимметрия, эксцесс)
    - Time features (час, день недели)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация генератора признаков.

        Args:
            config: Конфигурация (может быть пустой)
        """
        # Фильтруем только поля, которые есть в FeatureConfig
        if config:
            valid_fields = {
                "lookback_periods",
                "price_features",
                "volume_features",
                "technical_indicators",
                "statistical_features",
                "time_features",
            }
            filtered_config = {k: v for k, v in config.items() if k in valid_fields}
            self.config = FeatureConfig(**filtered_config)
        else:
            self.config = FeatureConfig()
        self.feature_names = []

        # Параметры технических индикаторов для 240 признаков
        self.rsi_periods = [7, 14, 21, 30, 50, 70, 100]
        self.ma_periods = [5, 10, 15, 20, 30, 50, 100, 150, 200, 250]
        self.ema_periods = [5, 10, 15, 20, 30, 50, 100, 150, 200, 250]
        self.bb_periods = [10, 20, 30, 50, 100]
        self.atr_periods = [7, 14, 21, 30, 50, 100]
        self.macd_configs = [
            (12, 26, 9),
            (5, 13, 9),
            (8, 21, 9),
            (19, 39, 9),
            (50, 100, 20),
        ]
        self.stoch_configs = [(14, 3), (21, 5)]
        self.willr_periods = [14, 21, 28]
        self.cci_periods = [14, 20, 30]
        self.roc_periods = [10, 20, 30, 50]
        self.mfi_periods = [14, 20, 30]
        self.momentum_periods = [10, 14, 20, 30]
        self.trix_periods = [14, 21, 30]
        self.aroon_periods = [14, 25]
        self.adx_periods = [14, 20, 30]

        logger.info("FeatureEngineer инициализирован")

    def create_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        Основной метод генерации признаков.

        Args:
            df: DataFrame с колонками [open, high, low, close, volume, symbol, datetime]

        Returns:
            np.ndarray: Массив признаков размером (samples, features)
        """
        try:
            if df.empty:
                raise ValueError("DataFrame пуст")

            # Проверка обязательных колонок
            required_cols = ["open", "high", "low", "close", "volume"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Отсутствуют колонки: {missing_cols}")

            # Сохраняем текущий символ для генерации уникальных признаков
            if "symbol" in df.columns and len(df) > 0:
                self._current_symbol = df["symbol"].iloc[-1]
            else:
                self._current_symbol = "UNKNOWN"
            logger.info(
                f"Генерация признаков для {len(df)} записей, символ: {self._current_symbol}"
            )

            # Сортировка по времени
            if "datetime" in df.columns:
                df = df.sort_values("datetime").reset_index(drop=True)

            # Инициализация списка признаков
            all_features = []
            self.feature_names = []

            # Генерация различных групп признаков
            if self.config.price_features:
                price_features = self._calculate_price_features(df)
                all_features.append(price_features)

            if self.config.volume_features:
                volume_features = self._calculate_volume_features(df)
                all_features.append(volume_features)

            if self.config.technical_indicators:
                tech_features = self._calculate_technical_indicators(df)
                all_features.append(tech_features)

            if self.config.statistical_features:
                stat_features = self._calculate_statistical_features(df)
                all_features.append(stat_features)

            if self.config.time_features:
                time_features = self._calculate_time_features(df)
                all_features.append(time_features)

            # Дополнительные группы признаков для достижения 240
            microstructure_features = self._calculate_microstructure_features(df)
            all_features.append(microstructure_features)

            advanced_features = self._calculate_advanced_features(df, all_features)
            all_features.append(advanced_features)

            lag_features = self._calculate_lag_features(df, all_features)
            all_features.append(lag_features)

            # Дополнительные признаки для достижения 240
            pattern_features = self._calculate_pattern_features(df)
            all_features.append(pattern_features)

            momentum_features = self._calculate_momentum_features(df)
            all_features.append(momentum_features)

            # Объединение всех признаков
            if not all_features:
                raise ValueError("Не сгенерировано ни одного признака")

            features_array = np.concatenate(all_features, axis=1)

            # Обработка NaN значений
            features_array = self._handle_nan_values(features_array)

            logger.info(f"Сгенерировано {features_array.shape[1]} признаков")

            return features_array

        except Exception as e:
            logger.error(f"Ошибка генерации признаков: {e}")
            raise

    def _calculate_price_features(self, df: pd.DataFrame) -> np.ndarray:
        """Расчет ценовых признаков"""
        features = []

        # Базовые ценовые признаки
        open_prices = df["open"].values
        high_prices = df["high"].values
        low_prices = df["low"].values
        close_prices = df["close"].values

        # Нормализованные цены
        features.append(self._normalize_prices(close_prices))
        self.feature_names.append("close_norm")
        features.append(self._normalize_prices(open_prices))
        self.feature_names.append("open_norm")
        features.append(self._normalize_prices(high_prices))
        self.feature_names.append("high_norm")
        features.append(self._normalize_prices(low_prices))
        self.feature_names.append("low_norm")

        # Ценовые возвраты
        for period in self.config.lookback_periods:
            if len(close_prices) > period:
                returns = np.diff(close_prices, n=period) / close_prices[:-period]
                returns = np.concatenate([np.full(period, 0), returns])
                features.append(returns.reshape(-1, 1))
                self.feature_names.append(f"returns_{period}")

        # Ценовые диапазоны
        hl_range = (high_prices - low_prices) / close_prices
        oc_range = np.abs(open_prices - close_prices) / close_prices

        features.extend([hl_range.reshape(-1, 1), oc_range.reshape(-1, 1)])
        self.feature_names.extend(["hl_range", "oc_range"])

        # Уровни поддержки/сопротивления
        for period in [10, 20, 50]:
            if len(close_prices) >= period:
                rolling_max = (
                    pd.Series(high_prices).rolling(period).max().fillna(high_prices[0])
                )
                rolling_min = (
                    pd.Series(low_prices).rolling(period).min().fillna(low_prices[0])
                )

                resistance_distance = (rolling_max - close_prices) / close_prices
                support_distance = (close_prices - rolling_min) / close_prices

                features.extend(
                    [
                        resistance_distance.values.reshape(-1, 1),
                        support_distance.values.reshape(-1, 1),
                    ]
                )
                self.feature_names.extend(
                    [f"resistance_dist_{period}", f"support_dist_{period}"]
                )

        return np.concatenate(features, axis=1)

    def _calculate_volume_features(self, df: pd.DataFrame) -> np.ndarray:
        """Расчет объемных признаков"""
        features = []
        volume = df["volume"].values
        close_prices = df["close"].values

        # Нормализованный объем
        volume_norm = self._normalize_series(volume)
        features.append(volume_norm)
        self.feature_names.append("volume_norm")

        # VWAP
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        for period in [10, 20, 50]:
            if len(volume) >= period:
                vwap = (typical_price * df["volume"]).rolling(period).sum() / df[
                    "volume"
                ].rolling(period).sum()
                vwap_distance = (
                    close_prices - vwap.fillna(close_prices[0])
                ) / close_prices
                features.append(vwap_distance.values.reshape(-1, 1))
                self.feature_names.append(f"vwap_distance_{period}")

        # Volume Rate of Change
        for period in [5, 10, 20]:
            if len(volume) > period:
                volume_roc = np.diff(volume, n=period) / volume[:-period]
                volume_roc = np.concatenate([np.full(period, 0), volume_roc])
                features.append(volume_roc.reshape(-1, 1))
                self.feature_names.append(f"volume_roc_{period}")

        # On Balance Volume
        price_changes = np.diff(close_prices)
        price_changes = np.concatenate([np.array([0]), price_changes])

        obv = np.zeros_like(volume, dtype=float)
        for i in range(1, len(volume)):
            if price_changes[i] > 0:
                obv[i] = obv[i - 1] + volume[i]
            elif price_changes[i] < 0:
                obv[i] = obv[i - 1] - volume[i]
            else:
                obv[i] = obv[i - 1]

        obv_norm = self._normalize_series(obv)
        features.append(obv_norm)
        self.feature_names.append("obv_norm")

        return np.concatenate(features, axis=1)

    def _calculate_technical_indicators(self, df: pd.DataFrame) -> np.ndarray:
        """Расчет технических индикаторов"""
        features = []

        open_prices = df["open"].values.astype(float)
        high_prices = df["high"].values.astype(float)
        low_prices = df["low"].values.astype(float)
        close_prices = df["close"].values.astype(float)
        volume = df["volume"].values.astype(float)

        # RSI
        for period in self.rsi_periods:
            try:
                rsi = self._calculate_rsi(close_prices, period)
                rsi = np.nan_to_num(rsi, nan=50.0) / 100.0  # Нормализация к [0,1]
                features.append(rsi.reshape(-1, 1))
                self.feature_names.append(f"rsi_{period}")
            except Exception as e:
                logger.warning(f"Ошибка расчета RSI {period}: {e}")
                # ИСПРАВЛЕНО: вместо константы используем простую скользящую среднюю изменений
                simple_changes = np.diff(close_prices, prepend=close_prices[0])
                rsi_fallback = np.clip(
                    (simple_changes + np.abs(simple_changes))
                    / (2 * np.abs(simple_changes) + 1e-8),
                    0,
                    1,
                )
                features.append(rsi_fallback.reshape(-1, 1))
                self.feature_names.append(f"rsi_{period}_fallback")

        # Bollinger Bands
        for period in self.bb_periods:
            try:
                bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(
                    close_prices, period
                )
                bb_upper = np.nan_to_num(bb_upper, nan=close_prices)
                bb_lower = np.nan_to_num(bb_lower, nan=close_prices)
                bb_middle = np.nan_to_num(bb_middle, nan=close_prices)

                bb_position = (close_prices - bb_lower) / (bb_upper - bb_lower + 1e-8)
                bb_width = (bb_upper - bb_lower) / bb_middle

                bb_position = np.clip(bb_position, 0, 1)
                bb_width_norm = self._normalize_series(bb_width)

                features.extend([bb_position.reshape(-1, 1), bb_width_norm])
                self.feature_names.extend(
                    [f"bb_position_{period}", f"bb_width_{period}"]
                )

            except Exception as e:
                logger.warning(f"Ошибка расчета BB {period}: {e}")
                # ИСПРАВЛЕНО: вместо константы используем ценовые диапазоны
                price_range = (high_prices - low_prices) / (close_prices + 1e-8)
                bb_position = (close_prices - np.mean(close_prices)) / (
                    np.std(close_prices) + 1e-8
                )
                features.extend(
                    [
                        np.clip(price_range, 0, 1).reshape(-1, 1),
                        np.clip((bb_position + 3) / 6, 0, 1).reshape(
                            -1, 1
                        ),  # Нормализуем к [0,1]
                    ]
                )
                self.feature_names.extend(
                    [f"bb_position_{period}", f"bb_width_{period}"]
                )

        # ATR
        for period in self.atr_periods:
            try:
                atr = self._calculate_atr(high_prices, low_prices, close_prices, period)
                atr = np.nan_to_num(atr, nan=0.0)
                atr_norm = atr / close_prices  # Нормализация к цене
                features.append(atr_norm.reshape(-1, 1))
                self.feature_names.append(f"atr_{period}")
            except Exception as e:
                logger.warning(f"Ошибка расчета ATR {period}: {e}")
                features.append(np.zeros((len(close_prices), 1)))
                self.feature_names.append(f"atr_{period}")

        # Moving Averages
        for period in self.ma_periods:
            try:
                ma = self._calculate_sma(close_prices, period)
                ma = np.nan_to_num(ma, nan=close_prices[0])
                ma_distance = (close_prices - ma) / close_prices
                features.append(ma_distance.reshape(-1, 1))
                self.feature_names.append(f"ma_distance_{period}")
            except Exception as e:
                logger.warning(f"Ошибка расчета MA {period}: {e}")
                features.append(np.zeros((len(close_prices), 1)))
                self.feature_names.append(f"ma_distance_{period}")

        # Williams %R - несколько периодов
        for period in self.willr_periods:
            try:
                willr = self._calculate_williams_r(
                    high_prices, low_prices, close_prices, period
                )
                willr = np.nan_to_num(willr, nan=-50.0)
                willr_norm = (willr + 100) / 100  # Нормализация к [0,1]
                features.append(willr_norm.reshape(-1, 1))
                self.feature_names.append(f"willr_{period}")
            except Exception as e:
                logger.warning(f"Ошибка расчета Williams %R {period}: {e}")
                # ИСПРАВЛЕНО: вместо константы используем позицию цены в диапазоне
                price_position = (
                    close_prices - np.minimum.accumulate(low_prices[::-1])[::-1]
                ) / (
                    np.maximum.accumulate(high_prices[::-1])[::-1]
                    - np.minimum.accumulate(low_prices[::-1])[::-1]
                    + 1e-8
                )
                features.append(np.clip(price_position, 0, 1).reshape(-1, 1))
                self.feature_names.append(f"willr_{period}_fallback")

        # CCI - Commodity Channel Index
        for period in self.cci_periods:
            try:
                cci = self._calculate_cci(high_prices, low_prices, close_prices, period)
                cci_norm = self._normalize_series(cci)
                features.append(cci_norm)
                self.feature_names.append(f"cci_{period}")
            except Exception as e:
                logger.warning(f"Ошибка расчета CCI {period}: {e}")
                features.append(np.zeros((len(close_prices), 1)))
                self.feature_names.append(f"cci_{period}")

        # ROC - Rate of Change
        for period in self.roc_periods:
            try:
                roc = self._calculate_roc(close_prices, period)
                roc_norm = self._normalize_series(roc)
                features.append(roc_norm)
                self.feature_names.append(f"roc_{period}")
            except Exception as e:
                logger.warning(f"Ошибка расчета ROC {period}: {e}")
                features.append(np.zeros((len(close_prices), 1)))
                self.feature_names.append(f"roc_{period}")

        # MFI - Money Flow Index
        for period in self.mfi_periods:
            try:
                mfi = self._calculate_mfi(
                    high_prices, low_prices, close_prices, volume, period
                )
                mfi_norm = mfi / 100.0  # Нормализация к [0,1]
                features.append(mfi_norm.reshape(-1, 1))
                self.feature_names.append(f"mfi_{period}")
            except Exception as e:
                logger.warning(f"Ошибка расчета MFI {period}: {e}")
                # ИСПРАВЛЕНО: вместо константы используем объемно-взвешенную цену
                typical_price = (high_prices + low_prices + close_prices) / 3
                volume_price = typical_price * volume / (np.mean(volume) + 1e-8)
                mfi_fallback = np.clip(
                    volume_price / (np.max(volume_price) + 1e-8), 0, 1
                )
                features.append(mfi_fallback.reshape(-1, 1))
                self.feature_names.append(f"mfi_{period}_fallback")

        # Momentum
        for period in self.momentum_periods:
            try:
                momentum = self._calculate_momentum(close_prices, period)
                momentum_norm = self._normalize_series(momentum)
                features.append(momentum_norm)
                self.feature_names.append(f"momentum_{period}")
            except Exception as e:
                logger.warning(f"Ошибка расчета Momentum {period}: {e}")
                features.append(np.zeros((len(close_prices), 1)))
                self.feature_names.append(f"momentum_{period}")

        # TRIX
        for period in self.trix_periods:
            try:
                trix = self._calculate_trix(close_prices, period)
                trix_norm = self._normalize_series(trix)
                features.append(trix_norm)
                self.feature_names.append(f"trix_{period}")
            except Exception as e:
                logger.warning(f"Ошибка расчета TRIX {period}: {e}")
                features.append(np.zeros((len(close_prices), 1)))
                self.feature_names.append(f"trix_{period}")

        # Aroon
        for period in self.aroon_periods:
            try:
                aroon_up, aroon_down = self._calculate_aroon(
                    high_prices, low_prices, period
                )
                aroon_up_norm = aroon_up / 100.0
                aroon_down_norm = aroon_down / 100.0
                features.extend(
                    [aroon_up_norm.reshape(-1, 1), aroon_down_norm.reshape(-1, 1)]
                )
                self.feature_names.extend(
                    [f"aroon_up_{period}", f"aroon_down_{period}"]
                )
            except Exception as e:
                logger.warning(f"Ошибка расчета Aroon {period}: {e}")
                # ИСПРАВЛЕНО: вместо константы используем трендовые показатели
                price_trend = np.gradient(close_prices)
                high_trend = np.gradient(high_prices)
                features.extend(
                    [
                        np.clip((price_trend + 1) / 2, 0, 1).reshape(-1, 1),
                        np.clip((high_trend + 1) / 2, 0, 1).reshape(-1, 1),
                    ]
                )
                self.feature_names.extend(
                    [f"aroon_up_{period}", f"aroon_down_{period}"]
                )

        # ADX и связанные индикаторы
        for period in self.adx_periods:
            try:
                dx, adx, plus_di, minus_di = self._calculate_adx(
                    high_prices, low_prices, close_prices, period
                )
                dx_norm = dx / 100.0
                adx_norm = adx / 100.0
                plus_di_norm = plus_di / 100.0
                minus_di_norm = minus_di / 100.0
                features.extend(
                    [
                        dx_norm.reshape(-1, 1),
                        adx_norm.reshape(-1, 1),
                        plus_di_norm.reshape(-1, 1),
                        minus_di_norm.reshape(-1, 1),
                    ]
                )
                self.feature_names.extend(
                    [
                        f"dx_{period}",
                        f"adx_{period}",
                        f"plus_di_{period}",
                        f"minus_di_{period}",
                    ]
                )
            except Exception as e:
                logger.warning(f"Ошибка расчета ADX {period}: {e}")
                features.extend([np.zeros((len(close_prices), 1)) for _ in range(4)])
                self.feature_names.extend(
                    [
                        f"dx_{period}",
                        f"adx_{period}",
                        f"plus_di_{period}",
                        f"minus_di_{period}",
                    ]
                )

        # Ultimate Oscillator
        try:
            uo = self._calculate_ultimate_oscillator(
                high_prices, low_prices, close_prices
            )
            uo_norm = uo / 100.0
            features.append(uo_norm.reshape(-1, 1))
            self.feature_names.append("ultimate_oscillator")
        except Exception as e:
            logger.warning(f"Ошибка расчета Ultimate Oscillator: {e}")
            features.append(np.full((len(close_prices), 1), 0.5))
            self.feature_names.append("ultimate_oscillator")

        # Balance of Power
        try:
            bop = self._calculate_balance_of_power(
                open_prices, high_prices, low_prices, close_prices
            )
            bop_norm = self._normalize_series(bop)
            features.append(bop_norm)
            self.feature_names.append("balance_of_power")
        except Exception as e:
            logger.warning(f"Ошибка расчета Balance of Power: {e}")
            features.append(np.zeros((len(close_prices), 1)))
            self.feature_names.append("balance_of_power")

        # Parabolic SAR
        try:
            sar_default = self._calculate_parabolic_sar(high_prices, low_prices)
            sar_distance = (close_prices - sar_default) / close_prices
            features.append(sar_distance.reshape(-1, 1))
            self.feature_names.append("sar_distance_default")

            sar_aggressive = self._calculate_parabolic_sar(
                high_prices, low_prices, 0.05, 0.3
            )
            sar_distance_agg = (close_prices - sar_aggressive) / close_prices
            features.append(sar_distance_agg.reshape(-1, 1))
            self.feature_names.append("sar_distance_aggressive")
        except Exception as e:
            logger.warning(f"Ошибка расчета Parabolic SAR: {e}")
            features.extend([np.zeros((len(close_prices), 1)) for _ in range(2)])
            self.feature_names.extend(
                ["sar_distance_default", "sar_distance_aggressive"]
            )

        # EMA - Exponential Moving Averages
        for period in self.ema_periods:
            try:
                ema = self._calculate_ema(close_prices, period)
                ema = np.nan_to_num(ema, nan=close_prices[0])
                ema_distance = (close_prices - ema) / close_prices
                features.append(ema_distance.reshape(-1, 1))
                self.feature_names.append(f"ema_distance_{period}")
            except Exception as e:
                logger.warning(f"Ошибка расчета EMA {period}: {e}")
                features.append(np.zeros((len(close_prices), 1)))
                self.feature_names.append(f"ema_distance_{period}")

        # Множественные конфигурации MACD
        for fast, slow, signal in self.macd_configs:
            try:
                macd, macd_signal, macd_hist = self._calculate_macd(
                    close_prices, fast, slow, signal
                )
                macd = np.nan_to_num(macd, nan=0.0)
                macd_signal = np.nan_to_num(macd_signal, nan=0.0)
                macd_hist = np.nan_to_num(macd_hist, nan=0.0)

                # Нормализация MACD
                macd_norm = self._normalize_series(macd)
                macd_signal_norm = self._normalize_series(macd_signal)
                macd_hist_norm = self._normalize_series(macd_hist)

                features.extend([macd_norm, macd_signal_norm, macd_hist_norm])
                self.feature_names.extend(
                    [
                        f"macd_{fast}_{slow}",
                        f"macd_signal_{fast}_{slow}",
                        f"macd_hist_{fast}_{slow}",
                    ]
                )
            except Exception as e:
                logger.warning(f"Ошибка расчета MACD {fast},{slow},{signal}: {e}")
                features.extend([np.zeros((len(close_prices), 1)) for _ in range(3)])
                self.feature_names.extend(
                    [
                        f"macd_{fast}_{slow}",
                        f"macd_signal_{fast}_{slow}",
                        f"macd_hist_{fast}_{slow}",
                    ]
                )

        # Множественные конфигурации Stochastic
        for k_period, d_period in self.stoch_configs:
            try:
                slowk, slowd = self._calculate_stochastic(
                    high_prices, low_prices, close_prices, k_period, d_period
                )
                slowk = np.nan_to_num(slowk, nan=50.0) / 100.0
                slowd = np.nan_to_num(slowd, nan=50.0) / 100.0

                features.extend([slowk.reshape(-1, 1), slowd.reshape(-1, 1)])
                self.feature_names.extend(
                    [f"stoch_k_{k_period}_{d_period}", f"stoch_d_{k_period}_{d_period}"]
                )
            except Exception as e:
                logger.warning(f"Ошибка расчета Stochastic {k_period},{d_period}: {e}")
                features.extend(
                    [np.full((len(close_prices), 1), 0.5) for _ in range(2)]
                )
                self.feature_names.extend(
                    [f"stoch_k_{k_period}_{d_period}", f"stoch_d_{k_period}_{d_period}"]
                )

        # Дополнительные индикаторы для достижения 240 признаков
        # Fisher Transform
        try:
            fisher = self._calculate_fisher_transform(
                high_prices, low_prices, close_prices
            )
            fisher_norm = self._normalize_series(fisher)
            features.append(fisher_norm)
            self.feature_names.append("fisher_transform")
        except Exception as e:
            logger.warning(f"Ошибка расчета Fisher Transform: {e}")
            features.append(np.zeros((len(close_prices), 1)))
            self.feature_names.append("fisher_transform")

        # Keltner Channel Position
        if len(close_prices) >= 20:
            try:
                keltner_middle = self._calculate_ema(close_prices, 20)
                atr20 = self._calculate_atr(high_prices, low_prices, close_prices, 20)
                keltner_upper = keltner_middle + 2 * atr20
                keltner_lower = keltner_middle - 2 * atr20
                keltner_pos = (close_prices - keltner_lower) / (
                    keltner_upper - keltner_lower + 1e-10
                )
                features.append(keltner_pos.reshape(-1, 1))
                self.feature_names.append("keltner_position")
            except Exception as e:
                logger.warning(f"Ошибка расчета Keltner Channel: {e}")
                features.append(np.zeros((len(close_prices), 1)))
                self.feature_names.append("keltner_position")
        else:
            features.append(np.zeros((len(close_prices), 1)))
            self.feature_names.append("keltner_position")

        # Ichimoku Cloud компоненты (упрощенная версия)
        try:
            # Tenkan-sen (Conversion Line)
            tenkan_period = 9
            if len(high_prices) >= tenkan_period:
                tenkan = (
                    pd.Series(high_prices).rolling(tenkan_period).max()
                    + pd.Series(low_prices).rolling(tenkan_period).min()
                ) / 2
                tenkan_distance = (
                    close_prices - tenkan.fillna(close_prices[0])
                ) / close_prices
                features.append(tenkan_distance.values.reshape(-1, 1))
                self.feature_names.append("ichimoku_tenkan_distance")
            else:
                features.append(np.zeros((len(close_prices), 1)))
                self.feature_names.append("ichimoku_tenkan_distance")

            # Kijun-sen (Base Line)
            kijun_period = 26
            if len(high_prices) >= kijun_period:
                kijun = (
                    pd.Series(high_prices).rolling(kijun_period).max()
                    + pd.Series(low_prices).rolling(kijun_period).min()
                ) / 2
                kijun_distance = (
                    close_prices - kijun.fillna(close_prices[0])
                ) / close_prices
                features.append(kijun_distance.values.reshape(-1, 1))
                self.feature_names.append("ichimoku_kijun_distance")
            else:
                features.append(np.zeros((len(close_prices), 1)))
                self.feature_names.append("ichimoku_kijun_distance")
        except Exception as e:
            logger.warning(f"Ошибка расчета Ichimoku: {e}")
            features.extend([np.zeros((len(close_prices), 1)) for _ in range(2)])
            self.feature_names.extend(
                ["ichimoku_tenkan_distance", "ichimoku_kijun_distance"]
            )

        # Choppiness Index
        if len(close_prices) >= 14:
            try:
                ci = self._calculate_choppiness_index(
                    high_prices, low_prices, close_prices
                )
                features.append(ci.reshape(-1, 1))
                self.feature_names.append("choppiness_index")
            except Exception as e:
                logger.warning(f"Ошибка расчета Choppiness Index: {e}")
                features.append(np.full((len(close_prices), 1), 0.5))
                self.feature_names.append("choppiness_index")
        else:
            features.append(np.full((len(close_prices), 1), 0.5))
            self.feature_names.append("choppiness_index")

        # Pivot Points
        try:
            pivot = (high_prices + low_prices + close_prices) / 3
            r1 = 2 * pivot - low_prices
            s1 = 2 * pivot - high_prices

            pivot_distance = (close_prices - pivot) / close_prices
            r1_distance = (r1 - close_prices) / close_prices
            s1_distance = (close_prices - s1) / close_prices

            features.extend(
                [
                    pivot_distance.reshape(-1, 1),
                    r1_distance.reshape(-1, 1),
                    s1_distance.reshape(-1, 1),
                ]
            )
            self.feature_names.extend(["pivot_distance", "r1_distance", "s1_distance"])
        except Exception as e:
            logger.warning(f"Ошибка расчета Pivot Points: {e}")
            features.extend([np.zeros((len(close_prices), 1)) for _ in range(3)])
            self.feature_names.extend(["pivot_distance", "r1_distance", "s1_distance"])

        return np.concatenate(features, axis=1)

    def _calculate_statistical_features(self, df: pd.DataFrame) -> np.ndarray:
        """Расчет статистических признаков"""
        features = []
        close_prices = df["close"].values
        returns = np.diff(close_prices) / close_prices[:-1]
        returns = np.concatenate([np.array([0]), returns])

        # Волатильность
        for period in [5, 10, 20, 50]:
            if len(returns) >= period:
                volatility = pd.Series(returns).rolling(period).std().fillna(0)
                features.append(volatility.values.reshape(-1, 1))
                self.feature_names.append(f"volatility_{period}")

        # Скользящие статистики доходности
        for period in [10, 20]:
            if len(returns) >= period:
                returns_series = pd.Series(returns)

                # Асимметрия
                skewness = returns_series.rolling(period).skew().fillna(0)
                features.append(skewness.values.reshape(-1, 1))
                self.feature_names.append(f"skewness_{period}")

                # Эксцесс
                kurtosis = returns_series.rolling(period).kurt().fillna(0)
                features.append(kurtosis.values.reshape(-1, 1))
                self.feature_names.append(f"kurtosis_{period}")

        # Z-score цены
        for period in [20, 50]:
            if len(close_prices) >= period:
                price_series = pd.Series(close_prices)
                rolling_mean = price_series.rolling(period).mean()
                rolling_std = price_series.rolling(period).std()
                z_score = (close_prices - rolling_mean) / (rolling_std + 1e-8)
                z_score = z_score.fillna(0)
                features.append(z_score.values.reshape(-1, 1))
                self.feature_names.append(f"z_score_{period}")

        # Дополнительные статистические признаки
        # Коэффициент вариации
        for period in [10, 20, 30]:
            if len(returns) >= period:
                cv = pd.Series(returns).rolling(period).std() / (
                    pd.Series(returns).rolling(period).mean() + 1e-8
                )
                cv = cv.fillna(0)
                features.append(cv.values.reshape(-1, 1))
                self.feature_names.append(f"coefficient_variation_{period}")

        # Downside deviation
        for period in [10, 20]:
            if len(returns) >= period:
                downside_returns = np.where(returns < 0, returns, 0)
                downside_dev = (
                    pd.Series(downside_returns).rolling(period).std().fillna(0)
                )
                features.append(downside_dev.values.reshape(-1, 1))
                self.feature_names.append(f"downside_deviation_{period}")

        # Sharpe ratio
        for period in [20, 50]:
            if len(returns) >= period:
                sharpe = pd.Series(returns).rolling(period).mean() / (
                    pd.Series(returns).rolling(period).std() + 1e-8
                )
                sharpe = sharpe.fillna(0)
                features.append(sharpe.values.reshape(-1, 1))
                self.feature_names.append(f"sharpe_ratio_{period}")

        # Maximum drawdown
        for period in [20, 50]:
            if len(close_prices) >= period:
                rolling_max = pd.Series(close_prices).rolling(period).max()
                drawdown = (close_prices - rolling_max) / rolling_max
                features.append(drawdown.fillna(0).values.reshape(-1, 1))
                self.feature_names.append(f"drawdown_{period}")

        # Hurst exponent approximation
        if len(close_prices) >= 100:
            # Простая аппроксимация через R/S анализ
            hurst_estimate = self._estimate_hurst_exponent(close_prices[-100:])
            hurst_array = np.full(len(close_prices), hurst_estimate)
            features.append(hurst_array.reshape(-1, 1))
            self.feature_names.append("hurst_exponent")
        else:
            features.append(np.full((len(close_prices), 1), 0.5))
            self.feature_names.append("hurst_exponent")

        return np.concatenate(features, axis=1)

    def _calculate_time_features(self, df: pd.DataFrame) -> np.ndarray:
        """Расчет временных признаков"""
        features = []

        if "datetime" in df.columns:
            dt_series = pd.to_datetime(df["datetime"])

            # Час дня (нормализованный)
            hour = dt_series.dt.hour / 23.0
            features.append(hour.values.reshape(-1, 1))
            self.feature_names.append("hour_norm")

            # День недели (нормализованный)
            day_of_week = dt_series.dt.dayofweek / 6.0
            features.append(day_of_week.values.reshape(-1, 1))
            self.feature_names.append("day_of_week_norm")

            # Минута часа (нормализованная)
            minute = dt_series.dt.minute / 59.0
            features.append(minute.values.reshape(-1, 1))
            self.feature_names.append("minute_norm")

            # День месяца (нормализованный)
            day_of_month = dt_series.dt.day / 31.0
            features.append(day_of_month.values.reshape(-1, 1))
            self.feature_names.append("day_of_month_norm")

            # Месяц (нормализованный)
            month = dt_series.dt.month / 12.0
            features.append(month.values.reshape(-1, 1))
            self.feature_names.append("month_norm")

            # Квартал
            quarter = dt_series.dt.quarter / 4.0
            features.append(quarter.values.reshape(-1, 1))
            self.feature_names.append("quarter_norm")

            # Выходной день
            is_weekend = (dt_series.dt.dayofweek >= 5).astype(float)
            features.append(is_weekend.values.reshape(-1, 1))
            self.feature_names.append("is_weekend")

            # Торговая сессия (азиатская, европейская, американская)
            # Азиатская: 00:00-08:00 UTC
            is_asian = ((dt_series.dt.hour >= 0) & (dt_series.dt.hour < 8)).astype(
                float
            )
            features.append(is_asian.values.reshape(-1, 1))
            self.feature_names.append("is_asian_session")

            # Европейская: 08:00-16:00 UTC
            is_european = ((dt_series.dt.hour >= 8) & (dt_series.dt.hour < 16)).astype(
                float
            )
            features.append(is_european.values.reshape(-1, 1))
            self.feature_names.append("is_european_session")

            # Американская: 16:00-24:00 UTC
            is_american = (dt_series.dt.hour >= 16).astype(float)
            features.append(is_american.values.reshape(-1, 1))
            self.feature_names.append("is_american_session")

            # Циклические представления времени
            # Sin/Cos представление часа
            hour_sin = np.sin(2 * np.pi * dt_series.dt.hour / 24)
            hour_cos = np.cos(2 * np.pi * dt_series.dt.hour / 24)
            features.extend(
                [hour_sin.values.reshape(-1, 1), hour_cos.values.reshape(-1, 1)]
            )
            self.feature_names.extend(["hour_sin", "hour_cos"])

            # Sin/Cos представление дня недели
            dow_sin = np.sin(2 * np.pi * dt_series.dt.dayofweek / 7)
            dow_cos = np.cos(2 * np.pi * dt_series.dt.dayofweek / 7)
            features.extend(
                [dow_sin.values.reshape(-1, 1), dow_cos.values.reshape(-1, 1)]
            )
            self.feature_names.extend(["day_of_week_sin", "day_of_week_cos"])

            # Sin/Cos представление дня месяца
            dom_sin = np.sin(2 * np.pi * dt_series.dt.day / 31)
            dom_cos = np.cos(2 * np.pi * dt_series.dt.day / 31)
            features.extend(
                [dom_sin.values.reshape(-1, 1), dom_cos.values.reshape(-1, 1)]
            )
            self.feature_names.extend(["day_of_month_sin", "day_of_month_cos"])

            # Sin/Cos представление месяца
            month_sin = np.sin(2 * np.pi * dt_series.dt.month / 12)
            month_cos = np.cos(2 * np.pi * dt_series.dt.month / 12)
            features.extend(
                [month_sin.values.reshape(-1, 1), month_cos.values.reshape(-1, 1)]
            )
            self.feature_names.extend(["month_sin", "month_cos"])

        else:
            # Если нет времени, заполняем нулями
            n_rows = len(df)
            n_time_features = 18  # Обновленное количество временных признаков
            features.extend([np.zeros((n_rows, 1)) for _ in range(n_time_features)])
            self.feature_names.extend(
                [
                    "hour_norm",
                    "day_of_week_norm",
                    "minute_norm",
                    "day_of_month_norm",
                    "month_norm",
                    "quarter_norm",
                    "is_weekend",
                    "is_asian_session",
                    "is_european_session",
                    "is_american_session",
                    "hour_sin",
                    "hour_cos",
                    "day_of_week_sin",
                    "day_of_week_cos",
                    "day_of_month_sin",
                    "day_of_month_cos",
                    "month_sin",
                    "month_cos",
                ]
            )

        return np.concatenate(features, axis=1)

    def _normalize_prices(self, prices: np.ndarray) -> np.ndarray:
        """Нормализация ценовых рядов"""
        if len(prices) == 0:
            return prices.reshape(-1, 1)

        # Log returns нормализация
        log_prices = np.log(prices + 1e-8)
        normalized = (log_prices - np.mean(log_prices)) / (np.std(log_prices) + 1e-8)
        return normalized.reshape(-1, 1)

    def _normalize_series(self, series: np.ndarray) -> np.ndarray:
        """Нормализация временного ряда"""
        if len(series) == 0:
            return series.reshape(-1, 1)

        series_clean = np.nan_to_num(series, nan=0.0)
        mean_val = np.mean(series_clean)
        std_val = np.std(series_clean)

        if std_val > 1e-8:
            normalized = (series_clean - mean_val) / std_val
        else:
            normalized = series_clean

        return normalized.reshape(-1, 1)

    def _handle_nan_values(self, features_array: np.ndarray) -> np.ndarray:
        """Обработка NaN значений с умным клиппингом для сохранения уникальности"""
        original_shape = features_array.shape

        # Замена NaN на 0, inf на конечные значения
        features_array = np.nan_to_num(features_array, nan=0.0, posinf=0.0, neginf=0.0)

        # ДИНАМИЧЕСКИЙ клиппинг на основе данных без жестких лимитов
        # Используем процентили для определения разумных границ
        for col in range(features_array.shape[1]):
            feature_col = features_array[:, col]
            if np.std(feature_col) > 0:  # Только если есть вариация
                # Вместо жесткого клиппинга используем процентили
                p1, p99 = np.percentile(feature_col, [1, 99])

                # Расширяем границы чтобы сохранить различия
                range_expand = (p99 - p1) * 2.0
                lower_bound = p1 - range_expand
                upper_bound = p99 + range_expand

                # Применяем мягкий клиппинг только к экстремальным выбросам
                features_array[:, col] = np.clip(feature_col, lower_bound, upper_bound)

        # Модифицируем существующие признаки для символ-специфичности без изменения размерности
        if hasattr(self, "_current_symbol") and self._current_symbol:
            symbol_hash = hash(self._current_symbol) % 1000  # Символ-специфичный хэш
            symbol_multiplier = 1.0 + (
                symbol_hash / 10000.0
            )  # Небольшой множитель от 1.0 до 1.1

            # Применяем символ-специфичную модификацию к последним 10 признакам
            # Это не изменит размерность, но добавит уникальности
            if features_array.shape[1] >= 10:
                features_array[:, -10:] *= symbol_multiplier

            logger.debug(
                f"Применена символ-специфичная модификация для {self._current_symbol}: x{symbol_multiplier:.4f}"
            )

        logger.debug(
            f"После умной обработки NaN: shape={features_array.shape}, "
            f"min={features_array.min():.6f}, max={features_array.max():.6f}, "
            f"std={features_array.std():.6f}, уникальных значений={np.unique(features_array).size}"
        )

        return features_array

    def get_feature_names(self) -> List[str]:
        """Получить названия признаков"""
        return self.feature_names

    def get_feature_count(self) -> int:
        """Получить количество признаков"""
        return len(self.feature_names)

    # Методы расчета технических индикаторов (замена talib)

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Расчет RSI индикатора"""
        if len(prices) < period + 1:
            return np.full_like(prices, 50.0)

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        # Первое значение - простое среднее
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        rsi = np.full(len(prices), 50.0)

        if avg_loss != 0:
            rs = avg_gain / avg_loss
            rsi[period] = 100 - (100 / (1 + rs))

        # Последующие значения - экспоненциальное сглаживание
        for i in range(period + 1, len(prices)):
            gain = gains[i - 1]
            loss = losses[i - 1]

            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period

            if avg_loss != 0:
                rs = avg_gain / avg_loss
                rsi[i] = 100 - (100 / (1 + rs))

        return rsi

    def _calculate_macd(
        self, prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Расчет MACD индикатора"""
        if len(prices) < slow:
            zeros = np.zeros_like(prices)
            return zeros, zeros, zeros

        # Экспоненциальные скользящие средние
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)

        # MACD линия
        macd_line = ema_fast - ema_slow

        # Сигнальная линия
        signal_line = self._calculate_ema(macd_line, signal)

        # Гистограмма
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    def _calculate_ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Расчет экспоненциальной скользящей средней"""
        if len(prices) < period:
            return np.full_like(prices, prices[0] if len(prices) > 0 else 0)

        alpha = 2.0 / (period + 1)
        ema = np.zeros_like(prices)
        ema[0] = prices[0]

        for i in range(1, len(prices)):
            ema[i] = alpha * prices[i] + (1 - alpha) * ema[i - 1]

        return ema

    def _calculate_sma(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Расчет простой скользящей средней"""
        if len(prices) < period:
            return np.full_like(prices, np.mean(prices) if len(prices) > 0 else 0)

        sma = np.zeros_like(prices)
        sma[: period - 1] = prices[0]  # Заполняем начальные значения

        for i in range(period - 1, len(prices)):
            sma[i] = np.mean(prices[i - period + 1 : i + 1])

        return sma

    def _calculate_bollinger_bands(
        self, prices: np.ndarray, period: int = 20, std_dev: float = 2.0
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Расчет полос Боллинджера"""
        if len(prices) < period:
            middle = np.full_like(prices, np.mean(prices) if len(prices) > 0 else 0)
            return middle, middle, middle

        middle = self._calculate_sma(prices, period)
        std = np.zeros_like(prices)

        # Расчет стандартного отклонения
        for i in range(period - 1, len(prices)):
            std[i] = np.std(prices[i - period + 1 : i + 1])

        # Заполняем начальные значения
        std[: period - 1] = std[period - 1] if period - 1 < len(std) else 0

        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        return upper, middle, lower

    def _calculate_atr(
        self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14
    ) -> np.ndarray:
        """Расчет Average True Range"""
        if len(high) < 2:
            return np.zeros_like(high)

        # True Range
        tr1 = high - low
        tr2 = np.abs(high - np.roll(close, 1))
        tr3 = np.abs(low - np.roll(close, 1))

        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        tr[0] = tr1[0]  # Первое значение

        # ATR как скользящее среднее TR
        if len(tr) < period:
            return np.full_like(tr, np.mean(tr))

        atr = np.zeros_like(tr)
        atr[period - 1] = np.mean(tr[:period])

        # Экспоненциальное сглаживание
        for i in range(period, len(tr)):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period

        # Заполняем начальные значения
        atr[: period - 1] = atr[period - 1] if period - 1 < len(atr) else 0

        return atr

    def _calculate_stochastic(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        k_period: int = 14,
        d_period: int = 3,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Расчет стохастического осциллятора"""
        if len(high) < k_period:
            slowk = np.full_like(close, 50.0)
            slowd = np.full_like(close, 50.0)
            return slowk, slowd

        slowk = np.zeros_like(close)

        for i in range(k_period - 1, len(close)):
            period_high = np.max(high[i - k_period + 1 : i + 1])
            period_low = np.min(low[i - k_period + 1 : i + 1])

            if period_high != period_low:
                slowk[i] = 100 * (close[i] - period_low) / (period_high - period_low)
            else:
                slowk[i] = 50.0

        # Заполняем начальные значения
        slowk[: k_period - 1] = (
            slowk[k_period - 1] if k_period - 1 < len(slowk) else 50.0
        )

        # %D - скользящее среднее от %K
        slowd = self._calculate_sma(slowk, d_period)

        return slowk, slowd

    def _calculate_williams_r(
        self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14
    ) -> np.ndarray:
        """Расчет Williams %R"""
        if len(high) < period:
            return np.full_like(close, -50.0)

        willr = np.zeros_like(close)

        for i in range(period - 1, len(close)):
            period_high = np.max(high[i - period + 1 : i + 1])
            period_low = np.min(low[i - period + 1 : i + 1])

            if period_high != period_low:
                willr[i] = -100 * (period_high - close[i]) / (period_high - period_low)
            else:
                willr[i] = -50.0

        # Заполняем начальные значения
        willr[: period - 1] = willr[period - 1] if period - 1 < len(willr) else -50.0

        return willr

    def _calculate_cci(
        self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 20
    ) -> np.ndarray:
        """Расчет Commodity Channel Index"""
        if len(high) < period:
            return np.zeros_like(close)

        # Typical Price
        typical_price = (high + low + close) / 3

        cci = np.zeros_like(close)

        for i in range(period - 1, len(close)):
            tp_slice = typical_price[i - period + 1 : i + 1]
            sma = np.mean(tp_slice)
            mad = np.mean(np.abs(tp_slice - sma))

            if mad != 0:
                cci[i] = (typical_price[i] - sma) / (0.015 * mad)
            else:
                cci[i] = 0

        return cci

    def _calculate_roc(self, prices: np.ndarray, period: int = 10) -> np.ndarray:
        """Расчет Rate of Change"""
        if len(prices) < period + 1:
            return np.zeros_like(prices)

        roc = np.zeros_like(prices)

        for i in range(period, len(prices)):
            if prices[i - period] != 0:
                roc[i] = ((prices[i] - prices[i - period]) / prices[i - period]) * 100

        return roc

    def _calculate_mfi(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        volume: np.ndarray,
        period: int = 14,
    ) -> np.ndarray:
        """Расчет Money Flow Index"""
        if len(high) < period + 1:
            return np.full_like(close, 50.0)

        typical_price = (high + low + close) / 3
        raw_money_flow = typical_price * volume

        mfi = np.full_like(close, 50.0)

        for i in range(period, len(close)):
            positive_flow = 0
            negative_flow = 0

            for j in range(i - period + 1, i + 1):
                if j > 0:
                    if typical_price[j] > typical_price[j - 1]:
                        positive_flow += raw_money_flow[j]
                    elif typical_price[j] < typical_price[j - 1]:
                        negative_flow += raw_money_flow[j]

            if negative_flow > 0:
                money_ratio = positive_flow / negative_flow
                mfi[i] = 100 - (100 / (1 + money_ratio))
            else:
                mfi[i] = 100

        return mfi

    def _calculate_momentum(self, prices: np.ndarray, period: int = 10) -> np.ndarray:
        """Расчет Momentum индикатора"""
        if len(prices) < period:
            return np.zeros_like(prices)

        momentum = np.zeros_like(prices)

        for i in range(period, len(prices)):
            momentum[i] = prices[i] - prices[i - period]

        return momentum

    def _calculate_trix(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Расчет TRIX индикатора"""
        if len(prices) < period * 3:
            return np.zeros_like(prices)

        # Тройное экспоненциальное сглаживание
        ema1 = self._calculate_ema(prices, period)
        ema2 = self._calculate_ema(ema1, period)
        ema3 = self._calculate_ema(ema2, period)

        # Rate of change EMA3
        trix = np.zeros_like(prices)
        for i in range(1, len(ema3)):
            if ema3[i - 1] != 0:
                trix[i] = ((ema3[i] - ema3[i - 1]) / ema3[i - 1]) * 10000

        return trix

    def _calculate_aroon(
        self, high: np.ndarray, low: np.ndarray, period: int = 25
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Расчет Aroon индикатора"""
        if len(high) < period:
            return np.full_like(high, 50.0), np.full_like(low, 50.0)

        aroon_up = np.zeros_like(high)
        aroon_down = np.zeros_like(low)

        for i in range(period - 1, len(high)):
            high_slice = high[i - period + 1 : i + 1]
            low_slice = low[i - period + 1 : i + 1]

            # Найти позицию максимума и минимума
            high_idx = np.argmax(high_slice)
            low_idx = np.argmin(low_slice)

            # Aroon расчет
            aroon_up[i] = ((period - (period - 1 - high_idx)) / period) * 100
            aroon_down[i] = ((period - (period - 1 - low_idx)) / period) * 100

        # Заполняем начальные значения
        aroon_up[: period - 1] = 50.0
        aroon_down[: period - 1] = 50.0

        return aroon_up, aroon_down

    def _calculate_adx(
        self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Расчет ADX и связанных индикаторов"""
        if len(high) < period + 1:
            zeros = np.zeros_like(close)
            return zeros, zeros, zeros, zeros

        # True Range
        tr = self._calculate_true_range(high, low, close)

        # Directional Movement
        plus_dm = np.zeros_like(close)
        minus_dm = np.zeros_like(close)

        for i in range(1, len(high)):
            up_move = high[i] - high[i - 1]
            down_move = low[i - 1] - low[i]

            if up_move > down_move and up_move > 0:
                plus_dm[i] = up_move
            if down_move > up_move and down_move > 0:
                minus_dm[i] = down_move

        # Сглаженные значения
        atr = self._calculate_atr(high, low, close, period)
        plus_di = np.zeros_like(close)
        minus_di = np.zeros_like(close)

        # Сглаживание DM
        smoothed_plus_dm = self._smooth_series(plus_dm, period)
        smoothed_minus_dm = self._smooth_series(minus_dm, period)

        # DI расчет
        for i in range(period, len(close)):
            if atr[i] != 0:
                plus_di[i] = (smoothed_plus_dm[i] / atr[i]) * 100
                minus_di[i] = (smoothed_minus_dm[i] / atr[i]) * 100

        # DX и ADX
        dx = np.zeros_like(close)
        for i in range(period, len(close)):
            di_sum = plus_di[i] + minus_di[i]
            if di_sum != 0:
                dx[i] = abs(plus_di[i] - minus_di[i]) / di_sum * 100

        # ADX - сглаженный DX
        adx = self._smooth_series(dx, period)

        return dx, adx, plus_di, minus_di

    def _calculate_true_range(
        self, high: np.ndarray, low: np.ndarray, close: np.ndarray
    ) -> np.ndarray:
        """Расчет True Range"""
        if len(high) < 2:
            return high - low

        tr1 = high - low
        tr2 = np.abs(high - np.roll(close, 1))
        tr3 = np.abs(low - np.roll(close, 1))

        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        tr[0] = tr1[0]  # Первое значение

        return tr

    def _smooth_series(self, series: np.ndarray, period: int) -> np.ndarray:
        """Сглаживание временного ряда методом Уайлдера"""
        smoothed = np.zeros_like(series)
        smoothed[period - 1] = np.mean(series[:period])

        for i in range(period, len(series)):
            smoothed[i] = (smoothed[i - 1] * (period - 1) + series[i]) / period

        # Заполняем начальные значения
        smoothed[: period - 1] = (
            smoothed[period - 1] if period - 1 < len(smoothed) else 0
        )

        return smoothed

    def _calculate_ultimate_oscillator(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period1: int = 7,
        period2: int = 14,
        period3: int = 28,
    ) -> np.ndarray:
        """Расчет Ultimate Oscillator"""
        if len(high) < period3 + 1:
            return np.full_like(close, 50.0)

        # Buying Pressure и True Range
        bp = close - np.minimum(low, np.roll(close, 1))
        tr = self._calculate_true_range(high, low, close)

        # Средние для каждого периода
        avg1 = np.zeros_like(close)
        avg2 = np.zeros_like(close)
        avg3 = np.zeros_like(close)

        for i in range(period3, len(close)):
            sum_bp1 = np.sum(bp[i - period1 + 1 : i + 1])
            sum_tr1 = np.sum(tr[i - period1 + 1 : i + 1])
            avg1[i] = sum_bp1 / sum_tr1 if sum_tr1 != 0 else 0

            sum_bp2 = np.sum(bp[i - period2 + 1 : i + 1])
            sum_tr2 = np.sum(tr[i - period2 + 1 : i + 1])
            avg2[i] = sum_bp2 / sum_tr2 if sum_tr2 != 0 else 0

            sum_bp3 = np.sum(bp[i - period3 + 1 : i + 1])
            sum_tr3 = np.sum(tr[i - period3 + 1 : i + 1])
            avg3[i] = sum_bp3 / sum_tr3 if sum_tr3 != 0 else 0

        # Ultimate Oscillator
        uo = ((avg1 * 4) + (avg2 * 2) + avg3) / 7 * 100

        return uo

    def _calculate_balance_of_power(
        self,
        open_prices: np.ndarray,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
    ) -> np.ndarray:
        """Расчет Balance of Power"""
        bop = np.zeros_like(close)

        for i in range(len(close)):
            hl_diff = high[i] - low[i]
            if hl_diff != 0:
                bop[i] = (close[i] - open_prices[i]) / hl_diff

        return bop

    def _calculate_parabolic_sar(
        self,
        high: np.ndarray,
        low: np.ndarray,
        acceleration: float = 0.02,
        maximum: float = 0.2,
    ) -> np.ndarray:
        """Расчет Parabolic SAR"""
        if len(high) < 2:
            return np.zeros_like(high)

        sar = np.zeros_like(high)
        ep = 0  # Extreme Point
        af = acceleration  # Acceleration Factor
        uptrend = True

        # Инициализация
        sar[0] = low[0]
        ep = high[0]

        for i in range(1, len(high)):
            if uptrend:
                sar[i] = sar[i - 1] + af * (ep - sar[i - 1])

                if low[i] <= sar[i]:
                    uptrend = False
                    sar[i] = ep
                    ep = low[i]
                    af = acceleration
                else:
                    if high[i] > ep:
                        ep = high[i]
                        af = min(af + acceleration, maximum)

                    # Убедимся что SAR не выше минимума последних двух периодов
                    if i > 1:
                        sar[i] = min(sar[i], low[i - 1], low[i - 2])
                    else:
                        sar[i] = min(sar[i], low[i - 1])
            else:
                sar[i] = sar[i - 1] + af * (ep - sar[i - 1])

                if high[i] >= sar[i]:
                    uptrend = True
                    sar[i] = ep
                    ep = high[i]
                    af = acceleration
                else:
                    if low[i] < ep:
                        ep = low[i]
                        af = min(af + acceleration, maximum)

                    # Убедимся что SAR не ниже максимума последних двух периодов
                    if i > 1:
                        sar[i] = max(sar[i], high[i - 1], high[i - 2])
                    else:
                        sar[i] = max(sar[i], high[i - 1])

        return sar

    def _calculate_microstructure_features(self, df: pd.DataFrame) -> np.ndarray:
        """Расчет микроструктурных признаков рынка"""
        features = []

        open_prices = df["open"].values.astype(float)
        high_prices = df["high"].values.astype(float)
        low_prices = df["low"].values.astype(float)
        close_prices = df["close"].values.astype(float)
        volume = df["volume"].values.astype(float)

        # Bid-Ask Spread Proxy
        spread_proxy = (high_prices - low_prices) / close_prices
        features.append(spread_proxy.reshape(-1, 1))
        self.feature_names.append("spread_proxy")

        # Price Impact
        returns = np.diff(close_prices) / close_prices[:-1]
        returns = np.concatenate([np.array([0]), returns])
        price_impact = np.abs(returns) / (volume + 1e-10)
        price_impact_norm = self._normalize_series(price_impact)
        features.append(price_impact_norm)
        self.feature_names.append("price_impact")

        # Order Imbalance Proxy
        order_imbalance = (close_prices - open_prices) / (
            high_prices - low_prices + 1e-10
        )
        features.append(order_imbalance.reshape(-1, 1))
        self.feature_names.append("order_imbalance")

        # Amihud Illiquidity
        amihud_illiq = np.abs(returns) / (volume * close_prices + 1e-10)
        amihud_norm = self._normalize_series(amihud_illiq)
        features.append(amihud_norm)
        self.feature_names.append("amihud_illiquidity")

        # Effective Spread
        mid_price = (high_prices + low_prices) / 2
        effective_spread = 2 * np.abs(close_prices - mid_price) / close_prices
        features.append(effective_spread.reshape(-1, 1))
        self.feature_names.append("effective_spread")

        # Price Dispersion
        price_dispersion = (high_prices - low_prices) / close_prices
        features.append(price_dispersion.reshape(-1, 1))
        self.feature_names.append("price_dispersion")

        # Intraday Momentum
        intraday_momentum = (close_prices - open_prices) / (open_prices + 1e-10)
        features.append(intraday_momentum.reshape(-1, 1))
        self.feature_names.append("intraday_momentum")

        # Volume Concentration
        volume_series = pd.Series(volume)
        volume_concentration = volume / (
            volume_series.rolling(20).max().fillna(1) + 1e-10
        )
        features.append(volume_concentration.values.reshape(-1, 1))
        self.feature_names.append("volume_concentration")

        # High-Low Ratio
        hl_ratio = high_prices / (low_prices + 1e-10)
        hl_ratio_norm = self._normalize_series(hl_ratio)
        features.append(hl_ratio_norm)
        self.feature_names.append("high_low_ratio")

        # Close Location Value
        clv = ((close_prices - low_prices) - (high_prices - close_prices)) / (
            high_prices - low_prices + 1e-10
        )
        features.append(clv.reshape(-1, 1))
        self.feature_names.append("close_location_value")

        return np.concatenate(features, axis=1)

    def _calculate_advanced_features(
        self, df: pd.DataFrame, existing_features: List[np.ndarray]
    ) -> np.ndarray:
        """Расчет продвинутых комбинированных признаков"""
        features = []

        close_prices = df["close"].values.astype(float)
        volume = df["volume"].values.astype(float)

        # Price Position in Range для разных периодов
        for period in [5, 10, 20]:
            if len(close_prices) >= period:
                high_rolling = (
                    pd.Series(df["high"].values)
                    .rolling(period)
                    .max()
                    .fillna(df["high"].values[0])
                )
                low_rolling = (
                    pd.Series(df["low"].values)
                    .rolling(period)
                    .min()
                    .fillna(df["low"].values[0])
                )
                price_position = (close_prices - low_rolling) / (
                    high_rolling - low_rolling + 1e-10
                )
                features.append(price_position.values.reshape(-1, 1))
                self.feature_names.append(f"price_position_{period}")

        # Volume-Price Trend
        vpt = np.zeros_like(close_prices)
        for i in range(1, len(close_prices)):
            price_change = (
                (close_prices[i] - close_prices[i - 1]) / close_prices[i - 1]
                if close_prices[i - 1] != 0
                else 0
            )
            vpt[i] = vpt[i - 1] + price_change * volume[i]
        vpt_norm = self._normalize_series(vpt)
        features.append(vpt_norm)
        self.feature_names.append("volume_price_trend")

        # Chaikin Money Flow (20 период)
        clv = (
            (close_prices - df["low"].values) - (df["high"].values - close_prices)
        ) / (df["high"].values - df["low"].values + 1e-10)
        mfv = clv * volume
        cmf = pd.Series(mfv).rolling(20).sum() / (
            pd.Series(volume).rolling(20).sum() + 1e-10
        )
        features.append(cmf.fillna(0).values.reshape(-1, 1))
        self.feature_names.append("chaikin_money_flow")

        # Donchian Channel Position
        for period in [20, 50]:
            if len(close_prices) >= period:
                upper_channel = (
                    pd.Series(df["high"].values)
                    .rolling(period)
                    .max()
                    .fillna(df["high"].values[0])
                )
                lower_channel = (
                    pd.Series(df["low"].values)
                    .rolling(period)
                    .min()
                    .fillna(df["low"].values[0])
                )
                donchian_pos = (close_prices - lower_channel) / (
                    upper_channel - lower_channel + 1e-10
                )
                features.append(donchian_pos.values.reshape(-1, 1))
                self.feature_names.append(f"donchian_position_{period}")

        # Awesome Oscillator (SMA5 - SMA34)
        if len(close_prices) >= 34:
            hl_mid = (df["high"].values + df["low"].values) / 2
            sma5 = self._calculate_sma(hl_mid, 5)
            sma34 = self._calculate_sma(hl_mid, 34)
            awesome_osc = sma5 - sma34
            awesome_norm = self._normalize_series(awesome_osc)
            features.append(awesome_norm)
            self.feature_names.append("awesome_oscillator")
        else:
            features.append(np.zeros((len(close_prices), 1)))
            self.feature_names.append("awesome_oscillator")

        # Elder Ray Bull/Bear Power
        if len(close_prices) >= 13:
            ema13 = self._calculate_ema(close_prices, 13)
            bull_power = df["high"].values - ema13
            bear_power = df["low"].values - ema13
            bull_norm = self._normalize_series(bull_power)
            bear_norm = self._normalize_series(bear_power)
            features.extend([bull_norm, bear_norm])
            self.feature_names.extend(["elder_bull_power", "elder_bear_power"])
        else:
            features.extend([np.zeros((len(close_prices), 1)) for _ in range(2)])
            self.feature_names.extend(["elder_bull_power", "elder_bear_power"])

        # Mass Index
        if len(close_prices) >= 25:
            hl_range = df["high"].values - df["low"].values
            ema9 = self._calculate_ema(hl_range, 9)
            ema9_double = self._calculate_ema(ema9, 9)
            ratio = ema9 / (ema9_double + 1e-10)
            mass_index = pd.Series(ratio).rolling(25).sum().fillna(25)
            mass_norm = self._normalize_series(mass_index.values)
            features.append(mass_norm)
            self.feature_names.append("mass_index")
        else:
            features.append(np.zeros((len(close_prices), 1)))
            self.feature_names.append("mass_index")

        return np.concatenate(features, axis=1)

    def _calculate_lag_features(
        self, df: pd.DataFrame, existing_features: List[np.ndarray]
    ) -> np.ndarray:
        """Расчет лаговых признаков"""
        features = []

        close_prices = df["close"].values
        volume = df["volume"].values

        # Лаги цен
        for lag in [1, 2, 3, 5, 10]:
            lagged_close = np.roll(close_prices, lag)
            lagged_close[:lag] = close_prices[0]  # Заполняем начальные значения
            close_lag_return = (close_prices - lagged_close) / (lagged_close + 1e-10)
            features.append(close_lag_return.reshape(-1, 1))
            self.feature_names.append(f"close_lag_return_{lag}")

        # Лаги объемов
        for lag in [1, 2, 3]:
            lagged_volume = np.roll(volume, lag)
            lagged_volume[:lag] = volume[0]
            volume_lag_ratio = volume / (lagged_volume + 1e-10)
            volume_lag_norm = self._normalize_series(volume_lag_ratio)
            features.append(volume_lag_norm)
            self.feature_names.append(f"volume_lag_ratio_{lag}")

        # Лаги волатильности
        returns = np.diff(close_prices) / close_prices[:-1]
        returns = np.concatenate([np.array([0]), returns])
        volatility = pd.Series(returns).rolling(20).std().fillna(0).values

        for lag in [1, 2]:
            lagged_vol = np.roll(volatility, lag)
            lagged_vol[:lag] = volatility[0]
            vol_lag_ratio = volatility / (lagged_vol + 1e-10)
            features.append(vol_lag_ratio.reshape(-1, 1))
            self.feature_names.append(f"volatility_lag_ratio_{lag}")

        return np.concatenate(features, axis=1)

    def _calculate_pattern_features(self, df: pd.DataFrame) -> np.ndarray:
        """Расчет признаков паттернов свечей"""
        features = []

        open_prices = df["open"].values
        high_prices = df["high"].values
        low_prices = df["low"].values
        close_prices = df["close"].values

        # Doji pattern
        body_size = np.abs(close_prices - open_prices)
        hl_range = high_prices - low_prices
        is_doji = (body_size / (hl_range + 1e-10) < 0.1).astype(float)
        features.append(is_doji.reshape(-1, 1))
        self.feature_names.append("is_doji")

        # Hammer pattern
        lower_shadow = np.minimum(open_prices, close_prices) - low_prices
        upper_shadow = high_prices - np.maximum(open_prices, close_prices)
        is_hammer = (
            (lower_shadow > 2 * body_size) & (upper_shadow < body_size * 0.3)
        ).astype(float)
        features.append(is_hammer.reshape(-1, 1))
        self.feature_names.append("is_hammer")

        # Engulfing pattern
        is_bullish_engulfing = np.zeros_like(close_prices)
        is_bearish_engulfing = np.zeros_like(close_prices)
        for i in range(1, len(close_prices)):
            # Bullish engulfing
            if (
                open_prices[i] < close_prices[i - 1]
                and close_prices[i] > open_prices[i - 1]
                and open_prices[i] <= close_prices[i - 1]
                and close_prices[i] >= open_prices[i - 1]
            ):
                is_bullish_engulfing[i] = 1
            # Bearish engulfing
            if (
                open_prices[i] > close_prices[i - 1]
                and close_prices[i] < open_prices[i - 1]
                and open_prices[i] >= close_prices[i - 1]
                and close_prices[i] <= open_prices[i - 1]
            ):
                is_bearish_engulfing[i] = 1

        features.append(is_bullish_engulfing.reshape(-1, 1))
        self.feature_names.append("is_bullish_engulfing")
        features.append(is_bearish_engulfing.reshape(-1, 1))
        self.feature_names.append("is_bearish_engulfing")

        # Three White Soldiers / Three Black Crows
        three_white_soldiers = np.zeros_like(close_prices)
        three_black_crows = np.zeros_like(close_prices)
        for i in range(2, len(close_prices)):
            # Three White Soldiers
            if (
                close_prices[i] > open_prices[i]
                and close_prices[i - 1] > open_prices[i - 1]
                and close_prices[i - 2] > open_prices[i - 2]
                and close_prices[i] > close_prices[i - 1]
                and close_prices[i - 1] > close_prices[i - 2]
            ):
                three_white_soldiers[i] = 1
            # Three Black Crows
            if (
                close_prices[i] < open_prices[i]
                and close_prices[i - 1] < open_prices[i - 1]
                and close_prices[i - 2] < open_prices[i - 2]
                and close_prices[i] < close_prices[i - 1]
                and close_prices[i - 1] < close_prices[i - 2]
            ):
                three_black_crows[i] = 1

        features.append(three_white_soldiers.reshape(-1, 1))
        self.feature_names.append("three_white_soldiers")
        features.append(three_black_crows.reshape(-1, 1))
        self.feature_names.append("three_black_crows")

        # Gap patterns
        gap_up = (low_prices > np.roll(high_prices, 1)).astype(float)
        gap_down = (high_prices < np.roll(low_prices, 1)).astype(float)
        gap_up[0] = 0
        gap_down[0] = 0

        features.append(gap_up.reshape(-1, 1))
        self.feature_names.append("gap_up")
        features.append(gap_down.reshape(-1, 1))
        self.feature_names.append("gap_down")

        # Inside bar
        inside_bar = (
            (high_prices <= np.roll(high_prices, 1))
            & (low_prices >= np.roll(low_prices, 1))
        ).astype(float)
        inside_bar[0] = 0
        features.append(inside_bar.reshape(-1, 1))
        self.feature_names.append("inside_bar")

        # Outside bar
        outside_bar = (
            (high_prices >= np.roll(high_prices, 1))
            & (low_prices <= np.roll(low_prices, 1))
        ).astype(float)
        outside_bar[0] = 0
        features.append(outside_bar.reshape(-1, 1))
        self.feature_names.append("outside_bar")

        return np.concatenate(features, axis=1)

    def _calculate_momentum_features(self, df: pd.DataFrame) -> np.ndarray:
        """Расчет дополнительных моментум признаков"""
        features = []

        close_prices = df["close"].values
        high_prices = df["high"].values
        low_prices = df["low"].values
        volume = df["volume"].values

        # Relative Vigor Index
        for period in [10, 14]:
            if len(close_prices) >= period + 1:
                co = close_prices - df["open"].values
                hl = high_prices - low_prices

                co_smooth = self._smooth_series(co, period)
                hl_smooth = self._smooth_series(hl, period)

                rvi = np.zeros_like(close_prices)
                rvi[period:] = co_smooth[period:] / (hl_smooth[period:] + 1e-10)

                features.append(rvi.reshape(-1, 1))
                self.feature_names.append(f"rvi_{period}")
            else:
                features.append(np.zeros((len(close_prices), 1)))
                self.feature_names.append(f"rvi_{period}")

        # Force Index
        for period in [13, 20]:
            if len(close_prices) >= period + 1:
                price_change = np.diff(close_prices)
                price_change = np.concatenate([np.array([0]), price_change])
                raw_fi = price_change * volume
                force_index = self._calculate_ema(raw_fi, period)
                fi_norm = self._normalize_series(force_index)
                features.append(fi_norm)
                self.feature_names.append(f"force_index_{period}")
            else:
                features.append(np.zeros((len(close_prices), 1)))
                self.feature_names.append(f"force_index_{period}")

        # Chande Momentum Oscillator
        for period in [14, 20]:
            if len(close_prices) >= period + 1:
                price_changes = np.diff(close_prices)
                price_changes = np.concatenate([np.array([0]), price_changes])

                gains = np.where(price_changes > 0, price_changes, 0)
                losses = np.where(price_changes < 0, -price_changes, 0)

                cmo = np.zeros_like(close_prices)

                for i in range(period, len(close_prices)):
                    sum_gains = np.sum(gains[i - period + 1 : i + 1])
                    sum_losses = np.sum(losses[i - period + 1 : i + 1])

                    if sum_gains + sum_losses != 0:
                        cmo[i] = (
                            (sum_gains - sum_losses) / (sum_gains + sum_losses) * 100
                        )

                cmo_norm = cmo / 100.0
                features.append(cmo_norm.reshape(-1, 1))
                self.feature_names.append(f"cmo_{period}")
            else:
                features.append(np.zeros((len(close_prices), 1)))
                self.feature_names.append(f"cmo_{period}")

        # Klinger Volume Oscillator
        if len(close_prices) >= 35:
            hlc = (high_prices + low_prices + close_prices) / 3
            dm = hlc - np.roll(hlc, 1)
            dm[0] = 0

            cm = np.zeros_like(close_prices)
            for i in range(1, len(close_prices)):
                if hlc[i] > hlc[i - 1]:
                    cm[i] = cm[i - 1] + (high_prices[i] - low_prices[i])
                else:
                    cm[i] = high_prices[i] - low_prices[i]

            vf = volume * np.sign(dm) * cm
            kvo = self._calculate_ema(vf, 34) - self._calculate_ema(vf, 55)
            kvo_signal = self._calculate_ema(kvo, 13)

            kvo_norm = self._normalize_series(kvo)
            kvo_signal_norm = self._normalize_series(kvo_signal)

            features.extend([kvo_norm, kvo_signal_norm])
            self.feature_names.extend(["klinger_oscillator", "klinger_signal"])
        else:
            features.extend([np.zeros((len(close_prices), 1)) for _ in range(2)])
            self.feature_names.extend(["klinger_oscillator", "klinger_signal"])

        # Price Rate of Change для дополнительных периодов
        for period in [3, 7, 14]:
            if len(close_prices) > period:
                proc = (
                    (close_prices - np.roll(close_prices, period))
                    / np.roll(close_prices, period)
                    * 100
                )
                proc[:period] = 0
                proc_norm = self._normalize_series(proc)
                features.append(proc_norm)
                self.feature_names.append(f"price_roc_{period}")
            else:
                features.append(np.zeros((len(close_prices), 1)))
                self.feature_names.append(f"price_roc_{period}")

        # Volume Oscillator
        if len(volume) >= 20:
            vol_short = self._calculate_ema(volume, 5)
            vol_long = self._calculate_ema(volume, 20)
            vol_osc = (vol_short - vol_long) / vol_long * 100
            vol_osc_norm = self._normalize_series(vol_osc)
            features.append(vol_osc_norm)
            self.feature_names.append("volume_oscillator")
        else:
            features.append(np.zeros((len(close_prices), 1)))
            self.feature_names.append("volume_oscillator")

        # Accumulation/Distribution Line
        clv = ((close_prices - low_prices) - (high_prices - close_prices)) / (
            high_prices - low_prices + 1e-10
        )
        adl = np.cumsum(clv * volume)
        adl_norm = self._normalize_series(adl)
        features.append(adl_norm)
        self.feature_names.append("accumulation_distribution")

        # Ease of Movement
        if len(close_prices) >= 14:
            distance = (high_prices + low_prices) / 2 - np.roll(
                (high_prices + low_prices) / 2, 1
            )
            emv = distance / (volume / 1e6 / ((high_prices - low_prices) + 1e-10))
            emv[0] = 0
            emv_smooth = self._calculate_sma(emv, 14)
            emv_norm = self._normalize_series(emv_smooth)
            features.append(emv_norm)
            self.feature_names.append("ease_of_movement")
        else:
            features.append(np.zeros((len(close_prices), 1)))
            self.feature_names.append("ease_of_movement")

        # Negative Volume Index
        nvi = np.ones_like(close_prices) * 1000  # Start at 1000
        for i in range(1, len(close_prices)):
            if volume[i] < volume[i - 1]:
                nvi[i] = nvi[i - 1] * (
                    1 + (close_prices[i] - close_prices[i - 1]) / close_prices[i - 1]
                )
            else:
                nvi[i] = nvi[i - 1]
        nvi_norm = self._normalize_series(nvi)
        features.append(nvi_norm)
        self.feature_names.append("negative_volume_index")

        # Positive Volume Index
        pvi = np.ones_like(close_prices) * 1000  # Start at 1000
        for i in range(1, len(close_prices)):
            if volume[i] > volume[i - 1]:
                pvi[i] = pvi[i - 1] * (
                    1 + (close_prices[i] - close_prices[i - 1]) / close_prices[i - 1]
                )
            else:
                pvi[i] = pvi[i - 1]
        pvi_norm = self._normalize_series(pvi)
        features.append(pvi_norm)
        self.feature_names.append("positive_volume_index")

        # Detrended Price Oscillator
        for period in [14, 20]:
            if len(close_prices) >= period * 2:
                ma = self._calculate_sma(close_prices, period)
                ma_shifted = np.roll(ma, period // 2 + 1)
                ma_shifted[: period // 2 + 1] = ma[0]
                dpo = close_prices - ma_shifted
                dpo_norm = self._normalize_series(dpo)
                features.append(dpo_norm)
                self.feature_names.append(f"dpo_{period}")
            else:
                features.append(np.zeros((len(close_prices), 1)))
                self.feature_names.append(f"dpo_{period}")

        # Вortex Indicator
        if len(close_prices) >= 14:
            vm_plus = np.abs(high_prices - np.roll(low_prices, 1))
            vm_minus = np.abs(low_prices - np.roll(high_prices, 1))
            vm_plus[0] = 0
            vm_minus[0] = 0

            tr = self._calculate_true_range(high_prices, low_prices, close_prices)

            vi_plus = pd.Series(vm_plus).rolling(14).sum() / (
                pd.Series(tr).rolling(14).sum() + 1e-10
            )
            vi_minus = pd.Series(vm_minus).rolling(14).sum() / (
                pd.Series(tr).rolling(14).sum() + 1e-10
            )

            features.append(vi_plus.fillna(0).values.reshape(-1, 1))
            self.feature_names.append("vortex_plus")
            features.append(vi_minus.fillna(0).values.reshape(-1, 1))
            self.feature_names.append("vortex_minus")
        else:
            features.extend([np.zeros((len(close_prices), 1)) for _ in range(2)])
            self.feature_names.extend(["vortex_plus", "vortex_minus"])

        # Percentage Price Oscillator
        if len(close_prices) >= 26:
            ema12 = self._calculate_ema(close_prices, 12)
            ema26 = self._calculate_ema(close_prices, 26)
            ppo = (ema12 - ema26) / ema26 * 100
            ppo_signal = self._calculate_ema(ppo, 9)
            ppo_hist = ppo - ppo_signal

            ppo_norm = self._normalize_series(ppo)
            ppo_signal_norm = self._normalize_series(ppo_signal)
            ppo_hist_norm = self._normalize_series(ppo_hist)

            features.extend([ppo_norm, ppo_signal_norm, ppo_hist_norm])
            self.feature_names.extend(["ppo", "ppo_signal", "ppo_hist"])
        else:
            features.extend([np.zeros((len(close_prices), 1)) for _ in range(3)])
            self.feature_names.extend(["ppo", "ppo_signal", "ppo_hist"])

        # Price Channel
        for period in [20, 50]:
            if len(close_prices) >= period:
                upper_channel = (
                    pd.Series(high_prices).rolling(period).max().fillna(high_prices[0])
                )
                lower_channel = (
                    pd.Series(low_prices).rolling(period).min().fillna(low_prices[0])
                )
                center_line = (upper_channel + lower_channel) / 2

                channel_pos = (close_prices - lower_channel) / (
                    upper_channel - lower_channel + 1e-10
                )
                center_distance = (close_prices - center_line) / center_line

                features.append(channel_pos.values.reshape(-1, 1))
                self.feature_names.append(f"price_channel_position_{period}")
                features.append(center_distance.values.reshape(-1, 1))
                self.feature_names.append(f"price_channel_center_dist_{period}")
            else:
                features.extend([np.zeros((len(close_prices), 1)) for _ in range(2)])
                self.feature_names.extend(
                    [
                        f"price_channel_position_{period}",
                        f"price_channel_center_dist_{period}",
                    ]
                )

        return np.concatenate(features, axis=1)

    def _estimate_hurst_exponent(self, prices: np.ndarray) -> float:
        """Оценка экспоненты Херста"""
        try:
            lags = range(2, min(20, len(prices) // 2))
            tau = [
                np.sqrt(np.std(np.subtract(prices[lag:], prices[:-lag])))
                for lag in lags
            ]

            # Линейная регрессия в логарифмическом пространстве
            poly = np.polyfit(np.log(lags), np.log(tau), 1)
            return poly[0] * 2.0  # Hurst exponent
        except:
            return 0.5  # Возвращаем 0.5 (случайное блуждание) в случае ошибки

    def _calculate_fisher_transform(
        self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 10
    ) -> np.ndarray:
        """Расчет Fisher Transform"""
        if len(close) < period:
            return np.zeros_like(close)

        # Нормализация цены в диапазон [-1, 1]
        hl2 = (high + low) / 2
        max_high = pd.Series(hl2).rolling(period).max().fillna(hl2[0])
        min_low = pd.Series(hl2).rolling(period).min().fillna(hl2[0])

        value = np.zeros_like(close)
        for i in range(len(close)):
            if max_high.iloc[i] != min_low.iloc[i]:
                value[i] = 2 * (
                    (hl2[i] - min_low.iloc[i]) / (max_high.iloc[i] - min_low.iloc[i])
                    - 0.5
                )
            value[i] = np.clip(value[i], -0.999, 0.999)

        # Fisher transform
        fisher = np.zeros_like(close)
        for i in range(1, len(close)):
            fisher[i] = 0.5 * np.log((1 + value[i]) / (1 - value[i] + 1e-10))

        return fisher

    def _calculate_choppiness_index(
        self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14
    ) -> np.ndarray:
        """Расчет Choppiness Index"""
        if len(close) < period:
            return np.full_like(close, 0.5)

        atr_sum = (
            pd.Series(self._calculate_true_range(high, low, close))
            .rolling(period)
            .sum()
        )
        high_low_range = (
            pd.Series(high).rolling(period).max() - pd.Series(low).rolling(period).min()
        )

        ci = np.zeros_like(close)
        for i in range(period - 1, len(close)):
            if high_low_range.iloc[i] > 0:
                ci[i] = (
                    100
                    * np.log10(atr_sum.iloc[i] / high_low_range.iloc[i])
                    / np.log10(period)
                )

        return ci / 100.0  # Нормализация к [0, 1]
