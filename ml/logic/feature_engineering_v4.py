"""
Feature Engineering v4.0 - точная копия из проекта обучения
Генерирует ровно 240 признаков как при обучении модели
"""

import warnings
from typing import Dict, Union

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from core.logger import setup_logger


class FeatureEngineer:
    """Создание признаков для модели прогнозирования - версия из обучения"""

    def __init__(self, config: Dict):
        self.config = config
        self.logger = setup_logger("FeatureEngineer")
        self.feature_list = []  # Список всех признаков в правильном порядке

    @staticmethod
    def safe_divide(
        numerator: pd.Series,
        denominator: pd.Series,
        fill_value=0.0,
        max_value=1000.0,
        min_denominator=1e-8,
    ) -> pd.Series:
        """Безопасное деление с обработкой малых значений"""
        safe_denominator = denominator.copy()
        mask_small = safe_denominator.abs() < min_denominator
        safe_denominator[mask_small] = min_denominator

        result = numerator / safe_denominator
        result = result.clip(lower=-max_value, upper=max_value)
        result = result.replace([np.inf, -np.inf], [fill_value, fill_value])
        result = result.fillna(fill_value)

        return result

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
        # Если это уже numpy array - возвращаем как есть (уже обработанные признаки)
        if isinstance(df, np.ndarray):
            self.logger.debug(f"Получен numpy array shape: {df.shape}")
            return df

        # Валидация DataFrame
        required_cols = ["open", "high", "low", "close", "volume"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Отсутствуют обязательные колонки: {missing_cols}")

        # Копируем данные
        data = df.copy()

        # Сортируем по времени если есть timestamp
        if "timestamp" in data.columns:
            data = data.sort_values("timestamp")
        elif "datetime" in data.columns:
            data = data.sort_values("datetime")

        # Сбрасываем индекс
        data = data.reset_index(drop=True)

        # Список для хранения всех признаков
        features = pd.DataFrame(index=data.index)

        # 1. БАЗОВЫЕ ПРИЗНАКИ (5)
        features["open"] = data["open"]
        features["high"] = data["high"]
        features["low"] = data["low"]
        features["close"] = data["close"]
        features["volume"] = data["volume"]

        # 2. RETURNS (10)
        for period in [1, 2, 3, 5, 10]:
            features[f"returns_{period}"] = data["close"].pct_change(period)

        for period in [1, 2, 3, 5, 10]:
            features[f"log_returns_{period}"] = np.log(
                data["close"] / data["close"].shift(period)
            )

        # 3. VOLATILITY (10)
        for period in [5, 10, 20]:
            features[f"volatility_{period}"] = (
                features["returns_1"].rolling(period).std()
            )

        # ATR
        high_low = data["high"] - data["low"]
        high_close = np.abs(data["high"] - data["close"].shift())
        low_close = np.abs(data["low"] - data["close"].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        features["true_range"] = true_range

        for period in [7, 14, 20]:
            features[f"atr_{period}"] = true_range.rolling(period).mean()

        # Bollinger Bands width
        for period in [10, 20, 30]:
            sma = data["close"].rolling(period).mean()
            std = data["close"].rolling(period).std()
            features[f"bb_width_{period}"] = (std * 2) / sma

        # 4. MOVING AVERAGES (20)
        for period in [5, 10, 20, 30, 50]:
            features[f"sma_{period}"] = data["close"].rolling(period).mean()

        for period in [5, 10, 20, 30, 50]:
            features[f"ema_{period}"] = (
                data["close"].ewm(span=period, adjust=False).mean()
            )

        # Price to MA ratios (10)
        for period in [5, 10, 20, 30, 50]:
            features[f"close_to_sma_{period}"] = self.safe_divide(
                data["close"], features[f"sma_{period}"]
            )

        for period in [5, 10, 20, 30, 50]:
            features[f"close_to_ema_{period}"] = self.safe_divide(
                data["close"], features[f"ema_{period}"]
            )

        # 5. TECHNICAL INDICATORS (30)

        # RSI
        for period in [7, 14, 21, 30]:
            delta = data["close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
            rs = self.safe_divide(gain, loss)
            features[f"rsi_{period}"] = 100 - (100 / (1 + rs))

        # MACD
        ema12 = data["close"].ewm(span=12, adjust=False).mean()
        ema26 = data["close"].ewm(span=26, adjust=False).mean()
        features["macd"] = ema12 - ema26
        features["macd_signal"] = features["macd"].ewm(span=9, adjust=False).mean()
        features["macd_diff"] = features["macd"] - features["macd_signal"]

        # Stochastic
        for period in [14, 21]:
            low_min = data["low"].rolling(period).min()
            high_max = data["high"].rolling(period).max()
            features[f"stoch_k_{period}"] = 100 * self.safe_divide(
                data["close"] - low_min, high_max - low_min
            )
            features[f"stoch_d_{period}"] = (
                features[f"stoch_k_{period}"].rolling(3).mean()
            )

        # CCI
        for period in [14, 20]:
            typical_price = (data["high"] + data["low"] + data["close"]) / 3
            sma_tp = typical_price.rolling(period).mean()
            mad = typical_price.rolling(period).apply(
                lambda x: np.abs(x - x.mean()).mean()
            )
            features[f"cci_{period}"] = self.safe_divide(
                typical_price - sma_tp, 0.015 * mad
            )

        # Williams %R
        for period in [10, 14]:
            high_max = data["high"].rolling(period).max()
            low_min = data["low"].rolling(period).min()
            features[f"williams_r_{period}"] = -100 * self.safe_divide(
                high_max - data["close"], high_max - low_min
            )

        # MFI
        typical_price = (data["high"] + data["low"] + data["close"]) / 3
        money_flow = typical_price * data["volume"]

        for period in [10, 14]:
            positive_flow = money_flow.where(typical_price > typical_price.shift(), 0)
            negative_flow = money_flow.where(typical_price < typical_price.shift(), 0)

            positive_flow_sum = positive_flow.rolling(period).sum()
            negative_flow_sum = negative_flow.rolling(period).sum()

            mfi_ratio = self.safe_divide(positive_flow_sum, negative_flow_sum)
            features[f"mfi_{period}"] = 100 - (100 / (1 + mfi_ratio))

        # ADX
        for period in [10, 14, 20]:
            plus_dm = data["high"].diff()
            minus_dm = -data["low"].diff()
            plus_dm[plus_dm < 0] = 0
            minus_dm[minus_dm < 0] = 0

            tr = true_range.rolling(period).mean()
            plus_di = 100 * self.safe_divide(plus_dm.rolling(period).mean(), tr)
            minus_di = 100 * self.safe_divide(minus_dm.rolling(period).mean(), tr)

            dx = 100 * self.safe_divide(np.abs(plus_di - minus_di), plus_di + minus_di)
            features[f"adx_{period}"] = dx.rolling(period).mean()
            features[f"plus_di_{period}"] = plus_di
            features[f"minus_di_{period}"] = minus_di

        # 6. VOLUME FEATURES (15)

        # Volume MA and ratios
        for period in [5, 10, 20]:
            features[f"volume_ma_{period}"] = data["volume"].rolling(period).mean()
            features[f"volume_ratio_{period}"] = self.safe_divide(
                data["volume"], features[f"volume_ma_{period}"]
            )

        # OBV
        obv = (np.sign(data["close"].diff()) * data["volume"]).fillna(0).cumsum()
        features["obv"] = obv
        features["obv_ma_10"] = obv.rolling(10).mean()
        features["obv_ma_20"] = obv.rolling(20).mean()

        # Volume pressure
        features["volume_pressure"] = self.safe_divide(
            data["volume"] * np.sign(data["close"] - data["open"]),
            data["volume"].rolling(10).mean(),
        )

        # VWAP
        cumulative_volume = data["volume"].cumsum()
        cumulative_pv = (data["close"] * data["volume"]).cumsum()
        features["vwap"] = self.safe_divide(cumulative_pv, cumulative_volume)
        features["close_to_vwap"] = self.safe_divide(data["close"], features["vwap"])

        # 7. MICROSTRUCTURE (15)

        # Spread
        features["spread"] = data["high"] - data["low"]
        features["spread_pct"] = self.safe_divide(features["spread"], data["close"])
        features["high_low_ratio"] = self.safe_divide(data["high"], data["low"])

        # Position in range
        features["close_position"] = self.safe_divide(
            data["close"] - data["low"], data["high"] - data["low"]
        )

        # Shadows
        features["upper_shadow"] = self.safe_divide(
            data["high"] - np.maximum(data["open"], data["close"]), features["spread"]
        )
        features["lower_shadow"] = self.safe_divide(
            np.minimum(data["open"], data["close"]) - data["low"], features["spread"]
        )

        # Gaps
        features["gap"] = data["open"] - data["close"].shift()
        features["gap_pct"] = self.safe_divide(features["gap"], data["close"].shift())

        # Candle patterns
        body = data["close"] - data["open"]
        features["body_size"] = np.abs(body)
        features["body_ratio"] = self.safe_divide(
            features["body_size"], features["spread"]
        )
        features["is_bullish"] = (body > 0).astype(int)
        features["is_bearish"] = (body < 0).astype(int)
        features["is_doji"] = (features["body_ratio"] < 0.1).astype(int)

        # Price levels
        features["is_new_high_20"] = (
            data["high"] == data["high"].rolling(20).max()
        ).astype(int)
        features["is_new_low_20"] = (
            data["low"] == data["low"].rolling(20).min()
        ).astype(int)

        # 8. MARKET REGIME (10)

        # Trend strength
        for period in [10, 20]:
            returns = data["close"].pct_change(period)
            features[f"trend_strength_{period}"] = returns / returns.rolling(50).std()
            features[f"trend_direction_{period}"] = np.sign(returns)

        # Regime (above/below MA)
        for period in [20, 50]:
            features[f"regime_sma_{period}"] = (
                data["close"] > features[f"sma_{period}"]
            ).astype(int)
            features[f"regime_ema_{period}"] = (
                data["close"] > features[f"ema_{period}"]
            ).astype(int)

        # Volatility regime
        current_vol = features["volatility_20"]
        vol_ma = current_vol.rolling(50).mean()
        features["high_vol_regime"] = (current_vol > vol_ma * 1.5).astype(int)
        features["low_vol_regime"] = (current_vol < vol_ma * 0.7).astype(int)

        # 9. SUPPORT/RESISTANCE (10)

        # Pivot points
        features["pivot_point"] = (data["high"] + data["low"] + data["close"]) / 3
        features["r1"] = 2 * features["pivot_point"] - data["low"]
        features["r2"] = features["pivot_point"] + (data["high"] - data["low"])
        features["s1"] = 2 * features["pivot_point"] - data["high"]
        features["s2"] = features["pivot_point"] - (data["high"] - data["low"])

        # Distance to levels
        for period in [20, 50]:
            resistance = data["high"].rolling(period).max()
            support = data["low"].rolling(period).min()
            features[f"distance_to_resistance_{period}"] = self.safe_divide(
                resistance - data["close"], data["close"]
            )
            features[f"distance_to_support_{period}"] = self.safe_divide(
                data["close"] - support, data["close"]
            )

        # Breakout indicators
        features["breakout_up"] = (
            data["close"] > data["high"].shift().rolling(20).max()
        ).astype(int)
        features["breakout_down"] = (
            data["close"] < data["low"].shift().rolling(20).min()
        ).astype(int)

        # 10. LAG FEATURES (30)

        # Price lags
        for lag in [1, 2, 3, 5, 10]:
            features[f"close_lag_{lag}"] = data["close"].shift(lag)
            features[f"volume_lag_{lag}"] = data["volume"].shift(lag)
            features[f"returns_lag_{lag}"] = features["returns_1"].shift(lag)

        # Indicator lags
        for lag in [1, 2, 3]:
            features[f"rsi_14_lag_{lag}"] = features["rsi_14"].shift(lag)
            features[f"macd_lag_{lag}"] = features["macd"].shift(lag)
            features[f"adx_14_lag_{lag}"] = features["adx_14"].shift(lag)
            features[f"volatility_20_lag_{lag}"] = features["volatility_20"].shift(lag)
            features[f"volume_ratio_10_lag_{lag}"] = features["volume_ratio_10"].shift(
                lag
            )

        # 11. ROLLING STATISTICS (20)

        # Price statistics
        for period in [10, 20]:
            features[f"close_mean_{period}"] = data["close"].rolling(period).mean()
            features[f"close_std_{period}"] = data["close"].rolling(period).std()
            features[f"close_skew_{period}"] = data["close"].rolling(period).skew()
            features[f"close_kurt_{period}"] = data["close"].rolling(period).kurt()

        # Volume statistics
        for period in [10, 20]:
            features[f"volume_mean_{period}"] = data["volume"].rolling(period).mean()
            features[f"volume_std_{period}"] = data["volume"].rolling(period).std()
            features[f"volume_skew_{period}"] = data["volume"].rolling(period).skew()
            features[f"volume_kurt_{period}"] = data["volume"].rolling(period).kurt()

        # Return statistics
        for period in [10, 20]:
            features[f"returns_mean_{period}"] = (
                features["returns_1"].rolling(period).mean()
            )
            features[f"returns_std_{period}"] = (
                features["returns_1"].rolling(period).std()
            )

        # 12. ОБРЕЗАЕМ ДО 240 ПРИЗНАКОВ

        # Берем первые 240 колонок
        feature_cols = features.columns.tolist()[:240]

        # Если признаков меньше 240, дополняем нулями
        while len(feature_cols) < 240:
            new_col = f"padding_{len(feature_cols)}"
            features[new_col] = 0
            feature_cols.append(new_col)

        # Финальный DataFrame с ровно 240 признаками
        final_features = features[feature_cols]

        # Заполняем NaN значения
        final_features = final_features.fillna(method="ffill").fillna(0)

        # Проверка на бесконечности
        final_features = final_features.replace([np.inf, -np.inf], 0)

        self.logger.info(f"Создано признаков: {len(final_features.columns)}")

        return final_features
