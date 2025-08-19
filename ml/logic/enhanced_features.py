"""
Расширенные признаки для улучшения точности предсказаний направления
Включает market regime, microstructure и cross-asset features
"""

import warnings

import pandas as pd

warnings.filterwarnings("ignore")

import logging


class LoggerAdapter:
    """Адаптер для совместимости с методами логгера из обучающего файла"""

    def __init__(self, name):
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def info(self, msg):
        self.logger.info(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def error(self, msg):
        self.logger.error(msg)


class EnhancedFeatureEngineer:
    """Создание продвинутых признаков для direction prediction"""

    def __init__(self):
        self.logger = LoggerAdapter("EnhancedFeatures")
        self.btc_data = None  # Для cross-asset features

    def add_market_regime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Определение рыночного режима"""
        self.logger.info("🏛️ Добавляем market regime features...")

        # 1. Trend Regime (Trending vs Ranging)
        df["sma_20"] = df["close"].rolling(20).mean()
        df["sma_50"] = df["close"].rolling(50).mean()
        df["ema_20"] = df["close"].ewm(span=20).mean()

        # ADX для силы тренда
        df["trend_strength"] = self._calculate_adx(df, period=14)

        # Классификация режима
        df["regime_trend"] = 0  # 0=Ranging, 1=Uptrend, 2=Downtrend
        uptrend_mask = (df["ema_20"] > df["sma_50"]) & (df["trend_strength"] > 25)
        downtrend_mask = (df["ema_20"] < df["sma_50"]) & (df["trend_strength"] > 25)
        df.loc[uptrend_mask, "regime_trend"] = 1
        df.loc[downtrend_mask, "regime_trend"] = 2

        # 2. Volatility Regime
        df["volatility_20"] = df["close"].pct_change().rolling(20).std()
        df["volatility_50"] = df["close"].pct_change().rolling(50).std()
        df["volatility_ratio"] = df["volatility_20"] / df["volatility_50"].replace(0, 1)

        # Классификация волатильности
        df["regime_volatility"] = pd.qcut(
            df["volatility_ratio"], q=3, labels=[0, 1, 2], duplicates="drop"
        )  # Low, Medium, High

        # 3. Volume Regime
        df["volume_ma_20"] = df["volume"].rolling(20).mean()
        df["volume_ratio"] = df["volume"] / df["volume_ma_20"].replace(0, 1)

        # Volume spike detection
        df["volume_spike"] = (df["volume_ratio"] > 2.0).astype(int)

        return df

    def add_microstructure_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Микроструктурные признаки из order flow"""
        self.logger.info("🔬 Добавляем microstructure features...")

        # 1. Order Flow Imbalance (OFI)
        df["price_change"] = df["close"].diff()
        df["volume_imbalance"] = df.apply(
            lambda x: x["volume"] if x["price_change"] > 0 else -x["volume"], axis=1
        )
        df["ofi"] = df["volume_imbalance"].rolling(10).sum()
        df["ofi_normalized"] = df["ofi"] / df["volume"].rolling(10).sum().replace(0, 1)

        # 2. Trade Intensity
        # Используем quote_volume если есть, иначе volume * close
        if "quote_volume" not in df.columns:
            df["quote_volume"] = df["volume"] * df["close"]
        df["trade_intensity"] = df["volume"] / df["quote_volume"].replace(0, 1)
        df["trade_intensity_ma"] = df["trade_intensity"].rolling(20).mean()

        return df

    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Расчет ADX для определения силы тренда"""
        high = df["high"]
        low = df["low"]
        close = df["close"]

        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()

        # Directional movements
        up_move = high - high.shift()
        down_move = low.shift() - low

        pos_dm = pd.Series(0.0, index=df.index)
        neg_dm = pd.Series(0.0, index=df.index)

        pos_dm[(up_move > down_move) & (up_move > 0)] = up_move
        neg_dm[(down_move > up_move) & (down_move > 0)] = down_move

        # Smooth DM
        pos_di = 100 * (pos_dm.rolling(period).mean() / atr.replace(0, 1))
        neg_di = 100 * (neg_dm.rolling(period).mean() / atr.replace(0, 1))

        # ADX
        dx = 100 * abs(pos_di - neg_di) / (pos_di + neg_di).replace(0, 1)
        adx = dx.rolling(period).mean()

        return adx.fillna(25)  # Default ADX value

    def create_enhanced_features(
        self, df: pd.DataFrame, all_symbols_data: dict[str, pd.DataFrame] | None = None
    ) -> pd.DataFrame:
        """Главная функция для создания всех enhanced features"""
        self.logger.info("🚀 Создаем enhanced features для улучшения direction prediction...")

        # Сохраняем оригинальные колонки
        original_columns = df.columns.tolist()

        # Последовательно добавляем все группы признаков
        df = self.add_market_regime_features(df)
        df = self.add_microstructure_features(df)

        # Очистка NaN
        new_columns = [col for col in df.columns if col not in original_columns]
        df[new_columns] = df[new_columns].fillna(method="ffill").fillna(0)

        self.logger.info(f"✅ Добавлено {len(new_columns)} новых признаков")

        return df
