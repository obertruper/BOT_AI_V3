"""
Калькулятор технических индикаторов для торговой системы
"""

import logging
from typing import Any, Dict

import pandas as pd

logger = logging.getLogger(__name__)


class IndicatorCalculator:
    """Базовый калькулятор технических индикаторов"""

    def __init__(self):
        self.logger = logger

    def calculate_sma(self, data: pd.Series, period: int) -> pd.Series:
        """Простое скользящее среднее"""
        return data.rolling(window=period).mean()

    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """Экспоненциальное скользящее среднее"""
        return data.ewm(span=period, adjust=False).mean()

    def calculate_rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """Индекс относительной силы (RSI)"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_macd(
        self,
        data: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> Dict[str, pd.Series]:
        """MACD индикатор"""
        ema_fast = self.calculate_ema(data, fast_period)
        ema_slow = self.calculate_ema(data, slow_period)

        macd_line = ema_fast - ema_slow
        signal_line = self.calculate_ema(macd_line, signal_period)
        histogram = macd_line - signal_line

        return {"macd": macd_line, "signal": signal_line, "histogram": histogram}

    def calculate_bollinger_bands(
        self, data: pd.Series, period: int = 20, std_dev: int = 2
    ) -> Dict[str, pd.Series]:
        """Полосы Боллинджера"""
        sma = self.calculate_sma(data, period)
        std = data.rolling(window=period).std()

        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)

        return {"upper": upper, "middle": sma, "lower": lower}

    def calculate_stochastic(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14,
        smooth_k: int = 3,
        smooth_d: int = 3,
    ) -> Dict[str, pd.Series]:
        """Стохастический осциллятор"""
        lowest_low = low.rolling(window=period).min()
        highest_high = high.rolling(window=period).max()

        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        k_smooth = k_percent.rolling(window=smooth_k).mean()
        d_smooth = k_smooth.rolling(window=smooth_d).mean()

        return {"k": k_smooth, "d": d_smooth}

    def calculate_atr(
        self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
    ) -> pd.Series:
        """Average True Range (ATR)"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return atr

    def calculate_obv(self, close: pd.Series, volume: pd.Series) -> pd.Series:
        """On Balance Volume (OBV)"""
        obv = volume.where(close > close.shift(), -volume).cumsum()
        return obv

    def calculate_vwap(
        self, high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series
    ) -> pd.Series:
        """Volume Weighted Average Price (VWAP)"""
        typical_price = (high + low + close) / 3
        vwap = (typical_price * volume).cumsum() / volume.cumsum()
        return vwap

    def calculate_all_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Рассчитать все основные индикаторы"""
        results = {}

        try:
            # Скользящие средние
            results["sma_20"] = self.calculate_sma(df["close"], 20)
            results["sma_50"] = self.calculate_sma(df["close"], 50)
            results["ema_20"] = self.calculate_ema(df["close"], 20)

            # RSI
            results["rsi"] = self.calculate_rsi(df["close"])

            # MACD
            macd_data = self.calculate_macd(df["close"])
            results.update(macd_data)

            # Bollinger Bands
            bb_data = self.calculate_bollinger_bands(df["close"])
            results["bb_upper"] = bb_data["upper"]
            results["bb_middle"] = bb_data["middle"]
            results["bb_lower"] = bb_data["lower"]

            # Stochastic
            if "high" in df and "low" in df:
                stoch_data = self.calculate_stochastic(
                    df["high"], df["low"], df["close"]
                )
                results["stoch_k"] = stoch_data["k"]
                results["stoch_d"] = stoch_data["d"]

                # ATR
                results["atr"] = self.calculate_atr(df["high"], df["low"], df["close"])

                # VWAP
                if "volume" in df:
                    results["vwap"] = self.calculate_vwap(
                        df["high"], df["low"], df["close"], df["volume"]
                    )
                    results["obv"] = self.calculate_obv(df["close"], df["volume"])

        except Exception as e:
            self.logger.error(f"Ошибка при расчете индикаторов: {e}")

        return results
