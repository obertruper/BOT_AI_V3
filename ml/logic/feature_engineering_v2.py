"""
Инженерия признаков для криптовалютных данных - BOT_AI_V3 версия
Адаптирован из LLM TRANSFORM проекта с поддержкой:
- RobustScaler вместо StandardScaler
- Walk-forward validation
- Crypto-специфичные признаки
- Безопасное деление и обработка NaN/Inf
"""

# Для совместимости с логированием
import warnings
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
import ta
from sklearn.preprocessing import RobustScaler
from tqdm import tqdm

warnings.filterwarnings("ignore")

# BOT_AI_V3 imports
from core.logger import setup_logger


class FeatureEngineer:
    """Создание признаков для модели прогнозирования - BOT_AI_V3 версия"""

    def __init__(self, config: Dict):
        self.config = config
        self.logger = setup_logger(__name__)
        self.feature_config = config.get("features", {})
        self.scalers = {}
        self.process_position = (
            None  # Позиция для прогресс-баров при параллельной обработке
        )
        self.disable_progress = False  # Флаг для отключения прогресс-баров

    @staticmethod
    def safe_divide(
        numerator: pd.Series,
        denominator: pd.Series,
        fill_value=0.0,
        max_value=1000.0,
        min_denominator=1e-8,
    ) -> pd.Series:
        """ИСПРАВЛЕНО: Безопасное деление с правильной обработкой малых значений"""
        # Создаем безопасный знаменатель
        safe_denominator = denominator.copy()

        # Заменяем очень маленькие значения
        mask_small = safe_denominator.abs() < min_denominator
        safe_denominator[mask_small] = min_denominator

        # Выполняем деление
        result = numerator / safe_denominator

        # Клиппинг результата для предотвращения экстремальных значений
        result = result.clip(lower=-max_value, upper=max_value)

        # Обработка inf и nan
        result = result.replace([np.inf, -np.inf], [fill_value, fill_value])
        result = result.fillna(fill_value)

        return result

    def calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        """Улучшенный расчет VWAP с дополнительными проверками"""
        # Базовый расчет VWAP
        vwap = self.safe_divide(df["turnover"], df["volume"], fill_value=df["close"])

        # Дополнительная проверка: VWAP не должен сильно отличаться от close
        # Если VWAP слишком отличается от close (более чем в 2 раза), используем close
        mask_invalid = (vwap < df["close"] * 0.5) | (vwap > df["close"] * 2.0)
        vwap[mask_invalid] = df["close"][mask_invalid]

        return vwap

    def create_features(
        self,
        df: pd.DataFrame,
        train_end_date: Optional[str] = None,
        use_enhanced_features: bool = False,
    ) -> pd.DataFrame:
        """Создание всех признаков для датасета с walk-forward валидацией

        Args:
            df: DataFrame с raw данными
            train_end_date: дата окончания обучения для walk-forward нормализации
            use_enhanced_features: использовать ли расширенные признаки для direction prediction
        """
        # Адаптация для совместимости: timestamp → datetime
        if "timestamp" in df.columns and "datetime" not in df.columns:
            df = df.copy()
            df["datetime"] = df["timestamp"]
            self.logger.debug(
                "Переименована колонка timestamp → datetime для совместимости"
            )

        # Адаптация для совместимости: добавляем turnover если отсутствует
        if "turnover" not in df.columns:
            df = df.copy() if df is df else df
            # turnover = volume * price (приблизительно)
            df["turnover"] = df["volume"] * df["close"]
            self.logger.debug("Создана колонка turnover = volume * close")

        if not self.disable_progress:
            self.logger.info(
                f"🔧 Начинаем feature engineering для {df['symbol'].nunique()} символов"
            )

        # Валидация данных
        self._validate_data(df)

        featured_dfs = []
        all_symbols_data = {}  # Для enhanced features

        # Первый проход - базовые признаки
        for symbol in df["symbol"].unique():
            symbol_data = df[df["symbol"] == symbol].copy()
            symbol_data = symbol_data.sort_values("datetime")

            symbol_data = self._create_basic_features(symbol_data)
            symbol_data = self._create_technical_indicators(symbol_data)
            symbol_data = self._create_microstructure_features(symbol_data)
            symbol_data = self._create_rally_detection_features(symbol_data)
            symbol_data = self._create_signal_quality_features(symbol_data)
            symbol_data = self._create_futures_specific_features(symbol_data)
            symbol_data = self._create_ml_optimized_features(symbol_data)
            symbol_data = self._create_temporal_features(symbol_data)
            symbol_data = self._create_target_variables(symbol_data)

            featured_dfs.append(symbol_data)

            # Сохраняем для enhanced features
            if use_enhanced_features:
                all_symbols_data[symbol] = symbol_data.copy()

        result_df = pd.concat(featured_dfs, ignore_index=True)

        # ИСПРАВЛЕНО: cross-asset features нужны все символы, но если обрабатываем по одному - пропускаем
        # Если в df больше одного символа - создаем cross-asset features
        if df["symbol"].nunique() > 1:
            result_df = self._create_cross_asset_features(result_df)

        # Добавляем enhanced features если запрошено
        if use_enhanced_features:
            result_df = self._add_enhanced_features(result_df, all_symbols_data)

        # Обработка NaN значений
        result_df = self._handle_missing_values(result_df)

        # Walk-forward нормализация только если указана дата (иначе нормализация будет в prepare_trading_data.py)
        if train_end_date:
            result_df = self._normalize_walk_forward(result_df, train_end_date)

        self._log_feature_statistics(result_df)

        if not self.disable_progress:
            self.logger.info(
                f"✅ Feature engineering завершен. Создано {len(result_df.columns)} признаков для {len(result_df)} записей"
            )

        return result_df

    def _validate_data(self, df: pd.DataFrame):
        """Валидация целостности данных"""
        # ИСПРАВЛЕНО: Конвертация числовых колонок в правильные типы
        numeric_columns = ["open", "high", "low", "close", "volume", "turnover"]
        for col in numeric_columns:
            if col in df.columns:
                # Конвертируем в числовой тип, заменяя ошибки на NaN
                df[col] = pd.to_numeric(df[col], errors="coerce")
                # Заполняем NaN значения предыдущими значениями
                df[col] = df[col].ffill().bfill()

        # Проверка на отсутствующие значения
        if df.isnull().any().any():
            if not self.disable_progress:
                self.logger.warning("Обнаружены пропущенные значения в данных")

        # Проверка на аномальные цены
        price_changes = df.groupby("symbol")["close"].pct_change()
        extreme_moves = abs(price_changes) > 0.15  # >15% за 15 минут

        if extreme_moves.sum() > 0:
            if not self.disable_progress:
                self.logger.warning(
                    f"Обнаружено {extreme_moves.sum()} экстремальных движений цены"
                )

        # Проверка временных гэпов (только значительные разрывы > 2 часов)
        for symbol in df["symbol"].unique():
            symbol_data = df[df["symbol"] == symbol]
            time_diff = symbol_data["datetime"].diff()
            expected_diff = pd.Timedelta("15 minutes")
            # Считаем большими только разрывы больше 2 часов (8 интервалов)
            large_gaps = time_diff > expected_diff * 8

            if large_gaps.sum() > 0:
                if not self.disable_progress:
                    self.logger.warning(
                        f"Символ {symbol}: обнаружено {large_gaps.sum()} значительных временных разрывов (> 2 часов)"
                    )

    def _create_basic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Базовые признаки из OHLCV данных без look-ahead bias"""
        df["returns"] = np.log(df["close"] / df["close"].shift(1))

        # Доходности за разные периоды
        for period in [5, 10, 20]:
            df[f"returns_{period}"] = np.log(df["close"] / df["close"].shift(period))

        # Ценовые соотношения
        df["high_low_ratio"] = df["high"] / df["low"]
        df["close_open_ratio"] = df["close"] / df["open"]

        # Позиция закрытия в диапазоне
        df["close_position"] = (df["close"] - df["low"]) / (
            df["high"] - df["low"] + 1e-10
        )

        # Объемные соотношения с использованием только исторических данных
        df["volume_ratio"] = self.safe_divide(
            df["volume"],
            df["volume"].rolling(20, min_periods=20).mean(),
            fill_value=1.0,
        )
        df["turnover_ratio"] = self.safe_divide(
            df["turnover"],
            df["turnover"].rolling(20, min_periods=20).mean(),
            fill_value=1.0,
        )

        # VWAP с улучшенным расчетом
        df["vwap"] = self.calculate_vwap(df)

        # Более надежный расчет close_vwap_ratio
        # Нормальное соотношение close/vwap должно быть около 1.0
        # VWAP уже проверен и исправлен в calculate_vwap()

        # Простой и надежный расчет
        df["close_vwap_ratio"] = df["close"] / df["vwap"]

        # ИСПРАВЛЕНО: Расширенные границы для криптовалют (±30%)
        # Криптовалюты могут отклоняться от VWAP на 20-50% в периоды высокой волатильности
        df["close_vwap_ratio"] = df["close_vwap_ratio"].clip(lower=0.7, upper=1.3)

        # Добавляем индикатор экстремального отклонения от VWAP
        df["vwap_extreme_deviation"] = (
            (df["close_vwap_ratio"] < 0.85) | (df["close_vwap_ratio"] > 1.15)
        ).astype(int)

        # Дополнительная проверка на аномалии
        # Если ratio все еще выходит за разумные пределы, заменяем на 1.0
        mask_invalid = (df["close_vwap_ratio"] < 0.95) | (df["close_vwap_ratio"] > 1.05)
        if mask_invalid.sum() > 0:
            self.logger.debug(
                f"Заменено {mask_invalid.sum()} аномальных close_vwap_ratio на 1.0"
            )
            df.loc[mask_invalid, "close_vwap_ratio"] = 1.0

        return df

    def _create_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Технические индикаторы"""
        tech_config = self.feature_config.get("technical", [])

        # SMA
        sma_config = next((c for c in tech_config if c.get("name") == "sma"), {})
        if sma_config:
            for period in sma_config.get("periods", [20, 50]):
                df[f"sma_{period}"] = ta.trend.sma_indicator(df["close"], period)
                df[f"close_sma_{period}_ratio"] = df["close"] / df[f"sma_{period}"]

        # EMA
        ema_config = next((c for c in tech_config if c.get("name") == "ema"), {})
        if ema_config:
            for period in ema_config.get("periods", [12, 26]):
                df[f"ema_{period}"] = ta.trend.ema_indicator(df["close"], period)
                df[f"close_ema_{period}_ratio"] = df["close"] / df[f"ema_{period}"]

        # RSI
        rsi_config = next((c for c in tech_config if c.get("name") == "rsi"), {})
        if rsi_config:
            df["rsi"] = ta.momentum.RSIIndicator(
                df["close"], window=rsi_config.get("period", 14)
            ).rsi()

            df["rsi_oversold"] = (df["rsi"] < 30).astype(int)
            df["rsi_overbought"] = (df["rsi"] > 70).astype(int)

        # MACD
        macd_config = next((c for c in tech_config if c.get("name") == "macd"), {})
        if macd_config:
            macd = ta.trend.MACD(
                df["close"],
                window_slow=macd_config.get("slow", 26),
                window_fast=macd_config.get("fast", 12),
                window_sign=macd_config.get("signal", 9),
            )
            # Нормализуем MACD относительно цены для сравнимости между активами
            # MACD в абсолютных значениях может быть очень большим для дорогих активов
            df["macd"] = macd.macd() / df["close"] * 100  # В процентах от цены
            df["macd_signal"] = macd.macd_signal() / df["close"] * 100
            df["macd_diff"] = macd.macd_diff() / df["close"] * 100

        # Bollinger Bands
        bb_config = next(
            (c for c in tech_config if c.get("name") == "bollinger_bands"), {}
        )
        if bb_config:
            bb = ta.volatility.BollingerBands(
                df["close"],
                window=bb_config.get("period", 20),
                window_dev=bb_config.get("std_dev", 2),
            )
            df["bb_high"] = bb.bollinger_hband()
            df["bb_low"] = bb.bollinger_lband()
            df["bb_middle"] = bb.bollinger_mavg()
            # ИСПРАВЛЕНО: bb_width как процент от цены
            df["bb_width"] = self.safe_divide(
                df["bb_high"] - df["bb_low"],
                df["close"],
                fill_value=0.02,  # 2% по умолчанию
                max_value=0.5,  # Максимум 50% от цены
            )

            # ИСПРАВЛЕНО: bb_position теперь корректно рассчитывается с использованием абсолютной ширины
            # bb_position показывает где находится цена внутри канала Bollinger
            bb_range = df["bb_high"] - df["bb_low"]
            df["bb_position"] = self.safe_divide(
                df["close"] - df["bb_low"],
                bb_range,
                fill_value=0.5,
                max_value=2.0,  # Позволяем выходы за пределы для отслеживания прорывов
            )

            # Создаем индикаторы прорывов ПЕРЕД клиппингом
            df["bb_breakout_upper"] = (df["bb_position"] > 1).astype(int)
            df["bb_breakout_lower"] = (df["bb_position"] < 0).astype(int)
            df["bb_breakout_strength"] = (
                np.abs(df["bb_position"] - 0.5) * 2
            )  # Сила отклонения от центра

            # Теперь ограничиваем для совместимости
            df["bb_position"] = df["bb_position"].clip(0, 1)

        # ATR
        atr_config = next((c for c in tech_config if c.get("name") == "atr"), {})
        if atr_config:
            df["atr"] = ta.volatility.AverageTrueRange(
                df["high"], df["low"], df["close"], window=atr_config.get("period", 14)
            ).average_true_range()

            # ATR в процентах от цены с ограничением экстремальных значений
            df["atr_pct"] = self.safe_divide(
                df["atr"],
                df["close"],
                fill_value=0.01,  # 1% по умолчанию
                max_value=0.2,  # Максимум 20% от цены
            )

        # Дополнительные технические индикаторы для crypto
        self._add_crypto_specific_indicators(df)

        return df

    def _add_crypto_specific_indicators(self, df: pd.DataFrame):
        """Добавляет криптоспецифичные технические индикаторы"""

        # Stochastic
        stoch = ta.momentum.StochasticOscillator(
            df["high"], df["low"], df["close"], window=14, smooth_window=3
        )
        df["stoch_k"] = stoch.stoch()
        df["stoch_d"] = stoch.stoch_signal()

        # ADX
        adx = ta.trend.ADXIndicator(df["high"], df["low"], df["close"])
        df["adx"] = adx.adx()
        df["adx_pos"] = adx.adx_pos()
        df["adx_neg"] = adx.adx_neg()

        # Parabolic SAR
        psar = ta.trend.PSARIndicator(df["high"], df["low"], df["close"])
        df["psar"] = psar.psar()
        # Вместо отдельных psar_up и psar_down, создаем индикатор направления
        df["psar_trend"] = (df["close"] > df["psar"]).astype(float)

        # ИСПРАВЛЕНО: Нормализованное расстояние PSAR по волатильности
        # Деление на ATR делает метрику сравнимой между активами
        df["psar_distance"] = (df["close"] - df["psar"]) / df["close"]
        if "atr" in df.columns:
            df["psar_distance_normalized"] = (df["close"] - df["psar"]) / (
                df["atr"] + 1e-10
            )
        else:
            df["psar_distance_normalized"] = df["psar_distance"]

        # Volume Weighted Moving Average (VWMA)
        df["vwma_20"] = (df["close"] * df["volume"]).rolling(20).sum() / df[
            "volume"
        ].rolling(20).sum()
        df["close_vwma_ratio"] = df["close"] / df["vwma_20"]

        # Money Flow Index (MFI) - объемный осциллятор
        try:
            mfi = ta.volume.MFIIndicator(
                high=df["high"],
                low=df["low"],
                close=df["close"],
                volume=df["volume"],
                window=14,
            )
            df["mfi"] = mfi.money_flow_index()
            df["mfi_overbought"] = (df["mfi"] > 80).astype(int)
            df["mfi_oversold"] = (df["mfi"] < 20).astype(int)
        except:
            pass

        # Commodity Channel Index (CCI)
        try:
            cci = ta.trend.CCIIndicator(
                high=df["high"], low=df["low"], close=df["close"], window=20
            )
            df["cci"] = cci.cci()
            df["cci_overbought"] = (df["cci"] > 100).astype(int)
            df["cci_oversold"] = (df["cci"] < -100).astype(int)
        except:
            pass

        # Williams %R
        try:
            williams = ta.momentum.WilliamsRIndicator(
                high=df["high"], low=df["low"], close=df["close"], lbp=14
            )
            df["williams_r"] = williams.williams_r()
        except:
            pass

    def _create_microstructure_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Признаки микроструктуры рынка"""
        # Спред high-low
        df["hl_spread"] = self.safe_divide(
            df["high"] - df["low"], df["close"], fill_value=0.0
        )
        df["hl_spread_ma"] = df["hl_spread"].rolling(20).mean()

        # Направление цены и объем
        df["price_direction"] = np.sign(df["close"] - df["open"])
        df["directed_volume"] = df["volume"] * df["price_direction"]
        df["volume_imbalance"] = (
            df["directed_volume"].rolling(10).sum() / df["volume"].rolling(10).sum()
        )

        # Ценовое воздействие - улучшенная формула
        # ИСПРАВЛЕНО: Используем dollar volume для более точной оценки
        df["dollar_volume"] = df["volume"] * df["close"]
        # ИСПРАВЛЕНО v3: Масштабируем price_impact для криптовалют
        # где dollar_volume может быть от $10K до $100M+
        # log10($10K) ≈ 4, log10($1M) ≈ 6, log10($100M) ≈ 8
        # Умножаем на 100 для получения значимых значений price_impact
        df["price_impact"] = self.safe_divide(
            df["returns"].abs() * 100,  # Умножаем на 100 для правильного масштаба
            np.log10(df["dollar_volume"] + 100),  # log10 для правильного масштаба
            fill_value=0.0,
            max_value=0.1,  # Лимит для нового масштаба
        )

        # Альтернативная формула с логарифмом объема
        df["price_impact_log"] = self.safe_divide(
            df["returns"].abs(),
            np.log(df["volume"] + 10),  # Увеличен сдвиг для стабильности
            fill_value=0.0,
            max_value=0.01,
        )

        return df

    def _create_rally_detection_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Признаки для детекции ралли и разворотов"""
        # Моментум на разных периодах
        df["momentum_24h"] = (
            df["close"] / df["close"].shift(96) - 1
        )  # 96 свечей = 24 часа
        df["momentum_4h"] = (
            df["close"] / df["close"].shift(16) - 1
        )  # 16 свечей = 4 часа
        df["momentum_1h"] = df["close"] / df["close"].shift(4) - 1  # 4 свечи = 1 час

        # Детекция паттернов разворота
        df["higher_highs"] = (
            (df["high"] > df["high"].shift(1))
            & (df["high"].shift(1) > df["high"].shift(2))
        ).astype(int)

        df["lower_lows"] = (
            (df["low"] < df["low"].shift(1)) & (df["low"].shift(1) < df["low"].shift(2))
        ).astype(int)

        # Скорость изменения объема
        df["volume_acceleration"] = df["volume"] / df["volume"].shift(1) - 1
        df["volume_trend"] = (
            df["volume"].rolling(5).mean() > df["volume"].rolling(20).mean()
        ).astype(int)

        return df

    def _create_signal_quality_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Признаки качества торгового сигнала"""
        # Волатильность на разных периодах
        df["volatility_5m"] = df["returns"].rolling(20).std()
        df["volatility_1h"] = df["returns"].rolling(240).std()
        df["volatility_ratio"] = df["volatility_5m"] / (df["volatility_1h"] + 1e-10)

        # Консистентность направления
        df["trend_consistency"] = (
            df["returns"].rolling(10).apply(lambda x: (x > 0).sum() / len(x))
        )

        # Расстояния до ключевых уровней
        df["distance_to_high_20"] = (df["high"].rolling(20).max() - df["close"]) / df[
            "close"
        ]
        df["distance_to_low_20"] = (df["close"] - df["low"].rolling(20).min()) / df[
            "close"
        ]

        # Позиция в диапазоне
        range_20 = df["high"].rolling(20).max() - df["low"].rolling(20).min()
        df["position_in_range_20"] = self.safe_divide(
            df["close"] - df["low"].rolling(20).min(), range_20, fill_value=0.5
        )

        return df

    def _create_futures_specific_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Признаки специфичные для фьючерсов"""
        # Funding rate прокси (на основе премии спот/фьючерс)
        # Для упрощения используем объем как прокси для интереса
        df["funding_rate_proxy"] = self.safe_divide(
            df["volume"] - df["volume"].rolling(96).mean(),
            df["volume"].rolling(96).mean(),
            fill_value=0.0,
        )

        # Open Interest прокси
        df["oi_proxy"] = df["volume"].rolling(24).sum()
        df["oi_change"] = df["oi_proxy"].pct_change()

        # Ликвидность метрики
        df["liquidity_score"] = np.log(df["volume"] + 1) / np.log(
            df["hl_spread"] + 1e-6
        )

        return df

    def _create_ml_optimized_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Создание ML-оптимизированных признаков для 2024-2025"""
        if not self.disable_progress:
            self.logger.info("Создание ML-оптимизированных признаков...")

        # 1. Hurst Exponent - мера персистентности рынка
        # >0.5 = тренд, <0.5 = возврат к среднему, ~0.5 = случайное блуждание
        def hurst_exponent(ts, max_lag=20):
            """Вычисление экспоненты Херста"""
            lags = range(2, min(max_lag, len(ts) // 2))
            tau = []

            for lag in lags:
                pp = np.array(ts[:-lag])
                pn = np.array(ts[lag:])
                diff = pn - pp
                tau.append(np.sqrt(np.nanmean(diff**2)))

            if len(tau) > 0 and all(t > 0 for t in tau):
                poly = np.polyfit(np.log(lags), np.log(tau), 1)
                return poly[0] * 2.0
            return 0.5

        # Применяем Hurst для close с окном 50
        df["hurst_exponent"] = (
            df["close"]
            .rolling(50)
            .apply(lambda x: hurst_exponent(x) if len(x) == 50 else 0.5)
        )

        # 2. Market Efficiency Ratio - эффективность движения цены
        # Высокие значения = сильный тренд, низкие = боковик
        df["efficiency_ratio"] = self.safe_divide(
            (df["close"] - df["close"].shift(20)).abs(),
            df["close"].diff().abs().rolling(20).sum(),
        )

        # 3. Regime Detection Features
        # Определение рыночного режима (тренд/флэт/высокая волатильность)
        returns = df["close"].pct_change()

        # Realized volatility
        df["realized_vol_5m"] = returns.rolling(20).std() * np.sqrt(20)
        df["realized_vol_15m"] = returns.rolling(60).std() * np.sqrt(60)
        df["realized_vol_1h"] = returns.rolling(240).std() * np.sqrt(240)

        # GARCH-подобная волатильность (упрощенная)
        df["garch_vol"] = returns.rolling(20).apply(
            lambda x: np.sqrt(0.94 * x.var() + 0.06 * x.iloc[-1] ** 2)
            if len(x) > 0
            else 0
        )

        # Режим волатильности
        if "atr" in df.columns:
            atr_q25 = df["atr"].rolling(1000).quantile(0.25)
            atr_q75 = df["atr"].rolling(1000).quantile(0.75)
            df["vol_regime"] = 0  # Нормальная
            df.loc[df["atr"] < atr_q25, "vol_regime"] = -1  # Низкая
            df.loc[df["atr"] > atr_q75, "vol_regime"] = 1  # Высокая

        # 4. Information-theoretic features
        # Энтропия распределения доходностей
        def shannon_entropy(series, bins=10):
            """Вычисление энтропии Шеннона"""
            if len(series) < bins:
                return 0
            counts, _ = np.histogram(series, bins=bins)
            probs = counts / counts.sum()
            probs = probs[probs > 0]
            return -np.sum(probs * np.log(probs))

        df["return_entropy"] = returns.rolling(100).apply(lambda x: shannon_entropy(x))

        # 5. Autocorrelation features
        # Автокорреляция доходностей на разных лагах
        df["returns_ac_1"] = returns.rolling(50).apply(
            lambda x: x.autocorr(lag=1) if len(x) > 1 else 0
        )
        df["returns_ac_5"] = returns.rolling(50).apply(
            lambda x: x.autocorr(lag=5) if len(x) > 5 else 0
        )
        df["returns_ac_10"] = returns.rolling(50).apply(
            lambda x: x.autocorr(lag=10) if len(x) > 10 else 0
        )

        # 6. Jump detection
        # Обнаружение прыжков в цене
        df["price_jump"] = (returns.abs() > returns.rolling(100).std() * 3).astype(int)

        df["jump_intensity"] = df["price_jump"].rolling(50).mean()

        # Заполнение пропусков
        ml_features = [
            "hurst_exponent",
            "efficiency_ratio",
            "realized_vol_5m",
            "realized_vol_15m",
            "realized_vol_1h",
            "garch_vol",
            "return_entropy",
            "returns_ac_1",
            "returns_ac_5",
            "returns_ac_10",
            "price_jump",
            "jump_intensity",
        ]

        # Заполняем пропуски
        for feature in ml_features:
            if feature in df.columns:
                df[feature] = df[feature].fillna(method="ffill").fillna(0)

        return df

    def _create_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Временные признаки"""
        df["hour"] = df["datetime"].dt.hour
        df["minute"] = df["datetime"].dt.minute

        # Циклическое кодирование времени
        df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
        df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)

        df["dayofweek"] = df["datetime"].dt.dayofweek
        df["is_weekend"] = (df["dayofweek"] >= 5).astype(int)

        df["dow_sin"] = np.sin(2 * np.pi * df["dayofweek"] / 7)
        df["dow_cos"] = np.cos(2 * np.pi * df["dayofweek"] / 7)

        df["day"] = df["datetime"].dt.day
        df["month"] = df["datetime"].dt.month

        df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
        df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

        # Торговые сессии
        df["asian_session"] = ((df["hour"] >= 0) & (df["hour"] < 8)).astype(int)
        df["european_session"] = ((df["hour"] >= 7) & (df["hour"] < 16)).astype(int)
        df["american_session"] = ((df["hour"] >= 13) & (df["hour"] < 22)).astype(int)

        # Пересечение сессий
        df["session_overlap"] = (
            (df["asian_session"] + df["european_session"] + df["american_session"]) > 1
        ).astype(int)

        return df

    def _create_cross_asset_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Кросс-активные признаки"""
        if not self.disable_progress:
            self.logger.info("Создание кросс-активных признаков...")

        # BTC как базовый актив
        btc_data = df[df["symbol"] == "BTCUSDT"][
            ["datetime", "close", "returns"]
        ].copy()
        if len(btc_data) > 0:
            btc_data.rename(
                columns={"close": "btc_close", "returns": "btc_returns"}, inplace=True
            )

            df = df.merge(btc_data, on="datetime", how="left")

            # Корреляция с BTC
            for symbol in df["symbol"].unique():
                if symbol != "BTCUSDT":
                    mask = df["symbol"] == symbol
                    # ИСПРАВЛЕНО: используем min_periods для корреляции
                    df.loc[mask, "btc_correlation"] = (
                        df.loc[mask, "returns"]
                        .rolling(window=96, min_periods=50)
                        .corr(df.loc[mask, "btc_returns"])
                    )

            df.loc[df["symbol"] == "BTCUSDT", "btc_correlation"] = 1.0

            # Относительная сила к BTC
            df["relative_strength_btc"] = df["close"] / df["btc_close"]
            df["rs_btc_ma"] = df.groupby("symbol")["relative_strength_btc"].transform(
                lambda x: x.rolling(20, min_periods=10).mean()
            )

            # ИСПРАВЛЕНО: заполняем NaN значения для BTC-связанных признаков
            df["btc_close"] = (
                df["btc_close"].fillna(method="ffill").fillna(method="bfill")
            )
            df["btc_returns"] = df["btc_returns"].fillna(0.0)
            df["btc_correlation"] = df["btc_correlation"].fillna(
                0.5
            )  # нейтральная корреляция
            df["relative_strength_btc"] = df["relative_strength_btc"].fillna(1.0)
            df["rs_btc_ma"] = df["rs_btc_ma"].fillna(1.0)
        else:
            # Заполняем нулями если нет данных BTC
            df["btc_close"] = 0
            df["btc_returns"] = 0
            df["btc_correlation"] = 0
            df["relative_strength_btc"] = 0
            df["rs_btc_ma"] = 0

        # Определяем сектора
        defi_tokens = ["AAVEUSDT", "UNIUSDT", "CAKEUSDT", "DYDXUSDT"]
        layer1_tokens = ["ETHUSDT", "SOLUSDT", "AVAXUSDT", "DOTUSDT", "NEARUSDT"]
        meme_tokens = [
            "DOGEUSDT",
            "FARTCOINUSDT",
            "MELANIAUSDT",
            "TRUMPUSDT",
            "POPCATUSDT",
            "PNUTUSDT",
            "ZEREBROUSDT",
            "WIFUSDT",
        ]

        df["sector"] = "other"
        df.loc[df["symbol"].isin(defi_tokens), "sector"] = "defi"
        df.loc[df["symbol"].isin(layer1_tokens), "sector"] = "layer1"
        df.loc[df["symbol"].isin(meme_tokens), "sector"] = "meme"
        df.loc[df["symbol"] == "BTCUSDT", "sector"] = "btc"

        # Секторные доходности
        df["sector_returns"] = df.groupby(["datetime", "sector"])["returns"].transform(
            "mean"
        )

        # Относительная доходность к сектору
        df["relative_to_sector"] = df["returns"] - df["sector_returns"]

        # Ранк доходности
        df["returns_rank"] = df.groupby("datetime")["returns"].rank(pct=True)

        return df

    def _create_target_variables(self, df: pd.DataFrame) -> pd.DataFrame:
        """Создание целевых переменных БЕЗ УТЕЧЕК ДАННЫХ - версия 4.0"""
        if not self.disable_progress:
            self.logger.info("🎯 Создание целевых переменных v4.0 (без утечек)...")

        # Периоды для расчета будущих возвратов (в свечах по 15 минут)
        return_periods = {
            "15m": 1,  # 15 минут
            "1h": 4,  # 1 час
            "4h": 16,  # 4 часа
            "12h": 48,  # 12 часов
        }

        # Пороги для классификации направления
        # ОПТИМИЗИРОВАНЫ для баланса между качеством и количеством сигналов
        direction_thresholds = {
            "15m": 0.0015,  # 0.15% - уменьшает шум от мелких движений
            "1h": 0.003,  # 0.3% - фильтрует случайные колебания
            "4h": 0.007,  # 0.7% - фокус на значимых движениях
            "12h": 0.01,  # 1% - долгосрочные тренды
        }

        # Уровни прибыли для бинарных целевых
        profit_levels = {
            "1pct_4h": (0.01, 16),  # 1% за 4 часа
            "2pct_4h": (0.02, 16),  # 2% за 4 часа
            "3pct_12h": (0.03, 48),  # 3% за 12 часов
            "5pct_12h": (0.05, 48),  # 5% за 12 часов
        }

        # A. Базовые возвраты (4)
        for period_name, n_candles in return_periods.items():
            df[f"future_return_{period_name}"] = df.groupby("symbol")[
                "close"
            ].transform(lambda x: x.shift(-n_candles) / x - 1)

        # B. Направление движения (4)
        for period_name in return_periods.keys():
            future_return = df[f"future_return_{period_name}"]
            threshold = direction_thresholds[period_name]

            df[f"direction_{period_name}"] = pd.cut(
                future_return,
                bins=[-np.inf, -threshold, threshold, np.inf],
                labels=["DOWN", "FLAT", "UP"],
            )

        # C. Достижение уровней прибыли LONG (4) - используем только shift для будущих цен
        for level_name, (profit_threshold, n_candles) in profit_levels.items():
            # Для каждой строки проверяем достигнет ли максимальная цена нужного уровня
            max_future_returns = pd.DataFrame()
            for i in range(1, n_candles + 1):
                future_high = df.groupby("symbol")["high"].transform(
                    lambda x: x.shift(-i)
                )
                future_return = future_high / df["close"] - 1
                max_future_returns[f"return_{i}"] = future_return

            # Максимальный return за период
            max_return = max_future_returns.max(axis=1)
            df[f"long_will_reach_{level_name}"] = (
                max_return >= profit_threshold
            ).astype(int)

        # D. Достижение уровней прибыли SHORT (4)
        for level_name, (profit_threshold, n_candles) in profit_levels.items():
            # Для SHORT: проверяем минимальную цену
            min_future_returns = pd.DataFrame()
            for i in range(1, n_candles + 1):
                future_low = df.groupby("symbol")["low"].transform(
                    lambda x: x.shift(-i)
                )
                future_return = df["close"] / future_low - 1  # Для SHORT инвертируем
                min_future_returns[f"return_{i}"] = future_return

            # Максимальный return для SHORT за период
            max_return = min_future_returns.max(axis=1)
            df[f"short_will_reach_{level_name}"] = (
                max_return >= profit_threshold
            ).astype(int)

        # Итоговая статистика
        if not self.disable_progress:
            self.logger.info("  ✅ Создано 20 целевых переменных без утечек данных")
            for period in ["15m", "1h", "4h", "12h"]:
                if f"direction_{period}" in df.columns:
                    dist = df[f"direction_{period}"].value_counts(normalize=True) * 100
                    self.logger.info(
                        f"     {period}: UP={dist.get('UP', 0):.1f}%, DOWN={dist.get('DOWN', 0):.1f}%, FLAT={dist.get('FLAT', 0):.1f}%"
                    )

        return df

    def _normalize_walk_forward(
        self, df: pd.DataFrame, train_end_date: str
    ) -> pd.DataFrame:
        """Walk-forward нормализация с использованием RobustScaler"""
        if not self.disable_progress:
            self.logger.info(
                f"📊 Walk-forward нормализация с границей: {train_end_date}"
            )

        # Разделяем данные по времени
        train_mask = df["datetime"] <= pd.to_datetime(train_end_date)
        test_mask = ~train_mask

        # Столбцы для исключения из нормализации
        exclude_cols = [
            "id",
            "symbol",
            "timestamp",
            "datetime",
            "sector",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "turnover",
        ]

        # Целевые переменные
        target_cols = [
            col
            for col in df.columns
            if col.startswith(
                ("future_", "direction_", "long_will_reach_", "short_will_reach_")
            )
        ]
        exclude_cols.extend(target_cols)

        # Временные колонки (уже нормализованы)
        time_cols = [
            "hour",
            "minute",
            "dayofweek",
            "day",
            "month",
            "is_weekend",
            "asian_session",
            "european_session",
            "american_session",
            "session_overlap",
        ]
        exclude_cols.extend(time_cols)

        # Определяем числовые признаки для нормализации
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        feature_cols = [col for col in numeric_cols if col not in exclude_cols]

        if not self.disable_progress:
            self.logger.info(
                f"Нормализуем {len(feature_cols)} признаков для {df['symbol'].nunique()} символов"
            )

        # Нормализация по символам
        for symbol in df["symbol"].unique():
            symbol_mask = df["symbol"] == symbol
            train_symbol_mask = train_mask & symbol_mask
            test_symbol_mask = test_mask & symbol_mask

            if train_symbol_mask.sum() == 0:
                continue

            # Инициализируем RobustScaler для символа
            if symbol not in self.scalers:
                self.scalers[symbol] = RobustScaler()

            # Получаем train данные для обучения scaler
            train_data = df.loc[train_symbol_mask, feature_cols].dropna()

            if len(train_data) > 0:
                # Обучаем scaler только на train данных
                self.scalers[symbol].fit(train_data)

                # Применяем к train данным
                if train_symbol_mask.sum() > 0:
                    train_to_scale = df.loc[train_symbol_mask, feature_cols].fillna(0)
                    df.loc[train_symbol_mask, feature_cols] = self.scalers[
                        symbol
                    ].transform(train_to_scale)

                # Применяем к test данным
                if test_symbol_mask.sum() > 0:
                    test_to_scale = df.loc[test_symbol_mask, feature_cols].fillna(0)
                    df.loc[test_symbol_mask, feature_cols] = self.scalers[
                        symbol
                    ].transform(test_to_scale)

        if not self.disable_progress:
            self.logger.info("✅ Walk-forward нормализация завершена")

        return df

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Обработка пропущенных значений"""
        if not self.disable_progress:
            self.logger.info("Обработка пропущенных значений...")

        # Сохраняем информационные колонки
        info_cols = [
            "id",
            "symbol",
            "timestamp",
            "datetime",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "turnover",
        ]

        # Группируем по символам для правильной обработки
        processed_dfs = []

        for symbol in df["symbol"].unique():
            symbol_data = df[df["symbol"] == symbol].copy()

            # Для каждой колонки применяем соответствующий метод заполнения
            for col in symbol_data.columns:
                if col in info_cols:
                    continue

                if symbol_data[col].isna().any():
                    # Для категориальных переменных (Categorical dtype)
                    if hasattr(symbol_data[col], "cat"):
                        # Для категориальных переменных используем наиболее частую категорию или 'FLAT'
                        if "direction" in col:
                            symbol_data[col] = symbol_data[col].fillna("FLAT")
                        else:
                            # Используем моду (наиболее частое значение)
                            mode = symbol_data[col].mode()
                            if len(mode) > 0:
                                symbol_data[col] = symbol_data[col].fillna(mode.iloc[0])
                    # Для технических индикаторов используем forward fill
                    elif any(
                        indicator in col
                        for indicator in ["sma", "ema", "rsi", "macd", "bb_", "adx"]
                    ):
                        symbol_data[col] = symbol_data[col].ffill()
                    # Для остальных используем 0
                    else:
                        symbol_data[col] = symbol_data[col].fillna(0)

            # Удаляем первые строки где могут быть NaN из-за расчета индикаторов
            # Находим максимальный период среди всех индикаторов
            max_period = 50  # SMA50 требует минимум 50 периодов
            symbol_data = symbol_data.iloc[max_period:].copy()

            processed_dfs.append(symbol_data)

        result_df = pd.concat(processed_dfs, ignore_index=True)

        # Финальная проверка
        nan_count = result_df.isna().sum().sum()
        if nan_count > 0:
            if not self.disable_progress:
                self.logger.warning(
                    f"Остались {nan_count} NaN значений после обработки"
                )
            # Принудительно заполняем оставшиеся NaN
            for col in result_df.columns:
                if result_df[col].isna().any():
                    # Для категориальных переменных
                    if hasattr(result_df[col], "cat"):
                        if "direction" in col:
                            result_df[col] = result_df[col].fillna("FLAT")
                        else:
                            mode = result_df[col].mode()
                            if len(mode) > 0:
                                result_df[col] = result_df[col].fillna(mode.iloc[0])
                    # Для числовых колонок
                    elif pd.api.types.is_numeric_dtype(result_df[col]):
                        result_df[col] = result_df[col].fillna(0)

        # Проверка на бесконечные значения
        numeric_cols = result_df.select_dtypes(include=[np.number]).columns
        inf_count = np.isinf(result_df[numeric_cols]).sum().sum()
        if inf_count > 0:
            if not self.disable_progress:
                self.logger.warning(
                    f"Обнаружены {inf_count} бесконечных значений, заменяем на конечные"
                )
            # ИСПРАВЛЕНО: Заменяем бесконечности на 99-й персентиль для каждой колонки
            for col in numeric_cols:
                if np.isinf(result_df[col]).any():
                    # Вычисляем персентили на конечных значениях
                    finite_vals = result_df[col][np.isfinite(result_df[col])]
                    if len(finite_vals) > 0:
                        p99 = finite_vals.quantile(0.99)
                        p1 = finite_vals.quantile(0.01)
                        result_df[col] = result_df[col].replace(
                            [np.inf, -np.inf], [p99, p1]
                        )
                    else:
                        result_df[col] = result_df[col].replace(
                            [np.inf, -np.inf], [0, 0]
                        )

        if not self.disable_progress:
            self.logger.info(
                f"Обработка завершена. Итоговый размер: {len(result_df)} записей"
            )
        return result_df

    def _log_feature_statistics(self, df: pd.DataFrame):
        """Логирование статистики по признакам"""
        if self.disable_progress:
            return

        total_features = len(df.columns)
        numeric_features = len(df.select_dtypes(include=[np.number]).columns)
        categorical_features = len(
            df.select_dtypes(include=["object", "category"]).columns
        )

        self.logger.info("📊 Статистика признаков:")
        self.logger.info(f"   - Всего признаков: {total_features}")
        self.logger.info(f"   - Числовых: {numeric_features}")
        self.logger.info(f"   - Категориальных: {categorical_features}")
        self.logger.info(f"   - Записей: {len(df)}")
        self.logger.info(f"   - Символов: {df['symbol'].nunique()}")

        # Проверка на NaN и inf
        nan_count = df.isna().sum().sum()
        inf_count = np.isinf(df.select_dtypes(include=[np.number])).sum().sum()

        if nan_count > 0:
            self.logger.warning(f"   ⚠️ NaN значений: {nan_count}")
        if inf_count > 0:
            self.logger.warning(f"   ⚠️ Inf значений: {inf_count}")

    def _add_enhanced_features(
        self, df: pd.DataFrame, all_symbols_data: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """Добавление расширенных признаков для улучшения direction prediction

        Args:
            df: DataFrame с базовыми признаками
            all_symbols_data: словарь с данными всех символов для cross-asset features

        Returns:
            DataFrame с enhanced features
        """
        self.logger.info("🚀 Добавление enhanced features для direction prediction...")

        # Базовые enhanced features без внешних зависимостей
        enhanced_dfs = []

        # Обрабатываем каждый символ
        for symbol in df["symbol"].unique():
            symbol_data = df[df["symbol"] == symbol].copy()

            # Добавляем дополнительные признаки для direction prediction
            # 1. Улучшенные momentum индикаторы
            symbol_data["momentum_strength"] = (
                symbol_data["momentum_4h"].abs() + symbol_data["momentum_1h"].abs()
            ) / 2

            # 2. Volatility clustering
            symbol_data["vol_cluster"] = (
                symbol_data["volatility_5m"]
                > symbol_data["volatility_5m"].rolling(20).mean()
            ).astype(int)

            # 3. Price position in multiple timeframes
            for period in [10, 20, 50]:
                high_period = symbol_data["high"].rolling(period).max()
                low_period = symbol_data["low"].rolling(period).min()
                symbol_data[f"price_position_{period}"] = (
                    symbol_data["close"] - low_period
                ) / (high_period - low_period + 1e-10)

            enhanced_dfs.append(symbol_data)

        # Объединяем результаты
        result_df = pd.concat(enhanced_dfs, ignore_index=True)

        # Логируем статистику новых признаков
        original_cols = set(df.columns)
        new_cols = set(result_df.columns) - original_cols

        if new_cols:
            self.logger.info(f"✅ Добавлено {len(new_cols)} enhanced features")

        return result_df

    def prepare_trading_data_without_leakage(
        self,
        df: pd.DataFrame,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        disable_progress: bool = False,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Подготовка данных для торговли БЕЗ DATA LEAKAGE
        Используется правильное временное разделение и нормализация только на train данных

        Args:
            df: DataFrame с признаками
            train_ratio: доля данных для обучения
            val_ratio: доля данных для валидации
            disable_progress: отключить прогресс-бары

        Returns:
            Tuple[train_data, val_data, test_data]
        """

        self.disable_progress = disable_progress

        if not self.disable_progress:
            self.logger.info("🧹 Подготовка данных без data leakage...")
            self.logger.info("1/5 - Создание признаков для всех символов...")

        # 1. Создание признаков для всех символов
        # Признаки уже созданы в df, только проверяем
        featured_dfs = []
        for symbol in df["symbol"].unique():
            symbol_data = df[df["symbol"] == symbol].copy()
            featured_dfs.append(symbol_data)

        if not self.disable_progress:
            self.logger.info("2/5 - Объединение кросс-активных признаков...")
        result_df = pd.concat(featured_dfs, ignore_index=True)
        result_df = self._create_cross_asset_features(result_df)

        if not self.disable_progress:
            self.logger.info("3/5 - Обработка пропущенных значений...")
        result_df = self._handle_missing_values(result_df)

        # 2. Разделение данных ПО ВРЕМЕНИ (критично для предотвращения data leakage)
        if not self.disable_progress:
            self.logger.info("4/5 - Временное разделение данных...")
        train_data_list = []
        val_data_list = []
        test_data_list = []

        for symbol in result_df["symbol"].unique():
            symbol_data = result_df[result_df["symbol"] == symbol].sort_values(
                "datetime"
            )
            n = len(symbol_data)

            train_end = int(n * train_ratio)
            val_end = int(n * (train_ratio + val_ratio))

            train_data_list.append(symbol_data.iloc[:train_end])
            val_data_list.append(symbol_data.iloc[train_end:val_end])
            test_data_list.append(symbol_data.iloc[val_end:])

        train_data = pd.concat(train_data_list, ignore_index=True)
        val_data = pd.concat(val_data_list, ignore_index=True)
        test_data = pd.concat(test_data_list, ignore_index=True)

        # 3. ПРАВИЛЬНАЯ нормализация БЕЗ DATA LEAKAGE
        if not self.disable_progress:
            self.logger.info("5/5 - Нормализация без data leakage...")

        # Определяем признаки для нормализации
        exclude_cols = [
            "id",
            "symbol",
            "timestamp",
            "datetime",
            "sector",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "turnover",
        ]

        # Целевые переменные
        target_cols = [
            col
            for col in train_data.columns
            if col.startswith(("target_", "future_", "optimal_"))
        ]
        exclude_cols.extend(target_cols)

        # Временные колонки (уже нормализованы)
        time_cols = [
            "hour",
            "minute",
            "dayofweek",
            "day",
            "month",
            "is_weekend",
            "asian_session",
            "european_session",
            "american_session",
            "session_overlap",
        ]
        exclude_cols.extend(time_cols)

        # Признаки-соотношения, которые уже нормализованы по своей природе
        ratio_cols = [
            "close_vwap_ratio",
            "close_open_ratio",
            "high_low_ratio",
            "close_position",
            "bb_position",
            "position_in_range_20",
            "position_in_range_50",
            "position_in_range_100",
        ]
        exclude_cols.extend(ratio_cols)

        feature_cols = [col for col in train_data.columns if col not in exclude_cols]

        # Нормализация по символам
        unique_symbols = train_data["symbol"].unique()
        # В многопроцессорном режиме отключаем прогресс-бары
        if disable_progress:
            norm_iterator = unique_symbols
        else:
            norm_iterator = tqdm(unique_symbols, desc="Нормализация", unit="символ")

        for symbol in norm_iterator:
            # Маски для каждого символа
            train_mask = train_data["symbol"] == symbol
            val_mask = val_data["symbol"] == symbol
            test_mask = test_data["symbol"] == symbol

            if train_mask.sum() == 0:
                continue

            # Обучаем RobustScaler ТОЛЬКО на train данных
            if symbol not in self.scalers:
                self.scalers[symbol] = RobustScaler()

            # Получаем только валидные train данные
            train_symbol_data = train_data.loc[train_mask, feature_cols].dropna()

            # Сохраняем числовые колонки для использования во всем цикле
            numeric_feature_cols = []

            if len(train_symbol_data) > 0:
                # Очистка экстремальных значений в train данных
                train_cleaned = train_symbol_data.copy()

                # Проверяем типы данных и фильтруем только числовые колонки
                for col in feature_cols:
                    if col in train_cleaned.columns and pd.api.types.is_numeric_dtype(
                        train_cleaned[col]
                    ):
                        numeric_feature_cols.append(col)
                    else:
                        if not self.disable_progress:
                            self.logger.warning(
                                f"Колонка '{col}' не является числовой или отсутствует, пропускаем"
                            )

                for col in numeric_feature_cols:
                    # ИСПРАВЛЕНО: Дополнительная проверка и конвертация перед квантилями
                    # Конвертируем в числовой тип на случай если есть строки
                    train_cleaned[col] = pd.to_numeric(
                        train_cleaned[col], errors="coerce"
                    )

                    # Пропускаем колонки с только NaN значениями
                    if train_cleaned[col].notna().sum() == 0:
                        if not self.disable_progress:
                            self.logger.warning(
                                f"Колонка '{col}' содержит только NaN значения, пропускаем"
                            )
                        continue

                    # Клиппинг экстремальных значений
                    q01 = train_cleaned[col].quantile(0.01)
                    q99 = train_cleaned[col].quantile(0.99)
                    train_cleaned[col] = train_cleaned[col].clip(lower=q01, upper=q99)

                    # Замена inf на конечные значения
                    train_cleaned[col] = train_cleaned[col].replace(
                        [np.inf, -np.inf], [q99, q01]
                    )
                    train_cleaned[col] = train_cleaned[col].fillna(
                        train_cleaned[col].median()
                    )

                # Обучаем RobustScaler на очищенных train данных только по числовым колонкам
                self.scalers[symbol].fit(train_cleaned[numeric_feature_cols])

                # Применяем ко всем данным символа
                # Train
                train_valid_mask = train_mask & train_data[
                    numeric_feature_cols
                ].notna().all(axis=1)
                if train_valid_mask.sum() > 0:
                    train_to_scale = train_data.loc[
                        train_valid_mask, numeric_feature_cols
                    ].copy()
                    # Применяем ту же очистку
                    for col in numeric_feature_cols:
                        # ИСПРАВЛЕНО: Конвертация в числовой тип
                        train_to_scale[col] = pd.to_numeric(
                            train_to_scale[col], errors="coerce"
                        )

                        if train_to_scale[col].notna().sum() == 0:
                            continue

                        q01 = (
                            train_cleaned[col].quantile(0.01)
                            if col in train_cleaned.columns
                            else train_to_scale[col].quantile(0.01)
                        )
                        q99 = (
                            train_cleaned[col].quantile(0.99)
                            if col in train_cleaned.columns
                            else train_to_scale[col].quantile(0.99)
                        )
                        train_to_scale[col] = train_to_scale[col].clip(
                            lower=q01, upper=q99
                        )
                        train_to_scale[col] = train_to_scale[col].replace(
                            [np.inf, -np.inf], [q99, q01]
                        )
                        train_to_scale[col] = train_to_scale[col].fillna(
                            train_to_scale[col].median()
                        )

                    train_data.loc[train_valid_mask, numeric_feature_cols] = (
                        self.scalers[symbol].transform(train_to_scale)
                    )

                # Val
                val_valid_mask = val_mask & val_data[numeric_feature_cols].notna().all(
                    axis=1
                )
                if val_valid_mask.sum() > 0:
                    val_to_scale = val_data.loc[
                        val_valid_mask, numeric_feature_cols
                    ].copy()
                    # Применяем ту же очистку используя статистики из train
                    for col in numeric_feature_cols:
                        # ИСПРАВЛЕНО: Конвертация в числовой тип
                        val_to_scale[col] = pd.to_numeric(
                            val_to_scale[col], errors="coerce"
                        )

                        if val_to_scale[col].notna().sum() == 0:
                            continue

                        q01 = (
                            train_cleaned[col].quantile(0.01)
                            if col in train_cleaned.columns
                            else val_to_scale[col].quantile(0.01)
                        )
                        q99 = (
                            train_cleaned[col].quantile(0.99)
                            if col in train_cleaned.columns
                            else val_to_scale[col].quantile(0.99)
                        )
                        val_to_scale[col] = val_to_scale[col].clip(lower=q01, upper=q99)
                        val_to_scale[col] = val_to_scale[col].replace(
                            [np.inf, -np.inf], [q99, q01]
                        )
                        val_to_scale[col] = val_to_scale[col].fillna(
                            val_to_scale[col].median()
                        )

                    val_data.loc[val_valid_mask, numeric_feature_cols] = self.scalers[
                        symbol
                    ].transform(val_to_scale)

                # Test
                test_valid_mask = test_mask & test_data[
                    numeric_feature_cols
                ].notna().all(axis=1)
                if test_valid_mask.sum() > 0:
                    test_to_scale = test_data.loc[
                        test_valid_mask, numeric_feature_cols
                    ].copy()
                    # Применяем ту же очистку используя статистики из train
                    for col in numeric_feature_cols:
                        # ИСПРАВЛЕНО: Конвертация в числовой тип
                        test_to_scale[col] = pd.to_numeric(
                            test_to_scale[col], errors="coerce"
                        )

                        if test_to_scale[col].notna().sum() == 0:
                            continue

                        q01 = (
                            train_cleaned[col].quantile(0.01)
                            if col in train_cleaned.columns
                            else test_to_scale[col].quantile(0.01)
                        )
                        q99 = (
                            train_cleaned[col].quantile(0.99)
                            if col in train_cleaned.columns
                            else test_to_scale[col].quantile(0.99)
                        )
                        test_to_scale[col] = test_to_scale[col].clip(
                            lower=q01, upper=q99
                        )
                        test_to_scale[col] = test_to_scale[col].replace(
                            [np.inf, -np.inf], [q99, q01]
                        )
                        test_to_scale[col] = test_to_scale[col].fillna(
                            test_to_scale[col].median()
                        )

                    test_data.loc[test_valid_mask, numeric_feature_cols] = self.scalers[
                        symbol
                    ].transform(test_to_scale)

        # КРИТИЧНО: Удаляем строки с NaN в future переменных
        # NaN появляются в последних N строках каждого символа из-за shift(-N)
        future_cols = [col for col in train_data.columns if col.startswith("future_")]
        if future_cols:
            if not self.disable_progress:
                self.logger.info("🧑 Удаление строк с NaN в целевых переменных...")

            # Подсчет до удаления
            train_before = len(train_data)
            val_before = len(val_data)
            test_before = len(test_data)

            # Удаляем строки с NaN в любой из future колонок
            train_data = train_data.dropna(subset=future_cols)
            val_data = val_data.dropna(subset=future_cols)
            test_data = test_data.dropna(subset=future_cols)

            if not self.disable_progress:
                self.logger.info(
                    f"  Удалено строк: Train={train_before - len(train_data)}, "
                    f"Val={val_before - len(val_data)}, Test={test_before - len(test_data)}"
                )

        # Финальная статистика
        if not self.disable_progress:
            self.logger.info("✅ Размеры данных без data leakage:")
            self.logger.info(f"   - Train: {len(train_data)} записей")
            self.logger.info(f"   - Val: {len(val_data)} записей")
            self.logger.info(f"   - Test: {len(test_data)} записей")
            self.logger.info(f"   - Признаков: {len(feature_cols)}")

        return train_data, val_data, test_data
