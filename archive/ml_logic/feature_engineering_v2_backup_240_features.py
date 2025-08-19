"""
Инженерия признаков для криптовалютных данных - BOT_AI_V3 версия
Адаптирован из LLM TRANSFORM проекта с поддержкой:
- RobustScaler вместо StandardScaler
- Walk-forward validation
- Crypto-специфичные признаки
- Безопасное деление и обработка NaN/Inf
"""

import warnings

import numpy as np
import pandas as pd
import ta
from sklearn.preprocessing import RobustScaler
from tqdm import tqdm

# Для совместимости с логированием

warnings.filterwarnings("ignore")

# BOT_AI_V3 imports
from core.logger import setup_logger


class FeatureEngineer:
    """Создание признаков для модели прогнозирования - BOT_AI_V3 версия"""

    def __init__(self, config: dict, inference_mode: bool = False):
        self.config = config
        self.logger = setup_logger(__name__)
        self.feature_config = config.get("features", {})
        self.scalers = {}
        self.process_position = None  # Позиция для прогресс-баров при параллельной обработке
        self.disable_progress = False  # Флаг для отключения прогресс-баров

        # ИСПРАВЛЕНО: Устанавливаем флаг inference режима
        self._is_inference_mode = inference_mode

        # Сразу импортируем список признаков если inference_mode включен
        if inference_mode:
            try:
                from ml.config.features_240 import REQUIRED_FEATURES_240

                self._required_features = REQUIRED_FEATURES_240
                self.logger.info(
                    f"✅ Загружен список из {len(REQUIRED_FEATURES_240)} требуемых признаков для inference mode"
                )
            except ImportError:
                self.logger.warning("⚠️ Не удалось импортировать REQUIRED_FEATURES_240")
                self._required_features = None

        # Добавляем методы-заглушки для совместимости с оригинальным кодом
        if not hasattr(self.logger, "start_stage"):
            self.logger.start_stage = lambda *args, **kwargs: self.logger.info(
                f"Starting stage: {args[0] if args else 'unknown'}"
            )
        if not hasattr(self.logger, "end_stage"):
            self.logger.end_stage = lambda *args, **kwargs: self.logger.info(
                f"Completed stage: {args[0] if args else 'unknown'}"
            )

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
        train_end_date: str | None = None,
        use_enhanced_features: bool = False,
        inference_mode: bool = False,
    ) -> pd.DataFrame:
        """Создание всех признаков для датасета с walk-forward валидацией

        Args:
            df: DataFrame с raw данными
            train_end_date: дата окончания обучения для walk-forward нормализации
            use_enhanced_features: использовать ли расширенные признаки для direction prediction
            inference_mode: если True, генерирует только необходимые 240 признаков для inference
        """
        if not self.disable_progress:
            mode_str = " (inference mode - 240 features)" if inference_mode else ""
            self.logger.info(
                f"🔧 Начинаем feature engineering для {df['symbol'].nunique()} символов{mode_str}"
            )

        # В inference mode проверяем что признаки загружены
        if inference_mode and not hasattr(self, "_required_features"):
            try:
                from ml.config.features_240 import REQUIRED_FEATURES_240

                self._required_features = REQUIRED_FEATURES_240
            except ImportError:
                self.logger.warning(
                    "⚠️ Не удалось импортировать REQUIRED_FEATURES_240, используем все признаки"
                )
                inference_mode = False
                self._required_features = None

        # Валидация данных
        self._validate_data(df)

        # ИСПРАВЛЕНО: Добавляем turnover если отсутствует (необходимо для расчетов)
        if "turnover" not in df.columns:
            df["turnover"] = df["close"] * df["volume"]
            if not self.disable_progress:
                self.logger.info("✅ Добавлен столбец turnover (close * volume)")

        featured_dfs = []
        all_symbols_data = {}  # Для enhanced features

        # Первый проход - базовые признаки
        for symbol in df["symbol"].unique():
            symbol_data = df[df["symbol"] == symbol].copy()

            # ИСПРАВЛЕНО: Сортируем по datetime из индекса или колонки
            if "datetime" in symbol_data.columns:
                symbol_data = symbol_data.sort_values("datetime")
            else:
                # Сортируем по индексу, если datetime в индексе
                symbol_data = symbol_data.sort_index()

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

        # ИСПРАВЛЕНО: cross-asset features всегда нужны в inference mode
        # В inference mode создаем cross-asset features для всех символов
        if df["symbol"].nunique() > 1 or (inference_mode and self._is_inference_mode):
            result_df = self._create_cross_asset_features(result_df)

        # Добавляем enhanced features если запрошено
        if use_enhanced_features:
            result_df = self._add_enhanced_features(result_df, all_symbols_data)

        # Обработка NaN значений
        result_df = self._handle_missing_values(result_df)

        # Walk-forward нормализация только если указана дата (иначе нормализация будет в prepare_trading_data.py)
        if train_end_date:
            result_df = self._normalize_walk_forward(result_df, train_end_date)

        # В inference mode возвращаем только необходимые признаки
        if inference_mode and hasattr(self, "_required_features"):
            # Сохраняем метаданные
            metadata_cols = ["symbol", "datetime", "open", "high", "low", "close", "volume"]
            keep_cols = metadata_cols.copy()

            # ИСПРАВЛЕНО: Добавляем extra_feature признаки если их нет
            extra_features_to_add = [
                "extra_feature_12",
                "extra_feature_14",
                "extra_feature_16",
                "extra_feature_24",
                "extra_feature_48",
                "extra_feature_96",
                "extra_feature_192",
                "extra_feature_384",
                "extra_feature_768",
                "extra_feature_960",
            ]
            for extra_feat in extra_features_to_add:
                if extra_feat not in result_df.columns:
                    # Создаем placeholder признаки с нулевыми значениями
                    result_df[extra_feat] = 0.0

            if not self.disable_progress:
                self.logger.info(
                    f"🔧 Inference mode активен: требуется {len(self._required_features)} признаков"
                )
                self.logger.info(f"🔧 Доступно колонок: {len(result_df.columns)}")

            # Добавляем только те признаки из REQUIRED_FEATURES_240, которые есть в DataFrame
            missing_features = []

            for feature in self._required_features:
                if feature in result_df.columns:
                    keep_cols.append(feature)
                else:
                    # Если признака нет, создаем его с нулевыми значениями
                    result_df[feature] = 0.0
                    keep_cols.append(feature)
                    missing_features.append(feature)

            if missing_features and not self.disable_progress:
                self.logger.warning(
                    f"🔧 Отсутствующие признаки ({len(missing_features)}): {missing_features[:10]}..."
                )

            # Фильтруем DataFrame: в inference mode возвращаем ТОЛЬКО признаки без метаданных
            feature_cols = [col for col in keep_cols if col not in metadata_cols]
            # Но сохраняем метаданные для структуры (добавляем в конце)
            final_cols = feature_cols + metadata_cols
            result_df = result_df[final_cols]

            if not self.disable_progress:
                self.logger.info(
                    f"📊 Inference mode: оставлено {len(feature_cols)} признаков из {len(self._required_features)} требуемых"
                )
        elif inference_mode and not hasattr(self, "_required_features"):
            self.logger.error("❌ Inference mode включен, но _required_features не установлено!")

        self._log_feature_statistics(result_df)

        if not self.disable_progress:
            feature_count = (
                len(result_df.columns) - 7 if inference_mode else len(result_df.columns)
            )  # Вычитаем метаданные
            self.logger.info(
                f"✅ Feature engineering завершен. Создано {feature_count} признаков для {len(result_df)} записей"
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
                self.logger.warning(f"Обнаружено {extreme_moves.sum()} экстремальных движений цены")

        # Проверка временных гэпов (только значительные разрывы > 2 часов)
        # ИСПРАВЛЕНО: Работаем с datetime в индексе, а не в колонке
        for symbol in df["symbol"].unique():
            symbol_data = df[df["symbol"] == symbol]

            # Используем datetime из индекса или из колонки, если она есть
            if "datetime" in symbol_data.columns:
                time_series = symbol_data["datetime"]
            elif hasattr(symbol_data.index, "to_series"):
                time_series = symbol_data.index.to_series()
            else:
                # Если нет ни колонки, ни datetime индекса, пропускаем проверку
                continue

            time_diff = time_series.diff()
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

        # Доходности за разные периоды (РАСШИРЕНО для REQUIRED_FEATURES_240)
        # ИСПРАВЛЕНО: Добавлены все недостающие периоды из features_240.py
        returns_periods = [
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            11,
            13,
            15,
            20,
            25,
            30,
            35,
            40,
            45,
            50,
            60,
            70,
            80,
            90,
            100,
            120,
            150,
            200,
        ]
        for period in returns_periods:
            df[f"returns_{period}"] = np.log(df["close"] / df["close"].shift(period))

        # Волатильность за разные периоды (ИСПРАВЛЕНО для REQUIRED_FEATURES_240)
        # ИСПРАВЛЕНО: Добавлены все недостающие периоды включая volatility_2, volatility_3
        volatility_periods = [
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            11,
            13,
            15,
            20,
            25,
            30,
            35,
            40,
            45,
            50,
            60,
            70,
            80,
            90,
            100,
            150,
            200,
        ]
        for period in volatility_periods:
            df[f"volatility_{period}"] = (
                df["returns"].rolling(period, min_periods=max(1, period // 2)).std()
            )

        # Микроструктурные признаки (ДОБАВЛЕНО для REQUIRED_FEATURES_240)
        # Спред high-low (bid-ask spread аппроксимация)
        df["spread"] = self.safe_divide(df["high"] - df["low"], df["close"], fill_value=0.0)
        df["spread_ma_10"] = df["spread"].rolling(10, min_periods=5).mean()
        df["spread_std_10"] = df["spread"].rolling(10, min_periods=5).std()

        # Order imbalance (дисбаланс ордеров) - аппроксимация через направление цены и объем
        df["price_direction"] = np.sign(df["close"] - df["open"])
        df["order_imbalance"] = df["volume"] * df["price_direction"]
        df["order_imbalance_ma_10"] = df["order_imbalance"].rolling(10, min_periods=5).mean()
        df["order_imbalance_std_10"] = df["order_imbalance"].rolling(10, min_periods=5).std()

        # Buy/Sell pressure (давление покупателей/продавцов)
        # Позитивное движение = давление покупателей
        df["buy_pressure"] = np.where(df["price_direction"] > 0, df["volume"], 0)
        df["sell_pressure"] = np.where(df["price_direction"] < 0, df["volume"], 0)
        df["net_pressure"] = df["buy_pressure"] - df["sell_pressure"]

        df["buy_pressure_ma_10"] = df["buy_pressure"].rolling(10, min_periods=5).mean()
        df["sell_pressure_ma_10"] = df["sell_pressure"].rolling(10, min_periods=5).mean()
        df["net_pressure_ma_10"] = df["net_pressure"].rolling(10, min_periods=5).mean()

        # Order flow признаки
        for period in [5, 10, 20]:
            df[f"order_flow_{period}"] = (
                df["order_imbalance"].rolling(period, min_periods=max(1, period // 2)).sum()
            )
            # Order flow ratio
            total_volume = df["volume"].rolling(period, min_periods=max(1, period // 2)).sum()
            df[f"order_flow_ratio_{period}"] = self.safe_divide(
                df[f"order_flow_{period}"], total_volume, fill_value=0.0
            )

        # Ценовые соотношения
        df["high_low_ratio"] = df["high"] / df["low"]
        df["close_open_ratio"] = df["close"] / df["open"]

        # Позиция закрытия в диапазоне
        df["close_position"] = (df["close"] - df["low"]) / (df["high"] - df["low"] + 1e-10)

        # Объемные соотношения с использованием только исторических данных
        df["volume_ratio"] = self.safe_divide(
            df["volume"], df["volume"].rolling(20, min_periods=20).mean(), fill_value=1.0
        )
        df["turnover_ratio"] = self.safe_divide(
            df["turnover"], df["turnover"].rolling(20, min_periods=20).mean(), fill_value=1.0
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
            self.logger.debug(f"Заменено {mask_invalid.sum()} аномальных close_vwap_ratio на 1.0")
            df.loc[mask_invalid, "close_vwap_ratio"] = 1.0

        return df

    def _create_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """ИСПРАВЛЕНО: Рассчитывает ВСЕ технические индикаторы из REQUIRED_FEATURES_240"""

        # ========== RSI - все необходимые периоды ==========
        rsi_periods = [5, 14, 21]  # Из конфигурации features_240.py
        for period in rsi_periods:
            rsi_indicator = ta.momentum.RSIIndicator(df["close"], window=period)
            df[f"rsi_{period}"] = rsi_indicator.rsi()

        # Добавляем дополнительные RSI периоды для совместимости
        for period in [7, 30, 50, 70, 100]:
            rsi_indicator = ta.momentum.RSIIndicator(df["close"], window=period)
            df[f"rsi_{period}"] = rsi_indicator.rsi()

        # ========== SMA - все необходимые периоды ==========
        sma_periods = [5, 10, 20, 50, 100, 200]  # Из конфигурации features_240.py
        for period in sma_periods:
            df[f"sma_{period}"] = ta.trend.sma_indicator(df["close"], period)

        # ========== EMA - все необходимые периоды ==========
        ema_periods = [5, 10, 20, 50, 100, 200]  # Из конфигурации features_240.py
        for period in ema_periods:
            df[f"ema_{period}"] = ta.trend.ema_indicator(df["close"], period)
            # Расстояние от цены до EMA (нормализованное)
            df[f"ema_distance_{period}"] = self.safe_divide(
                df["close"] - df[f"ema_{period}"], df["close"], fill_value=0.0
            )

        # Дополнительные EMA периоды
        for period in [15, 30, 150, 250]:
            df[f"ema_{period}"] = ta.trend.ema_indicator(df["close"], period)
            df[f"ema_distance_{period}"] = self.safe_divide(
                df["close"] - df[f"ema_{period}"], df["close"], fill_value=0.0
            )

        # ========== MACD - все необходимые конфигурации ==========
        macd_configs = [
            (5, 13, 5),  # Быстрый MACD
            (5, 35, 5),  # ТРЕБУЕТСЯ: для REQUIRED_FEATURES_240
            (8, 21, 5),  # Средний MACD
            (12, 26, 9),  # Классический MACD
            (19, 39, 9),  # Медленный MACD
            (50, 100, 20),  # Очень медленный MACD
        ]

        for fast, slow, signal in macd_configs:
            macd = ta.trend.MACD(
                df["close"], window_fast=fast, window_slow=slow, window_sign=signal
            )
            # Нормализуем MACD относительно цены
            df[f"macd_{fast}_{slow}"] = self.safe_divide(macd.macd(), df["close"], fill_value=0.0)
            df[f"macd_signal_{fast}_{slow}"] = self.safe_divide(
                macd.macd_signal(), df["close"], fill_value=0.0
            )
            df[f"macd_hist_{fast}_{slow}"] = self.safe_divide(
                macd.macd_diff(), df["close"], fill_value=0.0
            )

        # ========== Bollinger Bands - все необходимые периоды ==========
        bb_periods = [10, 20, 30, 50, 100]
        for period in bb_periods:
            bb = ta.volatility.BollingerBands(df["close"], window=period, window_dev=2)
            df[f"bb_upper_{period}"] = bb.bollinger_hband()
            df[f"bb_middle_{period}"] = bb.bollinger_mavg()
            df[f"bb_lower_{period}"] = bb.bollinger_lband()

            # BB width (нормализованная)
            df[f"bb_width_{period}"] = self.safe_divide(
                bb.bollinger_hband() - bb.bollinger_lband(), df["close"], fill_value=0.02
            )

            # BB position (где находится цена внутри полос)
            bb_range = bb.bollinger_hband() - bb.bollinger_lband()
            df[f"bb_position_{period}"] = self.safe_divide(
                df["close"] - bb.bollinger_lband(), bb_range, fill_value=0.5
            ).clip(0, 1)

        # ========== ATR - все необходимые периоды ==========
        atr_periods = [7, 14, 21, 30, 50, 100]
        for period in atr_periods:
            atr = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], window=period)
            df[f"atr_{period}"] = atr.average_true_range()

        # ========== ADX - все необходимые периоды ==========
        adx_periods = [14, 21, 20, 30]  # Добавлен период 21 для REQUIRED_FEATURES_240
        for period in adx_periods:
            adx = ta.trend.ADXIndicator(df["high"], df["low"], df["close"], window=period)
            df[f"adx_{period}"] = adx.adx()
            df[f"plus_di_{period}"] = adx.adx_pos()
            df[f"minus_di_{period}"] = adx.adx_neg()
            df[f"dx_{period}"] = df[f"plus_di_{period}"] - df[f"minus_di_{period}"]

        # ========== CCI - все необходимые периоды ==========
        cci_periods = [14, 20, 30]
        for period in cci_periods:
            cci = ta.trend.CCIIndicator(df["high"], df["low"], df["close"], window=period)
            df[f"cci_{period}"] = cci.cci()

        # ========== Stochastic - все необходимые периоды ==========
        stoch_configs = [(14, 3), (21, 3)]  # Исправлено: используем период 3 для совместимости
        for k_period, d_period in stoch_configs:
            stoch = ta.momentum.StochasticOscillator(
                df["high"], df["low"], df["close"], window=k_period, smooth_window=d_period
            )
            df[f"stoch_k_{k_period}"] = stoch.stoch()  # ИСПРАВЛЕНО: убираем d_period из названия
            df[f"stoch_d_{k_period}"] = (
                stoch.stoch_signal()
            )  # ИСПРАВЛЕНО: убираем d_period из названия

        # Дополнительные stochastic с периодом 21 для D-линии
        stoch_21 = ta.momentum.StochasticOscillator(
            df["high"], df["low"], df["close"], window=21, smooth_window=3
        )
        df["stoch_k_21"] = stoch_21.stoch()
        df["stoch_d_21"] = stoch_21.stoch_signal()

        # ========== Williams %R - все необходимые периоды ==========
        willr_periods = [14, 21, 28]
        for period in willr_periods:
            willr = ta.momentum.WilliamsRIndicator(df["high"], df["low"], df["close"], lbp=period)
            df[f"williams_r_{period}"] = willr.williams_r()

        # ДОБАВЛЕНО: Williams %R для всех периодов из REQUIRED_FEATURES_240

        # ========== MFI - все необходимые периоды ==========
        mfi_periods = [14, 21, 20, 30]  # Добавлен период 21 для REQUIRED_FEATURES_240
        for period in mfi_periods:
            mfi = ta.volume.MFIIndicator(
                df["high"], df["low"], df["close"], df["volume"], window=period
            )
            df[f"mfi_{period}"] = mfi.money_flow_index()

        # ========== OBV и производные ==========
        obv = ta.volume.OnBalanceVolumeIndicator(df["close"], df["volume"])
        df["obv"] = obv.on_balance_volume()

        # Нормализованный OBV
        df["obv_norm"] = self.safe_divide(
            df["obv"] - df["obv"].rolling(50).mean(), df["obv"].rolling(50).std(), fill_value=0.0
        )

        # OBV SMA и EMA
        df["obv_sma_20"] = ta.trend.sma_indicator(df["obv"], 20)
        df["obv_ema_20"] = ta.trend.ema_indicator(df["obv"], 20)

        # ========== Дополнительные индикаторы ==========

        # Aroon
        for period in [14, 25]:
            aroon = ta.trend.AroonIndicator(df["high"], df["low"], window=period)
            df[f"aroon_up_{period}"] = aroon.aroon_up()
            df[f"aroon_down_{period}"] = aroon.aroon_down()

        # DPO (Detrended Price Oscillator)
        for period in [14, 20]:
            dpo = ta.trend.DPOIndicator(df["close"], window=period)
            df[f"dpo_{period}"] = dpo.dpo()

        # CMO (Chande Momentum Oscillator)
        for period in [14, 20]:
            cmo = ta.momentum.PercentageVolumeOscillator(
                df["volume"], window_slow=period * 2, window_fast=period
            )
            df[f"cmo_{period}"] = cmo.pvo()

        # ROC (Rate of Change)
        for period in [10, 20, 30, 50]:
            roc = ta.momentum.ROCIndicator(df["close"], window=period)
            df[f"roc_{period}"] = roc.roc()

        # RVI (Relative Vigor Index)
        for period in [10, 14]:
            # Простая аппроксимация RVI
            df[f"rvi_{period}"] = self.safe_divide(
                (df["close"] - df["open"]).rolling(period).mean(),
                (df["high"] - df["low"]).rolling(period).mean(),
                fill_value=0.0,
            )

        # TRIX
        for period in [14, 21, 30]:
            # Тройная экспоненциальная скользящая средняя
            ema1 = ta.trend.ema_indicator(df["close"], period)
            ema2 = ta.trend.ema_indicator(ema1, period)
            ema3 = ta.trend.ema_indicator(ema2, period)
            df[f"trix_{period}"] = ema3.pct_change()

        # PPO (Percentage Price Oscillator)
        ppo = ta.momentum.PercentagePriceOscillator(df["close"])
        df["ppo"] = ppo.ppo()
        df["ppo_signal"] = ppo.ppo_signal()
        df["ppo_hist"] = ppo.ppo_hist()

        # Mass Index
        mass_index = ta.trend.MassIndex(df["high"], df["low"])
        df["mass_index"] = mass_index.mass_index()

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
        df["adx_14"] = adx.adx()
        df["adx"] = df["adx_14"]  # Для совместимости
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
            df["psar_distance_normalized"] = (df["close"] - df["psar"]) / (df["atr"] + 1e-10)
        else:
            df["psar_distance_normalized"] = df["psar_distance"]

        # ===== НОВЫЕ ТЕХНИЧЕСКИЕ ИНДИКАТОРЫ (2024 best practices) =====

        # 1. Ichimoku Cloud - популярный в крипто
        try:
            ichimoku = ta.trend.IchimokuIndicator(
                high=df["high"],
                low=df["low"],
                window1=9,  # Tenkan-sen
                window2=26,  # Kijun-sen
                window3=52,  # Senkou Span B
            )
            df["ichimoku_tenkan"] = ichimoku.ichimoku_conversion_line()  # Tenkan-sen
            df["ichimoku_kijun"] = ichimoku.ichimoku_base_line()  # Kijun-sen
            df["ichimoku_conversion"] = df["ichimoku_tenkan"]  # Для совместимости
            df["ichimoku_base"] = df["ichimoku_kijun"]  # Для совместимости
            df["ichimoku_span_a"] = ichimoku.ichimoku_a()
            df["ichimoku_span_b"] = ichimoku.ichimoku_b()
            # Облако - расстояние между span A и B
            df["ichimoku_cloud_thickness"] = (df["ichimoku_span_a"] - df["ichimoku_span_b"]) / df[
                "close"
            ]
            # Позиция цены относительно облака
            df["price_vs_cloud"] = (
                df["close"] - (df["ichimoku_span_a"] + df["ichimoku_span_b"]) / 2
            ) / df["close"]
        except:
            pass

        # 2. Keltner Channels - альтернатива Bollinger Bands
        try:
            keltner = ta.volatility.KeltnerChannel(
                high=df["high"], low=df["low"], close=df["close"], window=20, window_atr=10
            )
            df["keltner_upper_20"] = keltner.keltner_channel_hband()
            df["keltner_middle_20"] = keltner.keltner_channel_mband()
            df["keltner_lower_20"] = keltner.keltner_channel_lband()
            df["keltner_position_20"] = (df["close"] - df["keltner_lower_20"]) / (
                df["keltner_upper_20"] - df["keltner_lower_20"]
            )
            # Для совместимости
            df["keltner_upper"] = df["keltner_upper_20"]
            df["keltner_middle"] = df["keltner_middle_20"]
            df["keltner_lower"] = df["keltner_lower_20"]
            df["keltner_position"] = df["keltner_position_20"]
        except:
            pass

        # 3. Donchian Channels - для определения прорывов
        try:
            donchian = ta.volatility.DonchianChannel(
                high=df["high"], low=df["low"], close=df["close"], window=20
            )
            df["donchian_upper_20"] = donchian.donchian_channel_hband()
            df["donchian_middle_20"] = donchian.donchian_channel_mband()
            df["donchian_lower_20"] = donchian.donchian_channel_lband()
            df["donchian_position_20"] = (df["close"] - df["donchian_lower_20"]) / (
                df["donchian_upper_20"] - df["donchian_lower_20"]
            )
            # Индикатор прорыва
            df["donchian_breakout"] = (
                (df["close"] > df["donchian_upper_20"].shift(1))
                | (df["close"] < df["donchian_lower_20"].shift(1))
            ).astype(int)
            # Для совместимости
            df["donchian_upper"] = df["donchian_upper_20"]
            df["donchian_middle"] = df["donchian_middle_20"]
            df["donchian_lower"] = df["donchian_lower_20"]
        except:
            pass

        # 4. Volume Weighted Moving Average (VWMA)
        df["vwma_20"] = (df["close"] * df["volume"]).rolling(20).sum() / df["volume"].rolling(
            20
        ).sum()
        df["close_vwma_ratio"] = df["close"] / df["vwma_20"]

        # 5. Money Flow Index (MFI) - объемный осциллятор
        try:
            mfi = ta.volume.MFIIndicator(
                high=df["high"], low=df["low"], close=df["close"], volume=df["volume"], window=14
            )
            df["mfi_14"] = mfi.money_flow_index()
            df["mfi"] = df["mfi_14"]  # Для совместимости
            df["mfi_overbought"] = (df["mfi"] > 80).astype(int)
            df["mfi_oversold"] = (df["mfi"] < 20).astype(int)
        except:
            pass

        # 6. Commodity Channel Index (CCI)
        try:
            cci = ta.trend.CCIIndicator(
                high=df["high"], low=df["low"], close=df["close"], window=20
            )
            df["cci_14"] = cci.cci()
            df["cci"] = df["cci_14"]  # Для совместимости
            df["cci_overbought"] = (df["cci"] > 100).astype(int)
            df["cci_oversold"] = (df["cci"] < -100).astype(int)
        except:
            pass

        # 7. Williams %R
        try:
            williams = ta.momentum.WilliamsRIndicator(
                high=df["high"], low=df["low"], close=df["close"], lbp=14
            )
            df["williams_r_14"] = williams.williams_r()
            df["williams_r"] = df["williams_r_14"]  # Для совместимости
        except:
            pass

        # 8. On Balance Volume (OBV)
        try:
            obv_indicator = ta.volume.OnBalanceVolumeIndicator(
                close=df["close"], volume=df["volume"]
            )
            df["obv"] = obv_indicator.on_balance_volume()
            # Нормализованный OBV
            df["obv_normalized"] = df["obv"] / (df["volume"].rolling(20).mean() + 1e-10)
        except:
            pass

        # 9. Ultimate Oscillator - комбинирует несколько периодов
        try:
            ultimate = ta.momentum.UltimateOscillator(
                high=df["high"], low=df["low"], close=df["close"], window1=7, window2=14, window3=28
            )
            df["ultimate_oscillator"] = ultimate.ultimate_oscillator()
        except:
            pass

        # 9. Accumulation/Distribution Index
        try:
            adl = ta.volume.AccDistIndexIndicator(
                high=df["high"], low=df["low"], close=df["close"], volume=df["volume"]
            )
            df["accumulation_distribution"] = adl.acc_dist_index()
        except:
            pass

        # 10. On Balance Volume (OBV)
        try:
            obv = ta.volume.OnBalanceVolumeIndicator(close=df["close"], volume=df["volume"])
            df["obv"] = obv.on_balance_volume()
            # OBV trend
            df["obv_ema"] = df["obv"].ewm(span=20).mean()
            df["obv_trend"] = (df["obv"] > df["obv_ema"]).astype(int)
        except:
            pass

        # 11. Chaikin Money Flow (CMF)
        try:
            cmf = ta.volume.ChaikinMoneyFlowIndicator(
                high=df["high"], low=df["low"], close=df["close"], volume=df["volume"], window=20
            )
            df["cmf"] = cmf.chaikin_money_flow()
        except:
            pass

        # 12. Average Directional Movement Index Rating (ADXR)
        try:
            adxr = ta.trend.ADXIndicator(
                high=df["high"], low=df["low"], close=df["close"], window=14
            )
            df["adxr"] = adxr.adx().rolling(14).mean()  # ADXR = среднее ADX
        except:
            pass

        # 13. Aroon Indicator
        try:
            aroon = ta.trend.AroonIndicator(close=df["close"], window=25)
            df["aroon_up"] = aroon.aroon_up()
            df["aroon_down"] = aroon.aroon_down()
            df["aroon_oscillator"] = df["aroon_up"] - df["aroon_down"]
        except:
            pass

        # 14. Pivot Points (поддержка/сопротивление)
        df["pivot"] = (df["high"] + df["low"] + df["close"]) / 3
        df["resistance1"] = 2 * df["pivot"] - df["low"]
        df["support1"] = 2 * df["pivot"] - df["high"]
        df["resistance2"] = df["pivot"] + (df["high"] - df["low"])
        df["support2"] = df["pivot"] - (df["high"] - df["low"])

        # Расстояние до уровней
        df["dist_to_resistance1"] = (df["resistance1"] - df["close"]) / df["close"]
        df["dist_to_support1"] = (df["close"] - df["support1"]) / df["close"]

        # 15. Rate of Change (ROC)
        try:
            roc = ta.momentum.ROCIndicator(close=df["close"], window=10)
            df["roc"] = roc.roc()
        except:
            pass

        # 16. Trix - тройное экспоненциальное сглаживание
        try:
            trix = ta.trend.TRIXIndicator(close=df["close"], window=15)
            df["trix"] = trix.trix()
        except:
            pass

        return df

    def _create_microstructure_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Признаки микроструктуры рынка"""
        # Спред high-low
        df["hl_spread"] = self.safe_divide(df["high"] - df["low"], df["close"], fill_value=0.0)
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
            max_value=10.0,
        )

        # ИСПРАВЛЕНО v3: Используем экспоненциальную формулу для toxicity
        # toxicity = exp(-price_impact * 20)
        # С новым масштабированием price_impact:
        # При price_impact=0.04: toxicity≈0.45
        # При price_impact=0.02: toxicity≈0.67
        # При price_impact=0.01: toxicity≈0.82
        df["toxicity"] = np.exp(-df["price_impact"] * 20)
        df["toxicity"] = df["toxicity"].clip(0.3, 1.0)

        # Амихуд неликвидность - скорректированная формула
        # Традиционная формула: |returns| / dollar_volume
        # Но мы масштабируем на миллион для получения значимых значений
        df["amihud_illiquidity"] = self.safe_divide(
            df["returns"].abs() * 1e6,  # Масштабируем на миллион
            df["turnover"],
            fill_value=0.0,
            max_value=100.0,  # Ограничиваем разумным максимумом
        )
        df["amihud_ma"] = df["amihud_illiquidity"].rolling(20).mean()

        # Кайл лямбда - правильная формула
        # ИСПРАВЛЕНО: |price_change| / volume, а не отношение std
        df["kyle_lambda"] = self.safe_divide(
            df["returns"].abs(), np.log(df["volume"] + 1), fill_value=0.0, max_value=10.0
        )

        # Альтернативная версия - отношение волатильностей
        df["volatility_volume_ratio"] = self.safe_divide(
            df["returns"].rolling(10).std(),
            df["volume"].rolling(10).std(),
            fill_value=0.0,
            max_value=10.0,
        )

        # Реализованная волатильность - правильная аннуализация
        # ИСПРАВЛЕНО: Разные периоды аннуализации
        # Для 15-минутных данных: 96 периодов в день, 365 дней в году
        df["realized_vol_1h"] = df["returns"].rolling(4).std() * np.sqrt(
            96
        )  # Часовая волатильность -> дневная
        df["realized_vol_daily"] = df["returns"].rolling(96).std() * np.sqrt(
            96
        )  # Дневная волатильность
        df["realized_vol_annual"] = df["returns"].rolling(96).std() * np.sqrt(
            96 * 365
        )  # Годовая волатильность

        # Для совместимости оставляем старое имя
        df["realized_vol"] = df["realized_vol_daily"]

        # Соотношение объема к волатильности
        # ИСПРАВЛЕНО: Используем log объема и нормализуем на средний объем
        avg_volume = df["volume"].rolling(96).mean()
        normalized_volume = df["volume"] / (avg_volume + 1)  # Нормализованный объем

        df["volume_volatility_ratio"] = self.safe_divide(
            normalized_volume,
            df["realized_vol"] * 100,  # Волатильность в процентах
            fill_value=1.0,
            max_value=100.0,  # Разумный лимит
        )

        return df

    def _create_rally_detection_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Создает ТОЧНО 15 признаков ралли из REQUIRED_FEATURES_240"""
        if not self.disable_progress:
            self.logger.info("🎯 Создание 15 RALLY_FEATURES...")

        # RALLY_FEATURES из features_240.py:
        # "current_rally_magnitude", "current_rally_duration", "current_rally_velocity",
        # "current_drawdown_magnitude", "current_drawdown_duration", "current_drawdown_velocity",
        # "recent_max_rally_1h", "recent_max_rally_4h", "recent_max_rally_12h",
        # "recent_max_drawdown_1h", "recent_max_drawdown_4h", "recent_max_drawdown_12h",
        # "prob_reach_1pct_4h", "prob_reach_2pct_4h", "prob_reach_3pct_12h"

        # 1. Текущие ралли/падения (6 признаков)
        # Рассчитываем текущий тренд начиная с последнего поворота

        # Определяем поворотные точки (локальные максимумы/минимумы)
        window = 5  # 75 минут для определения поворота
        local_max = (
            df["high"]
            .rolling(window * 2 + 1, center=True)
            .apply(lambda x: x.iloc[window] == x.max(), raw=False)
            .fillna(False)
        )
        local_min = (
            df["low"]
            .rolling(window * 2 + 1, center=True)
            .apply(lambda x: x.iloc[window] == x.min(), raw=False)
            .fillna(False)
        )

        # Находим индексы поворотных точек
        turning_points = local_max.astype(bool) | local_min.astype(bool)

        # Для каждой строки находим последнюю поворотную точку
        last_turn_idx = turning_points.cumsum().groupby(df.index).transform("last")
        last_turn_price = df["close"].where(turning_points).ffill()
        last_turn_high = df["high"].where(turning_points).ffill()
        last_turn_low = df["low"].where(turning_points).ffill()

        # Длительность с последнего поворота (в количестве периодов)
        # ИСПРАВЛЕНО: Обрабатываем как DatetimeIndex, так и RangeIndex
        turn_indices = df.index[turning_points].tolist()
        turn_duration = pd.Series(0, index=df.index, dtype=int)
        for i, idx in enumerate(df.index):
            # Находим последний поворот до текущего момента
            recent_turns = [t for t in turn_indices if t <= idx]
            if recent_turns:
                last_turn = recent_turns[-1]
                # Проверяем тип индекса и вычисляем длительность
                if isinstance(df.index, pd.DatetimeIndex):
                    # Для DatetimeIndex преобразуем timedelta в количество 15-минутных периодов
                    duration_timedelta = idx - last_turn
                    duration_periods = int(duration_timedelta.total_seconds() / (15 * 60))
                else:
                    # Для RangeIndex просто вычитаем индексы (уже в периодах)
                    duration_periods = i - df.index.get_loc(last_turn)
                turn_duration.iloc[i] = max(0, duration_periods)

        # Текущее ралли (рост от последнего минимума)
        current_is_rally = df["close"] > last_turn_price
        df["current_rally_magnitude"] = np.where(
            current_is_rally,
            (df["close"] / last_turn_price - 1) * 100,
            0.0,  # в процентах
        )
        df["current_rally_duration"] = np.where(current_is_rally, turn_duration, 0)
        df["current_rally_velocity"] = self.safe_divide(
            df["current_rally_magnitude"],
            df["current_rally_duration"] + 1,  # +1 чтобы избежать деления на 0
            fill_value=0.0,
        )

        # Текущее падение (падение от последнего максимума)
        current_is_drawdown = df["close"] < last_turn_price
        df["current_drawdown_magnitude"] = np.where(
            current_is_drawdown,
            (1 - df["close"] / last_turn_price) * 100,
            0.0,  # в процентах
        )
        df["current_drawdown_duration"] = np.where(current_is_drawdown, turn_duration, 0)
        df["current_drawdown_velocity"] = self.safe_divide(
            df["current_drawdown_magnitude"], df["current_drawdown_duration"] + 1, fill_value=0.0
        )

        if not self.disable_progress:
            self.logger.info("  ✓ Текущие ралли/падения: создано 6 признаков")

        # 2. Недавние максимумы ралли и падений (6 признаков)
        periods = {"1h": 4, "4h": 16, "12h": 48}  # в 15-минутных свечах

        for period_name, n_candles in periods.items():
            # Максимальное ралли за период
            max_rally = 0
            max_drawdown = 0

            for i in range(1, n_candles + 1):
                # Ралли: максимальный рост от минимума в окне
                rolling_min = df["low"].rolling(i, min_periods=1).min()
                rally = (df["high"] / rolling_min - 1) * 100
                max_rally = np.maximum(max_rally, rally)

                # Падение: максимальное падение от максимума в окне
                rolling_max = df["high"].rolling(i, min_periods=1).max()
                drawdown = (1 - df["low"] / rolling_max) * 100
                max_drawdown = np.maximum(max_drawdown, drawdown)

            df[f"recent_max_rally_{period_name}"] = max_rally
            df[f"recent_max_drawdown_{period_name}"] = max_drawdown

        if not self.disable_progress:
            self.logger.info("  ✓ Недавние максимумы: создано 6 признаков")

        # 3. Вероятности достижения уровней (3 признака)
        # Основано на исторической волатильности и текущем моментуме

        # Историческая волатильность
        returns = df["close"].pct_change()
        vol_4h = returns.rolling(16).std() * np.sqrt(16)  # 4-часовая волатильность
        vol_12h = returns.rolling(48).std() * np.sqrt(48)  # 12-часовая волатильность

        # Текущий моментум
        momentum_1h = df["close"].pct_change(4)
        momentum_4h = df["close"].pct_change(16)

        # Простая модель вероятности: базируется на волатильности и моментуме
        # P(reach X% in T hours) = sigmoid(momentum/volatility - threshold)

        def sigmoid(x):
            return 1 / (1 + np.exp(-np.clip(x, -10, 10)))

        # Нормализуем моментум относительно волатильности
        momentum_vol_ratio_4h = self.safe_divide(momentum_4h, vol_4h, fill_value=0.0)
        momentum_vol_ratio_12h = self.safe_divide(momentum_4h, vol_12h, fill_value=0.0)

        # Калибруем пороги так, чтобы базовая вероятность была ~30%
        # При нулевом моментуме: P = 0.3
        # threshold = -log(1/0.3 - 1) ≈ -0.85
        base_threshold = -0.85

        # 1% за 4 часа
        df["prob_reach_1pct_4h"] = sigmoid(momentum_vol_ratio_4h * 2 + base_threshold)

        # 2% за 4 часа
        df["prob_reach_2pct_4h"] = sigmoid(momentum_vol_ratio_4h * 1.5 + base_threshold - 0.5)

        # 3% за 12 часов
        df["prob_reach_3pct_12h"] = sigmoid(momentum_vol_ratio_12h * 1.2 + base_threshold - 0.3)

        if not self.disable_progress:
            self.logger.info("  ✓ Вероятности достижения уровней: создано 3 признака")

        # Итоговая проверка
        rally_features = [
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
        ]

        created_count = sum(1 for feat in rally_features if feat in df.columns)
        if not self.disable_progress:
            self.logger.info(f"✅ Rally features: создано {created_count}/15 признаков")

        # Заполняем NaN значения
        for feat in rally_features:
            if feat in df.columns:
                df[feat] = df[feat].fillna(0.0)

        return df

    def _create_signal_quality_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Создает ТОЧНО 15 признаков качества сигналов из REQUIRED_FEATURES_240"""
        if not self.disable_progress:
            self.logger.info("🎯 Создание 15 SIGNAL_QUALITY_FEATURES...")

        # SIGNAL_QUALITY_FEATURES из features_240.py:
        # "momentum_score", "trend_strength", "trend_consistency", "momentum_divergence",
        # "trend_acceleration", "trend_quality", "overbought_score", "oversold_score",
        # "divergence_bull", "divergence_bear", "pattern_strength", "breakout_strength",
        # "reversal_probability", "support_distance", "resistance_distance"

        # 1. Моментум и тренд (6 признаков)

        # momentum_score - комбинированная оценка моментума
        rsi_momentum = (
            (df["rsi"] - 50) / 50 if "rsi" in df.columns else pd.Series(0, index=df.index)
        )
        macd_momentum = (
            df["macd"] / (df["close"] * 0.01)
            if "macd" in df.columns
            else pd.Series(0, index=df.index)
        )
        price_momentum = df["close"].pct_change(10) * 10  # 10-периодный моментум
        df["momentum_score"] = (
            rsi_momentum + macd_momentum.fillna(0) + price_momentum.fillna(0)
        ) / 3
        df["momentum_score"] = df["momentum_score"].clip(-2, 2)  # Нормализуем в диапазон [-2, 2]

        # trend_strength - сила тренда из ADX или альтернатива
        if "adx" in df.columns:
            df["trend_strength"] = df["adx"] / 100  # Нормализуем ADX к [0, 1]
        else:
            # Альтернативная оценка силы тренда
            sma_short = df["close"].rolling(10).mean()
            sma_long = df["close"].rolling(50).mean()
            trend_diff = (sma_short - sma_long) / sma_long
            df["trend_strength"] = trend_diff.abs().rolling(20).mean().fillna(0.5)

        # trend_consistency - консистентность направления тренда
        price_direction = np.sign(df["close"] - df["close"].shift(1))
        df["trend_consistency"] = (
            price_direction.rolling(20).mean().abs()
        )  # Чем ближе к 1, тем консистентнее

        # momentum_divergence - дивергенция между ценой и моментумом
        price_momentum_20 = df["close"].pct_change(20)
        rsi_momentum_20 = (
            df["rsi"].diff(20) if "rsi" in df.columns else pd.Series(0, index=df.index)
        )
        # Нормализуем и сравниваем направления
        price_dir = np.sign(price_momentum_20)
        rsi_dir = np.sign(rsi_momentum_20)
        df["momentum_divergence"] = (price_dir != rsi_dir).astype(float)  # 1 = дивергенция, 0 = нет

        # trend_acceleration - ускорение тренда
        momentum_short = df["close"].pct_change(5)
        momentum_long = df["close"].pct_change(20)
        df["trend_acceleration"] = momentum_short - momentum_long  # Положительное = ускорение вверх

        # trend_quality - качество тренда (сила + консистентность)
        df["trend_quality"] = df["trend_strength"] * df["trend_consistency"]

        if not self.disable_progress:
            self.logger.info("  ✓ Моментум и тренд: создано 6 признаков")

        # 2. Уровни перекупленности/перепроданности (4 признака)

        # overbought_score - степень перекупленности
        if "rsi" in df.columns:
            rsi_overbought = np.maximum(0, df["rsi"] - 70) / 30  # Шкала от 0 до 1
        else:
            rsi_overbought = pd.Series(0, index=df.index)

        # Добавляем оценку от Bollinger Bands
        if "bb_position" in df.columns:
            bb_overbought = np.maximum(0, df["bb_position"] - 0.8) / 0.2
        else:
            bb_overbought = pd.Series(0, index=df.index)

        df["overbought_score"] = (rsi_overbought + bb_overbought) / 2

        # oversold_score - степень перепроданности
        if "rsi" in df.columns:
            rsi_oversold = np.maximum(0, 30 - df["rsi"]) / 30
        else:
            rsi_oversold = pd.Series(0, index=df.index)

        if "bb_position" in df.columns:
            bb_oversold = np.maximum(0, 0.2 - df["bb_position"]) / 0.2
        else:
            bb_oversold = pd.Series(0, index=df.index)

        df["oversold_score"] = (rsi_oversold + bb_oversold) / 2

        # divergence_bull - бычья дивергенция (цена падает, индикаторы растут)
        price_falling = df["close"] < df["close"].shift(10)
        if "rsi" in df.columns:
            rsi_rising = df["rsi"] > df["rsi"].shift(10)
            df["divergence_bull"] = (price_falling & rsi_rising).astype(float)
        else:
            df["divergence_bull"] = pd.Series(0, index=df.index)

        # divergence_bear - медвежья дивергенция (цена растет, индикаторы падают)
        price_rising = df["close"] > df["close"].shift(10)
        if "rsi" in df.columns:
            rsi_falling = df["rsi"] < df["rsi"].shift(10)
            df["divergence_bear"] = (price_rising & rsi_falling).astype(float)
        else:
            df["divergence_bear"] = pd.Series(0, index=df.index)

        if not self.disable_progress:
            self.logger.info("  ✓ Уровни перекупленности/перепроданности: создано 4 признака")

        # 3. Паттерны и сила (5 признаков)

        # pattern_strength - сила паттерна (на основе объема и волатильности)
        volume_relative = df["volume"] / df["volume"].rolling(20).mean()
        if "atr" in df.columns:
            volatility_relative = df["atr"] / df["atr"].rolling(20).mean()
        else:
            volatility_relative = df["close"].rolling(5).std() / df["close"].rolling(20).std()

        df["pattern_strength"] = (volume_relative * volatility_relative).fillna(1.0)
        df["pattern_strength"] = df["pattern_strength"].clip(
            0, 5
        )  # Ограничиваем экстремальные значения

        # breakout_strength - сила прорыва
        if "bb_position" in df.columns:
            # Прорыв Bollinger Bands
            bb_breakout = (df["bb_position"] > 1) | (df["bb_position"] < 0)
            breakout_magnitude = np.abs(df["bb_position"] - 0.5) * 2  # Сила отклонения от центра
        else:
            # Альтернативный расчет через ценовые уровни
            high_20 = df["high"].rolling(20).max()
            low_20 = df["low"].rolling(20).min()
            bb_breakout = (df["close"] > high_20) | (df["close"] < low_20)
            breakout_magnitude = np.maximum(
                (df["close"] - high_20) / high_20, (low_20 - df["close"]) / low_20
            ).fillna(0)

        df["breakout_strength"] = bb_breakout.astype(float) * breakout_magnitude

        # reversal_probability - вероятность разворота
        # Основана на экстремальных значениях индикаторов
        extreme_rsi = (
            (df["rsi"] > 80) | (df["rsi"] < 20)
            if "rsi" in df.columns
            else pd.Series(False, index=df.index)
        )
        extreme_bb = (
            (df["bb_position"] > 0.9) | (df["bb_position"] < 0.1)
            if "bb_position" in df.columns
            else pd.Series(False, index=df.index)
        )

        # Увеличиваем вероятность разворота при экстремальных значениях
        df["reversal_probability"] = (extreme_rsi.astype(float) + extreme_bb.astype(float)) / 2

        # support_distance - расстояние до ближайшей поддержки
        low_50 = df["low"].rolling(50).min()  # Поддержка за 50 периодов
        df["support_distance"] = (df["close"] - low_50) / df["close"]

        # resistance_distance - расстояние до ближайшего сопротивления
        high_50 = df["high"].rolling(50).max()  # Сопротивление за 50 периодов
        df["resistance_distance"] = (high_50 - df["close"]) / df["close"]

        if not self.disable_progress:
            self.logger.info("  ✓ Паттерны и сила: создано 5 признаков")

        # Итоговая проверка
        signal_quality_features = [
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
        ]

        created_count = sum(1 for feat in signal_quality_features if feat in df.columns)
        if not self.disable_progress:
            self.logger.info(f"✅ Signal quality features: создано {created_count}/15 признаков")

        # Заполняем NaN значения
        for feat in signal_quality_features:
            if feat in df.columns:
                df[feat] = df[feat].fillna(0.0)

        return df

    def _create_futures_specific_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Создает ТОЧНО 10 фьючерс-специфичных признаков из REQUIRED_FEATURES_240"""
        if not self.disable_progress:
            self.logger.info("🎯 Создание 10 FUTURES_FEATURES...")

        # FUTURES_FEATURES из features_240.py:
        # "funding_rate", "open_interest", "oi_change_1h", "long_short_ratio", "taker_buy_sell_ratio",
        # "funding_momentum", "oi_weighted_momentum", "liquidation_pressure", "basis_spread", "term_structure"

        # В реальной торговой системе эти данные должны поступать с биржи
        # Для обучения модели создаем синтетические признаки на основе OHLCV

        # 1. Основные метрики фьючерсов (5 признаков)

        # funding_rate - синтетический funding rate на основе momentum
        # Положительный momentum -> длинные позиции доминируют -> положительный funding
        momentum_4h = df["close"].pct_change(16)  # 4-часовой momentum
        df["funding_rate"] = np.tanh(momentum_4h * 50) * 0.001  # В диапазоне ±0.1%

        # open_interest - синтетический на основе объема
        # Высокий объем часто коррелирует с высоким open interest
        volume_normalized = df["volume"] / df["volume"].rolling(96).mean()
        df["open_interest"] = volume_normalized.rolling(24).mean()  # Сглаженный показатель

        # oi_change_1h - изменение open interest за час
        df["oi_change_1h"] = df["open_interest"].pct_change(4)  # За 4 периода = 1 час

        # long_short_ratio - на основе price momentum и volume
        # При росте цены на объеме -> больше длинных позиций
        price_change = df["close"].pct_change()
        volume_weight = volume_normalized.clip(0.1, 3.0)  # Ограничиваем экстремальные значения
        long_bias = pd.Series(
            np.where(price_change > 0, price_change * volume_weight, 0), index=df.index
        )
        short_bias = pd.Series(
            np.where(price_change < 0, abs(price_change) * volume_weight, 0), index=df.index
        )
        long_sum = long_bias.rolling(24).sum()
        short_sum = short_bias.rolling(24).sum()
        df["long_short_ratio"] = self.safe_divide(long_sum, short_sum, fill_value=1.0)

        # taker_buy_sell_ratio - на основе close vs vwap
        # Если close > vwap -> больше агрессивных покупок
        if "vwap" in df.columns:
            buy_pressure = np.maximum(0, df["close"] - df["vwap"]) / df["close"]
            sell_pressure = np.maximum(0, df["vwap"] - df["close"]) / df["close"]
        else:
            # Альтернатива через high/low
            buy_pressure = (df["close"] - df["low"]) / (df["high"] - df["low"] + 1e-10)
            sell_pressure = 1 - buy_pressure

        buy_sum = pd.Series(buy_pressure, index=df.index).rolling(12).sum()
        sell_sum = pd.Series(sell_pressure, index=df.index).rolling(12).sum()
        df["taker_buy_sell_ratio"] = self.safe_divide(buy_sum, sell_sum, fill_value=1.0)

        if not self.disable_progress:
            self.logger.info("  ✓ Основные метрики фьючерсов: создано 5 признаков")

        # 2. Производные метрики (5 признаков)

        # funding_momentum - изменение funding rate
        df["funding_momentum"] = df["funding_rate"].diff(4)  # Изменение за час

        # oi_weighted_momentum - momentum взвешенный на open interest
        price_momentum = df["close"].pct_change(12)  # 3-часовой momentum
        oi_weight = df["open_interest"] / (df["open_interest"].rolling(96).mean() + 1e-6)
        df["oi_weighted_momentum"] = price_momentum * oi_weight.clip(0.1, 3.0)

        # liquidation_pressure - давление ликвидаций
        # Высокое при резких движениях против trend + высокое плечо (через volatility)
        atr_normalized = (
            df["atr_pct"] / df["atr_pct"].rolling(96).mean()
            if "atr_pct" in df.columns
            else pd.Series(1, index=df.index)
        )
        price_shock = abs(df["close"].pct_change(4))  # Резкое движение за час
        df["liquidation_pressure"] = price_shock * atr_normalized * volume_normalized
        df["liquidation_pressure"] = df["liquidation_pressure"].clip(
            0, 5
        )  # Ограничиваем экстремальные значения

        # basis_spread - спред между фьючерсом и спотом
        # Синтетический на основе funding rate (они коррелируют)
        df["basis_spread"] = df["funding_rate"] * 8  # Примерно 8x от funding rate

        # term_structure - структура сроков
        # На основе volatility term structure (ближние vs дальние фьючерсы)
        vol_short = df["close"].rolling(24).std()  # Краткосрочная волатильность
        vol_long = df["close"].rolling(96).std()  # Долгосрочная волатильность
        df["term_structure"] = self.safe_divide(vol_short, vol_long, fill_value=1.0)

        if not self.disable_progress:
            self.logger.info("  ✓ Производные метрики: создано 5 признаков")

        # Итоговая проверка
        futures_features = [
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
        ]

        created_count = sum(1 for feat in futures_features if feat in df.columns)
        if not self.disable_progress:
            self.logger.info(f"✅ Futures features: создано {created_count}/10 признаков")

        # Заполняем NaN значения
        for feat in futures_features:
            if feat in df.columns:
                df[feat] = df[feat].fillna(0.0)

        return df

    def _create_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Создает ТОЧНО 12 временных признаков из REQUIRED_FEATURES_240"""
        if not self.disable_progress:
            self.logger.info("🎯 Создание 12 TEMPORAL_FEATURES...")

        # TEMPORAL_FEATURES из features_240.py:
        # "hour_sin", "hour_cos", "day_sin", "day_cos", "week_sin", "week_cos",
        # "month_sin", "month_cos", "is_weekend", "is_month_start", "is_month_end", "is_quarter_end"

        # 1. Циклические признаки времени (8 признаков)

        # ИСПРАВЛЕНО: Получаем datetime из индекса или колонки
        if "datetime" in df.columns:
            datetime_series = df["datetime"]
        else:
            # Используем индекс как datetime
            datetime_series = pd.Series(df.index, index=df.index)

        # Час дня (0-23)
        hour = datetime_series.dt.hour
        df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
        df["hour_cos"] = np.cos(2 * np.pi * hour / 24)

        # День месяца (1-31)
        day = datetime_series.dt.day
        df["day_sin"] = np.sin(2 * np.pi * day / 31)
        df["day_cos"] = np.cos(2 * np.pi * day / 31)

        # Неделя года (1-52)
        week = datetime_series.dt.isocalendar().week
        df["week_sin"] = np.sin(2 * np.pi * week / 52)
        df["week_cos"] = np.cos(2 * np.pi * week / 52)

        # Месяц года (1-12)
        month = datetime_series.dt.month
        df["month_sin"] = np.sin(2 * np.pi * month / 12)
        df["month_cos"] = np.cos(2 * np.pi * month / 12)

        if not self.disable_progress:
            self.logger.info("  ✓ Циклические признаки времени: создано 8 признаков")

        # 2. Категориальные временные признаки (4 признака)

        # Выходные дни
        dayofweek = datetime_series.dt.dayofweek
        df["is_weekend"] = (dayofweek >= 5).astype(int)  # Суббота=5, Воскресенье=6

        # Начало месяца (первые 3 дня)
        df["is_month_start"] = (day <= 3).astype(int)

        # Конец месяца (последние 4 дня)
        df["is_month_end"] = (day >= 28).astype(int)

        # Конец квартала (март, июнь, сентябрь, декабрь)
        df["is_quarter_end"] = month.isin([3, 6, 9, 12]).astype(int)

        if not self.disable_progress:
            self.logger.info("  ✓ Категориальные временные признаки: создано 4 признака")

        # Итоговая проверка
        temporal_features = [
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
        ]

        created_count = sum(1 for feat in temporal_features if feat in df.columns)
        if not self.disable_progress:
            self.logger.info(f"✅ Temporal features: создано {created_count}/12 признаков")

        # Заполняем NaN значения
        for feat in temporal_features:
            if feat in df.columns:
                df[feat] = df[feat].fillna(0.0)

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
            df["close"].rolling(50).apply(lambda x: hurst_exponent(x) if len(x) == 50 else 0.5)
        )

        # 2. Fractal Dimension - сложность ценового движения
        # 1 = прямая линия, 2 = заполняет плоскость
        def fractal_dimension(ts):
            """Вычисление фрактальной размерности методом Хигучи"""
            N = len(ts)
            if N < 10:
                return 1.5

            kmax = min(5, N // 2)
            L = []

            for k in range(1, kmax + 1):
                Lk = 0
                for m in range(k):
                    Lmk = 0
                    for i in range(1, int((N - m) / k)):
                        Lmk += abs(ts[m + i * k] - ts[m + (i - 1) * k])
                    if int((N - m) / k) > 0:
                        Lmk = Lmk * (N - 1) / (k * int((N - m) / k))
                    Lk += Lmk
                L.append(Lk / k)

            if len(L) > 0 and all(l > 0 for l in L):
                x = np.log(range(1, kmax + 1))
                y = np.log(L)
                poly = np.polyfit(x, y, 1)
                return poly[0]
            return 1.5

        df["fractal_dimension"] = (
            df["close"]
            .rolling(30)
            .apply(lambda x: fractal_dimension(x.values) if len(x) == 30 else 1.5)
        )

        # 3. Market Efficiency Ratio - эффективность движения цены
        # Высокие значения = сильный тренд, низкие = боковик
        df["efficiency_ratio"] = self.safe_divide(
            (df["close"] - df["close"].shift(20)).abs(), df["close"].diff().abs().rolling(20).sum()
        )

        # 4. Trend Quality Index - качество тренда
        # Комбинация ADX, направления и волатильности
        if "adx" in df.columns and "sma_50" in df.columns and "bb_width" in df.columns:
            df["trend_quality"] = (
                df["adx"]
                / 100  # Сила тренда
                * ((df["close"] > df["sma_50"]).astype(float) * 2 - 1)  # Направление
                * (
                    1 - df["bb_width"] / df["bb_width"].rolling(50).max()
                )  # Нормализованная волатильность
            )
        else:
            df["trend_quality"] = 0

        # 5. Regime Detection Features
        # Определение рыночного режима (тренд/флэт/высокая волатильность)
        returns = df["close"].pct_change()

        # Realized volatility
        df["realized_vol_5m"] = returns.rolling(20).std() * np.sqrt(20)
        df["realized_vol_15m"] = returns.rolling(60).std() * np.sqrt(60)
        df["realized_vol_1h"] = returns.rolling(240).std() * np.sqrt(240)

        # GARCH-подобная волатильность (упрощенная)
        # ИСПРАВЛЕНО: Улучшена обработка типов данных и NaN значений
        def garch_volatility(x):
            """Безопасная GARCH волатильность с проверкой типов"""
            try:
                if len(x) == 0 or x.isna().all():
                    return 0.0

                var_val = float(x.var())
                last_val = float(x.iloc[-1])

                if np.isnan(var_val) or np.isnan(last_val):
                    return 0.0

                result = 0.94 * var_val + 0.06 * (last_val**2)

                if result < 0:
                    return 0.0

                return float(np.sqrt(result))
            except (IndexError, ValueError, TypeError):
                return 0.0

        df["garch_vol"] = returns.rolling(20).apply(garch_volatility)

        # Режим волатильности
        if "atr" in df.columns:
            atr_q25 = df["atr"].rolling(1000).quantile(0.25)
            atr_q75 = df["atr"].rolling(1000).quantile(0.75)
            df["vol_regime"] = 0  # Нормальная
            df.loc[df["atr"] < atr_q25, "vol_regime"] = -1  # Низкая
            df.loc[df["atr"] > atr_q75, "vol_regime"] = 1  # Высокая

        # 6. Information-theoretic features
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

        # 7. Microstructure features
        # Amihud illiquidity
        if "amihud_illiquidity" not in df.columns:
            df["amihud_illiquidity"] = (
                self.safe_divide(returns.abs(), df["turnover"]).rolling(20).mean()
            )

        # Kyle's lambda (price impact)
        if "kyle_lambda" not in df.columns:
            df["kyle_lambda"] = self.safe_divide(
                returns.abs().rolling(20).mean(), df["volume"].rolling(20).mean()
            )

        # 8. Cross-sectional features (если есть данные BTC)
        if "btc_returns" in df.columns:
            # Beta к BTC
            df["btc_beta"] = (
                returns.rolling(100).cov(df["btc_returns"]) / df["btc_returns"].rolling(100).var()
            )

            # Идиосинкратическая волатильность
            df["idio_vol"] = (returns - df["btc_beta"] * df["btc_returns"]).rolling(50).std()

        # 9. Autocorrelation features
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
        df["returns_ac_20"] = returns.rolling(50).apply(
            lambda x: x.autocorr(lag=20) if len(x) > 20 else 0
        )

        # 10. Jump detection
        # Обнаружение прыжков в цене
        df["price_jump"] = (returns.abs() > returns.rolling(100).std() * 3).astype(int)

        df["jump_intensity"] = df["price_jump"].rolling(50).mean()

        # 10a. Volatility clustering - кластеризация волатильности
        # Высокая волатильность обычно следует за высокой волатильностью
        df["vol_clustering"] = returns.pow(2).rolling(20).mean().rolling(20).std()

        # 10b. Efficiency-adjusted volatility
        # Волатильность с учетом эффективности движения
        if "efficiency_ratio" in df.columns:
            df["efficiency_volatility"] = df["realized_vol_1h"] * (1 - df["efficiency_ratio"])
        else:
            df["efficiency_volatility"] = df["realized_vol_1h"]

        # 10c. Microstructure noise estimation
        # Оценка рыночного шума через первые разности
        df["microstructure_noise"] = (df["close"].diff() / df["close"]).rolling(20).std()

        # 10d. Дополнительные ML признаки для точного количества
        # Парные корреляции объема и цены
        df["vol_price_corr"] = df["volume"].rolling(50).corr(df["close"])
        df["vol_returns_corr"] = df["volume"].rolling(50).corr(returns.abs())

        # Волатильность волатильности (vol of vol)
        df["vol_of_vol"] = returns.rolling(20).std().rolling(20).std()

        # Относительная сила индекса (альтернативная)
        gains = returns.where(returns > 0, 0).rolling(14).mean()
        losses = -returns.where(returns < 0, 0).rolling(14).mean()
        df["rsi_alternative"] = 100 - (100 / (1 + gains / (losses + 1e-10)))

        # Тренд-фильтр Ходрика-Прескотта (упрощенный)
        df["hp_trend"] = df["close"].rolling(100).mean()
        df["hp_cycle"] = (df["close"] - df["hp_trend"]) / df["close"]

        # Интенсивность торгов (tick rule)
        df["trade_intensity"] = (df["volume"] / df["volume"].rolling(20).mean()) * np.sign(returns)

        # 11. Order flow imbalance persistence
        if "order_flow_imbalance" in df.columns:
            df["ofi_persistence"] = (
                df["order_flow_imbalance"]
                .rolling(20)
                .apply(lambda x: x.autocorr(lag=1) if len(x) > 1 else 0)
            )

        # 12. Volume-synchronized probability of informed trading (VPIN)
        # Упрощенная версия
        df["vpin"] = self.safe_divide(
            (df["volume"] * ((df["close"] > df["open"]).astype(float) - 0.5))
            .rolling(50)
            .sum()
            .abs(),
            df["volume"].rolling(50).sum(),
        )

        # 13. Liquidity-adjusted returns
        if "amihud_illiquidity" in df.columns:
            df["liquidity_adj_returns"] = returns * (
                1 - df["amihud_illiquidity"] / df["amihud_illiquidity"].rolling(100).max()
            )

        # 14. Tail risk measures
        # Conditional Value at Risk (CVaR)
        df["cvar_5pct"] = returns.rolling(100).apply(
            lambda x: (
                x[x <= x.quantile(0.05)].mean()
                if len(x[x <= x.quantile(0.05)]) > 0
                else x.quantile(0.05)
            )
        )

        # ДОБАВЛЯЕМ ВСЕ ОТСУТСТВУЮЩИЕ ML_OPTIMIZED_FEATURES из features_240.py

        # 15. Статистические признаки (price z-scores)
        df["price_z_score_20"] = (df["close"] - df["close"].rolling(20).mean()) / df[
            "close"
        ].rolling(20).std()
        df["price_z_score_50"] = (df["close"] - df["close"].rolling(50).mean()) / df[
            "close"
        ].rolling(50).std()
        df["price_z_score_100"] = (df["close"] - df["close"].rolling(100).mean()) / df[
            "close"
        ].rolling(100).std()

        # Volume z-scores
        df["volume_z_score_20"] = (df["volume"] - df["volume"].rolling(20).mean()) / df[
            "volume"
        ].rolling(20).std()
        df["volume_z_score_50"] = (df["volume"] - df["volume"].rolling(50).mean()) / df[
            "volume"
        ].rolling(50).std()

        # Return moments
        df["return_skewness_20"] = returns.rolling(20).skew()
        df["return_skewness_50"] = returns.rolling(50).skew()
        df["return_kurtosis_20"] = returns.rolling(20).kurt()
        df["return_kurtosis_50"] = returns.rolling(50).kurt()

        # Efficiency ratios
        df["price_efficiency_ratio"] = self.safe_divide(
            (df["close"] - df["close"].shift(20)).abs(), df["close"].diff().abs().rolling(20).sum()
        )
        df["volume_efficiency_ratio"] = self.safe_divide(
            (df["volume"] - df["volume"].shift(20)).abs(),
            df["volume"].diff().abs().rolling(20).sum(),
        )

        # Entropy features
        def rolling_entropy(series, window=20, bins=10):
            def entropy_calc(x):
                if len(x) < bins:
                    return 0
                counts, _ = np.histogram(x, bins=bins)
                probs = counts / counts.sum()
                probs = probs[probs > 0]
                return -np.sum(probs * np.log(probs))

            return series.rolling(window).apply(entropy_calc)

        df["entropy_20"] = rolling_entropy(returns, 20)
        df["entropy_50"] = rolling_entropy(returns, 50)

        # Autocorrelation features
        df["autocorrelation_lag_1"] = returns.rolling(50).apply(
            lambda x: x.autocorr(lag=1) if len(x) > 1 else 0
        )
        df["autocorrelation_lag_5"] = returns.rolling(50).apply(
            lambda x: x.autocorr(lag=5) if len(x) > 5 else 0
        )
        df["autocorrelation_lag_10"] = returns.rolling(50).apply(
            lambda x: x.autocorr(lag=10) if len(x) > 10 else 0
        )

        # Partial autocorrelation (simplified)
        df["partial_autocorr_1"] = df[
            "autocorrelation_lag_1"
        ]  # Для лага 1 частная корреляция = обычная
        df["partial_autocorr_5"] = df["autocorrelation_lag_5"] - df["autocorrelation_lag_1"] * df[
            "autocorrelation_lag_1"
        ].shift(4)

        # 16. Pattern recognition features
        # Higher highs, lower lows patterns
        df["higher_high"] = (
            (df["high"] > df["high"].shift(1)) & (df["high"].shift(1) > df["high"].shift(2))
        ).astype(float)
        df["lower_low"] = (
            (df["low"] < df["low"].shift(1)) & (df["low"].shift(1) < df["low"].shift(2))
        ).astype(float)
        df["higher_low"] = (
            (df["low"] > df["low"].shift(1)) & (df["low"].shift(1) > df["low"].shift(2))
        ).astype(float)
        df["lower_high"] = (
            (df["high"] < df["high"].shift(1)) & (df["high"].shift(1) < df["high"].shift(2))
        ).astype(float)

        # Candlestick patterns
        body = (df["close"] - df["open"]).abs()
        upper_shadow = df["high"] - np.maximum(df["open"], df["close"])
        lower_shadow = np.minimum(df["open"], df["close"]) - df["low"]

        df["bullish_engulfing"] = (
            (df["close"] > df["open"])
            & (df["close"].shift(1) < df["open"].shift(1))
            & (df["open"] < df["close"].shift(1))
            & (df["close"] > df["open"].shift(1))
        ).astype(float)

        df["bearish_engulfing"] = (
            (df["close"] < df["open"])
            & (df["close"].shift(1) > df["open"].shift(1))
            & (df["open"] > df["close"].shift(1))
            & (df["close"] < df["open"].shift(1))
        ).astype(float)

        df["hammer"] = (
            (lower_shadow > body * 2) & (upper_shadow < body * 0.1) & (body > 0)
        ).astype(float)

        df["shooting_star"] = (
            (upper_shadow > body * 2) & (lower_shadow < body * 0.1) & (body > 0)
        ).astype(float)

        df["doji"] = (body < (df["high"] - df["low"]) * 0.1).astype(float)

        # Three soldiers/crows patterns
        df["three_white_soldiers"] = (
            (df["close"] > df["open"])
            & (df["close"].shift(1) > df["open"].shift(1))
            & (df["close"].shift(2) > df["open"].shift(2))
            & (df["close"] > df["close"].shift(1))
            & (df["close"].shift(1) > df["close"].shift(2))
        ).astype(float)

        df["three_black_crows"] = (
            (df["close"] < df["open"])
            & (df["close"].shift(1) < df["open"].shift(1))
            & (df["close"].shift(2) < df["open"].shift(2))
            & (df["close"] < df["close"].shift(1))
            & (df["close"].shift(1) < df["close"].shift(2))
        ).astype(float)

        # Star patterns (simplified)
        gap_up = df["low"] > df["high"].shift(1)
        gap_down = df["high"] < df["low"].shift(1)

        df["morning_star"] = (
            (df["close"].shift(2) < df["open"].shift(2))  # Bearish candle
            & gap_down.shift(1)  # Gap down
            & (df["close"] > df["open"])  # Bullish candle
            & gap_up  # Gap up
        ).astype(float)

        df["evening_star"] = (
            (df["close"].shift(2) > df["open"].shift(2))  # Bullish candle
            & gap_up.shift(1)  # Gap up
            & (df["close"] < df["open"])  # Bearish candle
            & gap_down  # Gap down
        ).astype(float)

        # Harami patterns
        prev_body = (df["close"].shift(1) - df["open"].shift(1)).abs()
        df["harami_bull"] = (
            (df["close"].shift(1) < df["open"].shift(1))  # Bearish mother
            & (df["close"] > df["open"])  # Bullish baby
            & (body < prev_body * 0.5)  # Baby smaller than mother
        ).astype(float)

        df["harami_bear"] = (
            (df["close"].shift(1) > df["open"].shift(1))  # Bullish mother
            & (df["close"] < df["open"])  # Bearish baby
            & (body < prev_body * 0.5)  # Baby smaller than mother
        ).astype(float)

        # 17. Adaptive features
        # Adaptive momentum based on volatility
        vol_norm = df["realized_vol_1h"] / df["realized_vol_1h"].rolling(100).mean()
        df["adaptive_momentum"] = returns.rolling(10).mean() * vol_norm.clip(0.5, 2.0)

        # Adaptive volatility (GARCH-like)
        df["adaptive_volatility"] = returns.rolling(20).std() * np.sqrt(vol_norm.clip(0.5, 2.0))

        # Adaptive trend (trend strength adjusted for volatility)
        trend_raw = (df["close"].rolling(20).mean() - df["close"].rolling(50).mean()) / df["close"]
        df["adaptive_trend"] = trend_raw / (vol_norm + 0.01)

        # 18. Regime features
        # Market regimes based on volatility and trend
        vol_percentile = df["realized_vol_1h"].rolling(200).rank(pct=True)
        trend_strength = trend_raw.abs().rolling(50).rank(pct=True)

        df["regime_state"] = 0  # Normal
        df.loc[(vol_percentile > 0.8) & (trend_strength > 0.7), "regime_state"] = (
            1  # Trending high vol
        )
        df.loc[(vol_percentile > 0.8) & (trend_strength < 0.3), "regime_state"] = (
            2  # Sideways high vol
        )
        df.loc[(vol_percentile < 0.2) & (trend_strength > 0.7), "regime_state"] = (
            3  # Trending low vol
        )
        df.loc[(vol_percentile < 0.2) & (trend_strength < 0.3), "regime_state"] = (
            4  # Sideways low vol
        )

        # Market phase (bull/bear/sideways)
        trend_50 = (df["close"] / df["close"].rolling(50).mean() - 1) * 100
        df["market_phase"] = 0  # Sideways
        df.loc[trend_50 > 5, "market_phase"] = 1  # Bull
        df.loc[trend_50 < -5, "market_phase"] = -1  # Bear

        # Regime classifications (with NaN handling)
        try:
            df["volatility_regime"] = pd.cut(
                vol_percentile.fillna(0.5), bins=3, labels=[0, 1, 2], duplicates="drop"
            ).astype(float)
        except ValueError:
            df["volatility_regime"] = 1.0  # Default to normal regime

        try:
            df["trend_regime"] = pd.cut(
                trend_strength.fillna(0.5), bins=3, labels=[0, 1, 2], duplicates="drop"
            ).astype(float)
        except ValueError:
            df["trend_regime"] = 1.0  # Default to normal regime

        try:
            momentum_percentile = (
                df["adaptive_momentum"].abs().rolling(50).rank(pct=True).fillna(0.5)
            )
            df["momentum_regime"] = pd.cut(
                momentum_percentile, bins=3, labels=[0, 1, 2], duplicates="drop"
            ).astype(float)
        except ValueError:
            df["momentum_regime"] = 1.0

        try:
            volume_percentile = df["volume"].rolling(50).rank(pct=True).fillna(0.5)
            df["volume_regime"] = pd.cut(
                volume_percentile, bins=3, labels=[0, 1, 2], duplicates="drop"
            ).astype(float)
        except ValueError:
            df["volume_regime"] = 1.0

        # Correlation regime (if BTC data available)
        if "btc_returns" in df.columns:
            corr_rolling = returns.rolling(100).corr(df["btc_returns"])
            try:
                corr_percentile = corr_rolling.abs().rolling(50).rank(pct=True).fillna(0.5)
                df["correlation_regime"] = pd.cut(
                    corr_percentile, bins=3, labels=[0, 1, 2], duplicates="drop"
                ).astype(float)
            except ValueError:
                df["correlation_regime"] = 1.0
        else:
            df["correlation_regime"] = 1.0  # Default normal

        # 19. Basic price features
        df["median_price"] = (df["high"] + df["low"]) / 2
        df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3
        df["weighted_close"] = (df["high"] + df["low"] + 2 * df["close"]) / 4
        df["price_range"] = df["high"] - df["low"]
        df["true_range"] = np.maximum(
            df["high"] - df["low"],
            np.maximum(
                (df["high"] - df["close"].shift(1)).abs(), (df["low"] - df["close"].shift(1)).abs()
            ),
        )
        df["average_price"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4

        # Return features
        df["log_return"] = np.log(df["close"] / df["close"].shift(1))
        df["squared_return"] = returns**2
        df["abs_return"] = returns.abs()

        # Volume features
        df["volume_rate"] = df["volume"] / df["volume"].rolling(20).mean()
        df["volume_trend"] = (
            df["volume"].rolling(10).mean() / df["volume"].rolling(30).mean() - 1
        ) * 100
        df["volume_oscillator"] = (
            df["volume"].rolling(5).mean() / df["volume"].rolling(20).mean() - 1
        ) * 100

        # Price dynamics
        df["price_momentum"] = (df["close"] / df["close"].shift(10) - 1) * 100
        df["price_acceleration"] = df["price_momentum"] - df["price_momentum"].shift(5)
        df["price_jerk"] = df["price_acceleration"] - df["price_acceleration"].shift(5)

        # Rolling statistics
        df["rolling_min_5"] = df["close"].rolling(5).min()
        df["rolling_max_5"] = df["close"].rolling(5).max()
        df["rolling_median_5"] = df["close"].rolling(5).median()
        df["rolling_std_5"] = df["close"].rolling(5).std()
        df["rolling_var_5"] = df["close"].rolling(5).var()

        # Заполнение пропусков
        ml_features = [
            "hurst_exponent",
            "fractal_dimension",
            "efficiency_ratio",
            "trend_quality",
            "realized_vol_5m",
            "realized_vol_15m",
            "realized_vol_1h",
            "garch_vol",
            "vol_regime",
            "return_entropy",
            "amihud_illiquidity",
            "kyle_lambda",
            "returns_ac_1",
            "returns_ac_5",
            "returns_ac_10",
            "price_jump",
            "jump_intensity",
            "vpin",
            "liquidity_adj_returns",
            "cvar_5pct",
            # Новые ML признаки
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
            "entropy_20",
            "entropy_50",
            "autocorrelation_lag_1",
            "autocorrelation_lag_5",
            "autocorrelation_lag_10",
            "partial_autocorr_1",
            "partial_autocorr_5",
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

        # Добавляем условные признаки если они были созданы
        if "btc_beta" in df.columns:
            ml_features.extend(["btc_beta", "idio_vol"])
        if "ofi_persistence" in df.columns:
            ml_features.append("ofi_persistence")

        # Заполняем пропуски
        for feature in ml_features:
            if feature in df.columns:
                df[feature] = df[feature].fillna(method="ffill").fillna(0)

        if not self.disable_progress:
            created_count = sum(1 for feat in ml_features if feat in df.columns)
            self.logger.info(f"✅ ML optimized features: создано {created_count} признаков")

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
                        # Для категориальных переменных используем наиболее частую категорию или 'FLAT'/'HOLD'
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
            # ИСПРАВЛЕНО: Увеличиваем max_period для корректного расчета всех индикаторов
            max_period = 240  # Требуется для SMA/EMA_200 и других долгосрочных индикаторов
            if len(symbol_data) > max_period:
                symbol_data = symbol_data.iloc[max_period:].copy()
            else:
                # Если данных мало, оставляем все что есть
                pass

            processed_dfs.append(symbol_data)

        result_df = pd.concat(processed_dfs, ignore_index=True)

        # ИСПРАВЛЕНО: Улучшенная финальная проверка и обработка NaN
        nan_count = result_df.isna().sum().sum()
        if nan_count > 0:
            if not self.disable_progress:
                self.logger.warning(f"Остались {nan_count} NaN значений после обработки")
            # Более агрессивное заполнение NaN
            for col in result_df.columns:
                if result_df[col].isna().any():
                    # Для категориальных переменных
                    if hasattr(result_df[col], "cat") or result_df[col].dtype == "object":
                        if "direction" in col:
                            result_df[col] = result_df[col].fillna("FLAT")
                        else:
                            mode = result_df[col].mode()
                            if len(mode) > 0:
                                result_df[col] = result_df[col].fillna(mode.iloc[0])
                            else:
                                result_df[col] = result_df[col].fillna("UNKNOWN")
                    # Для числовых колонок
                    else:
                        # Сначала пробуем forward fill, потом backward fill, потом 0
                        result_df[col] = result_df[col].ffill().bfill().fillna(0)

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
                        result_df[col] = result_df[col].replace([np.inf, -np.inf], [p99, p1])
                    else:
                        result_df[col] = result_df[col].replace([np.inf, -np.inf], [0, 0])

        if not self.disable_progress:
            self.logger.info(f"Обработка завершена. Итоговый размер: {len(result_df)} записей")
        return result_df

    def _create_cross_asset_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Создает ТОЧНО 8 кросс-активных признаков из REQUIRED_FEATURES_240"""
        if not self.disable_progress:
            self.logger.info("🎯 Создание 8 CROSS_ASSET_FEATURES...")

        # CROSS_ASSET_FEATURES из features_240.py:
        # "btc_correlation_15m", "btc_correlation_1h", "btc_correlation_4h",
        # "eth_correlation_15m", "eth_correlation_1h", "eth_correlation_4h",
        # "market_beta_1h", "market_beta_4h"

        # ИСПРАВЛЕНО: Получаем данные базовых активов с поддержкой inference режима
        btc_data = (
            df[df["symbol"] == "BTCUSDT"][["datetime", "close"]].copy()
            if "BTCUSDT" in df["symbol"].values
            else pd.DataFrame()
        )
        eth_data = (
            df[df["symbol"] == "ETHUSDT"][["datetime", "close"]].copy()
            if "ETHUSDT" in df["symbol"].values
            else pd.DataFrame()
        )

        # ИСПРАВЛЕНО: Если это inference режим и нет BTC/ETH данных в DataFrame,
        # загружаем их из базы данных
        if (
            hasattr(self, "_is_inference_mode")
            and self._is_inference_mode
            and (len(btc_data) == 0 or len(eth_data) == 0)
        ):
            if not self.disable_progress:
                self.logger.info("🔄 Inference режим: загружаем BTC/ETH данные из БД...")
            btc_data, eth_data = self._load_btc_eth_data_for_inference(df)
            if not self.disable_progress:
                self.logger.info(
                    f"✅ Загружено BTC данных: {len(btc_data)}, ETH данных: {len(eth_data)}"
                )

        # ИСПРАВЛЕНО: Обработка BTC данных с защитой от NaN и типов
        if len(btc_data) > 0:
            # ИСПРАВЛЕНО: Конвертируем Decimal в float для корректных вычислений
            btc_data["close"] = btc_data["close"].astype(float)
            btc_data["btc_returns"] = btc_data["close"].pct_change()
            btc_data = btc_data[["datetime", "btc_returns"]].copy()
            # Убираем первую строку с NaN
            btc_data = btc_data.dropna()
            df = df.merge(btc_data, on="datetime", how="left")
            # Заполняем пропуски нулями и конвертируем в float
            df["btc_returns"] = df["btc_returns"].astype(float).fillna(0.0)
        else:
            if not self.disable_progress:
                self.logger.warning("⚠️ BTC данные недоступны, используем нулевые значения")
            df["btc_returns"] = 0.0

        # ИСПРАВЛЕНО: Обработка ETH данных с защитой от NaN и типов
        if len(eth_data) > 0:
            # ИСПРАВЛЕНО: Конвертируем Decimal в float для корректных вычислений
            eth_data["close"] = eth_data["close"].astype(float)
            eth_data["eth_returns"] = eth_data["close"].pct_change()
            eth_data = eth_data[["datetime", "eth_returns"]].copy()
            # Убираем первую строку с NaN
            eth_data = eth_data.dropna()
            df = df.merge(eth_data, on="datetime", how="left")
            # Заполняем пропуски нулями и конвертируем в float
            df["eth_returns"] = df["eth_returns"].astype(float).fillna(0.0)
        else:
            if not self.disable_progress:
                self.logger.warning("⚠️ ETH данные недоступны, используем нулевые значения")
            df["eth_returns"] = 0.0

        # ИСПРАВЛЕНО: Создаем признаки ТОЧНО КАК ПРИ ОБУЧЕНИИ МОДЕЛИ (из ааа.py)
        # 1. Основная BTC корреляция (как при обучении - window=96)
        for symbol in df["symbol"].unique():
            if symbol == "BTCUSDT":
                df.loc[df["symbol"] == symbol, "btc_correlation"] = 1.0
            else:
                mask = df["symbol"] == symbol
                symbol_returns = df.loc[mask, "returns"].astype(float)
                btc_returns = df.loc[mask, "btc_returns"].astype(float)

                # Используем ТОЧНО такие же параметры как при обучении
                rolling_corr = symbol_returns.rolling(
                    window=96, min_periods=50  # КАК В ОРИГИНАЛЕ  # КАК В ОРИГИНАЛЕ
                ).corr(btc_returns)

                df.loc[mask, "btc_correlation"] = rolling_corr

        # Для совместимости с REQUIRED_FEATURES_240 дублируем в новые названия
        df["btc_correlation_15m"] = df["btc_correlation"]  # Основная корреляция
        df["btc_correlation_1h"] = df["btc_correlation"]  # Дублируем
        df["btc_correlation_4h"] = df["btc_correlation"]  # Дублируем

        if not self.disable_progress:
            self.logger.info("  ✓ BTC корреляция: создана как при обучении (window=96)")

        # 2. ETH корреляции - В ОРИГИНАЛЕ НЕ БЫЛО, создаем заглушки
        # Так как модель не обучалась с ETH корреляциями, используем 0.5 (нейтральное значение)
        df["eth_correlation_15m"] = 0.5
        df["eth_correlation_1h"] = 0.5
        df["eth_correlation_4h"] = 0.5

        if not self.disable_progress:
            self.logger.info("ETH correlations: stubs created (not in original training)")

        # 3. BTC Beta - КАК В ОРИГИНАЛЕ (из ааа.py строка 1366)
        # Beta к BTC как в оригинале: rolling(100)
        for symbol in df["symbol"].unique():
            mask = df["symbol"] == symbol
            symbol_returns = df.loc[mask, "returns"].astype(float)
            btc_returns = df.loc[mask, "btc_returns"].astype(float)

            # КАК В ОРИГИНАЛЕ: Beta = Cov / Var с window=100
            covariance = symbol_returns.rolling(100, min_periods=50).cov(btc_returns)
            btc_variance = btc_returns.rolling(100, min_periods=50).var()

            # Beta = Cov / Var
            beta = self.safe_divide(covariance, btc_variance, fill_value=1.0)
            beta = beta.clip(-3, 3)  # Ограничиваем экстремальные значения beta

            df.loc[mask, "btc_beta"] = beta

        # Для совместимости с REQUIRED_FEATURES_240 дублируем в новые названия
        df["market_beta_1h"] = df["btc_beta"]  # Используем оригинальную beta
        df["market_beta_4h"] = df["btc_beta"]  # Дублируем

        if not self.disable_progress:
            self.logger.info("  ✓ Market beta: создано 2 признака")

        # Итоговая проверка
        cross_asset_features = [
            "btc_correlation_15m",
            "btc_correlation_1h",
            "btc_correlation_4h",
            "eth_correlation_15m",
            "eth_correlation_1h",
            "eth_correlation_4h",
            "market_beta_1h",
            "market_beta_4h",
        ]

        created_count = sum(1 for feat in cross_asset_features if feat in df.columns)
        missing_features = [feat for feat in cross_asset_features if feat not in df.columns]

        if not self.disable_progress:
            self.logger.info(f"✅ Cross-asset features: создано {created_count}/8 признаков")
        if missing_features:
            self.logger.warning(f"🚫 ОТСУТСТВУЮТ: {missing_features}")
        # Cross-asset features успешно созданы
        if not self.disable_progress:
            self.logger.info(f"✅ Cross-asset features: создано {created_count}/8 признаков")

        # Заполняем NaN значения
        for feat in cross_asset_features:
            if feat in df.columns:
                # Для корреляций используем нейтральное значение 0.5
                if "correlation" in feat:
                    fill_value = 0.5
                # Для beta используем рыночную нейтральность 1.0
                elif "beta" in feat:
                    fill_value = 1.0
                else:
                    fill_value = 0.0

                df[feat] = df[feat].fillna(fill_value)

        return df

    def _load_btc_eth_data_for_inference(
        self, df: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Загружает BTC и ETH данные из БД для inference режима (синхронно)"""
        try:
            import os
            from datetime import UTC, datetime, timedelta

            from sqlalchemy import create_engine, text

            # Определяем временной диапазон из исходного DataFrame
            if "datetime" in df.columns:
                start_time = df["datetime"].min() - timedelta(hours=1)
                end_time = df["datetime"].max() + timedelta(hours=1)
            else:
                # Fallback - берем последние 200 свечей
                end_time = datetime.now(UTC)
                start_time = end_time - timedelta(days=2)

            if not self.disable_progress:
                self.logger.info(f"🔄 Загружаем BTC/ETH данные за период {start_time} - {end_time}")

            # ИСПРАВЛЕНО: Используем синхронное подключение к БД
            db_url = f"postgresql://{os.getenv('PGUSER', 'obertruper')}:{os.getenv('PGPASSWORD', '')}@{os.getenv('PGHOST', 'localhost')}:{os.getenv('PGPORT', '5555')}/{os.getenv('PGDATABASE', 'bot_trading_v3')}"
            engine = create_engine(db_url)

            # Загружаем BTC данные
            btc_query = text(
                """
                SELECT datetime, close 
                FROM raw_market_data 
                WHERE symbol = 'BTCUSDT' 
                AND datetime BETWEEN :start_time AND :end_time 
                ORDER BY datetime
            """
            )

            # Загружаем ETH данные
            eth_query = text(
                """
                SELECT datetime, close 
                FROM raw_market_data 
                WHERE symbol = 'ETHUSDT' 
                AND datetime BETWEEN :start_time AND :end_time 
                ORDER BY datetime
            """
            )

            with engine.connect() as connection:
                # Загружаем BTC данные
                btc_result = connection.execute(
                    btc_query, {"start_time": start_time, "end_time": end_time}
                ).fetchall()

                # Загружаем ETH данные
                eth_result = connection.execute(
                    eth_query, {"start_time": start_time, "end_time": end_time}
                ).fetchall()

            # Конвертируем в DataFrame
            btc_data = (
                pd.DataFrame(btc_result, columns=["datetime", "close"])
                if btc_result
                else pd.DataFrame()
            )
            eth_data = (
                pd.DataFrame(eth_result, columns=["datetime", "close"])
                if eth_result
                else pd.DataFrame()
            )

            if not self.disable_progress:
                self.logger.info(
                    f"✅ Загружено BTC данных: {len(btc_data)}, ETH данных: {len(eth_data)}"
                )

            return btc_data, eth_data

        except Exception as e:
            if not self.disable_progress:
                self.logger.error(f"Ошибка загрузки BTC/ETH данных: {e}")
                import traceback

                traceback.print_exc()
            # Возвращаем пустые DataFrame
            return pd.DataFrame(), pd.DataFrame()

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

        # Commission and costs
        commission_rate = 0.0006  # 0.06%
        slippage = 0.0005  # 0.05%

        # A. Базовые возвраты (4)
        for period_name, n_candles in return_periods.items():
            df[f"future_return_{period_name}"] = df.groupby("symbol")["close"].transform(
                lambda x: x.shift(-n_candles) / x - 1
            )

        # B. Направление движения (4)
        for period_name in return_periods:
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
                future_high = df.groupby("symbol")["high"].transform(lambda x: x.shift(-i))
                future_return = future_high / df["close"] - 1
                max_future_returns[f"return_{i}"] = future_return

            # Максимальный return за период
            max_return = max_future_returns.max(axis=1)
            df[f"long_will_reach_{level_name}"] = (max_return >= profit_threshold).astype(int)

        # D. Достижение уровней прибыли SHORT (4)
        for level_name, (profit_threshold, n_candles) in profit_levels.items():
            # Для SHORT: проверяем минимальную цену
            min_future_returns = pd.DataFrame()
            for i in range(1, n_candles + 1):
                future_low = df.groupby("symbol")["low"].transform(lambda x: x.shift(-i))
                future_return = df["close"] / future_low - 1  # Для SHORT инвертируем
                min_future_returns[f"return_{i}"] = future_return

            # Максимальный return для SHORT за период
            max_return = min_future_returns.max(axis=1)
            df[f"short_will_reach_{level_name}"] = (max_return >= profit_threshold).astype(int)

        # E. Риск-метрики (4)
        # Максимальная просадка за период (для LONG)
        for period_name, n_candles in [("1h", 4), ("4h", 16)]:
            min_prices = pd.DataFrame()
            for i in range(1, n_candles + 1):
                future_low = df.groupby("symbol")["low"].transform(lambda x: x.shift(-i))
                min_prices[f"low_{i}"] = future_low

            # Минимальная цена за период
            min_price = min_prices.min(axis=1)
            df[f"max_drawdown_{period_name}"] = (df["close"] / min_price - 1).fillna(0)

        # Максимальный рост за период (для SHORT)
        for period_name, n_candles in [("1h", 4), ("4h", 16)]:
            max_prices = pd.DataFrame()
            for i in range(1, n_candles + 1):
                future_high = df.groupby("symbol")["high"].transform(lambda x: x.shift(-i))
                max_prices[f"high_{i}"] = future_high

            # Максимальная цена за период
            max_price = max_prices.max(axis=1)
            df[f"max_rally_{period_name}"] = (max_price / df["close"] - 1).fillna(0)

        # ИСПРАВЛЕНО: Убираем торговые сигналы с утечками данных
        # best_action, risk_reward_ratio и optimal_hold_time будут генерироваться
        # в trading/signal_generator.py на основе предсказаний модели

        # ПЕРЕНЕСЕНО В ПРИЗНАКИ: signal_strength теперь feature, не target
        # Это основано на исторических данных, без утечек

        # УДАЛЕНО: risk_reward_ratio и optimal_hold_time содержали утечки данных
        # Эти переменные будут генерироваться в trading/signal_generator.py
        # на основе предсказаний модели, а не реальных будущих данных

        # УДАЛЕНО: best_action и все legacy переменные (best_direction, reached, hit)
        # В версии 4.0 используем только 20 целевых переменных без утечек данных
        # Все необходимые целевые переменные уже созданы выше

        # Фиктивные временные переменные для совместимости
        df["long_tp1_time"] = 16  # 4 часа
        df["long_tp2_time"] = 16
        df["long_tp3_time"] = 48  # 12 часов
        df["long_sl_time"] = 100
        df["short_tp1_time"] = 16
        df["short_tp2_time"] = 16
        df["short_tp3_time"] = 48
        df["short_sl_time"] = 100

        # Expected value для совместимости
        df["long_expected_value"] = df["future_return_4h"] * df["long_will_reach_2pct_4h"] * 2.0
        df["short_expected_value"] = -df["future_return_4h"] * df["short_will_reach_2pct_4h"] * 2.0

        # Optimal entry фиктивные переменные
        df["long_optimal_entry_time"] = 1
        df["long_optimal_entry_price"] = df["close"]
        df["long_optimal_entry_improvement"] = 0
        df["short_optimal_entry_time"] = 1
        df["short_optimal_entry_price"] = df["close"]
        df["short_optimal_entry_improvement"] = 0

        # Итоговая статистика
        if not self.disable_progress:
            self.logger.info("  ✅ Создано 20 целевых переменных без утечек данных")
            self.logger.info("  📊 Распределение направлений:")
            for period in ["15m", "1h", "4h", "12h"]:
                if f"direction_{period}" in df.columns:
                    dist = df[f"direction_{period}"].value_counts(normalize=True) * 100
                    self.logger.info(
                        f"     {period}: UP={dist.get('UP', 0):.1f}%, DOWN={dist.get('DOWN', 0):.1f}%, FLAT={dist.get('FLAT', 0):.1f}%"
                    )

        return df

    def _normalize_walk_forward(self, df: pd.DataFrame, train_end_date: str) -> pd.DataFrame:
        """Walk-forward нормализация с использованием RobustScaler"""
        if not self.disable_progress:
            self.logger.info(f"📊 Walk-forward нормализация с границей: {train_end_date}")

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
            if col.startswith(("future_", "direction_", "long_will_reach_", "short_will_reach_"))
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
                    df.loc[train_symbol_mask, feature_cols] = self.scalers[symbol].transform(
                        train_to_scale
                    )

                # Применяем к test данным
                if test_symbol_mask.sum() > 0:
                    test_to_scale = df.loc[test_symbol_mask, feature_cols].fillna(0)
                    df.loc[test_symbol_mask, feature_cols] = self.scalers[symbol].transform(
                        test_to_scale
                    )

        if not self.disable_progress:
            self.logger.info("✅ Walk-forward нормализация завершена")

        return df

    def _log_feature_statistics(self, df: pd.DataFrame):
        """Логирование статистики по признакам"""
        if not self.disable_progress:
            feature_counts = {
                "basic": len(
                    [
                        col
                        for col in df.columns
                        if col in ["returns", "high_low_ratio", "close_open_ratio", "volume_ratio"]
                    ]
                ),
                "technical": len(
                    [
                        col
                        for col in df.columns
                        if any(ind in col for ind in ["sma", "ema", "rsi", "macd", "bb", "atr"])
                    ]
                ),
                "microstructure": len(
                    [
                        col
                        for col in df.columns
                        if any(
                            ms in col for ms in ["spread", "imbalance", "toxicity", "illiquidity"]
                        )
                    ]
                ),
                "temporal": len(
                    [
                        col
                        for col in df.columns
                        if any(t in col for t in ["hour", "day", "month", "session"])
                    ]
                ),
                "cross_asset": len(
                    [
                        col
                        for col in df.columns
                        if any(ca in col for ca in ["btc_", "sector", "rank", "momentum"])
                    ]
                ),
            }

            self.logger.info(f"📊 Создано признаков по категориям: {feature_counts}")

            # Проверка пропущенных значений
            missing_counts = df.isnull().sum()
            if missing_counts.sum() > 0:
                self.logger.warning(
                    f"⚠️ Обнаружены пропущенные значения в {missing_counts[missing_counts > 0].shape[0]} признаках"
                )

    def get_feature_names(self, include_targets: bool = False) -> list[str]:
        """Получение списка названий признаков"""
        # TODO: Реализовать правильное хранение названий признаков
        return []

    def save_scalers(self, path: str):
        """Сохранение скейлеров для использования в продакшене"""
        import pickle

        with open(path, "wb") as f:
            pickle.dump(self.scalers, f)

        if not self.disable_progress:
            self.logger.info(f"Скейлеры сохранены в {path}")

    def load_scalers(self, path: str):
        """Загрузка сохраненных скейлеров"""
        import pickle

        with open(path, "rb") as f:
            self.scalers = pickle.load(f)

        if not self.disable_progress:
            self.logger.info(f"Скейлеры загружены из {path}")

    def _add_enhanced_features(
        self, df: pd.DataFrame, all_symbols_data: dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """Добавление расширенных признаков для улучшения direction prediction

        Args:
            df: DataFrame с базовыми признаками
            all_symbols_data: словарь с данными всех символов для cross-asset features

        Returns:
            DataFrame с enhanced features
        """
        try:
            from data.enhanced_features import EnhancedFeatureEngineer
        except ImportError:
            self.logger.warning(
                "⚠️ Модуль enhanced_features не найден, пропускаем enhanced features"
            )
            return df

        self.logger.info("🚀 Добавление enhanced features для direction prediction...")

        enhanced_engineer = EnhancedFeatureEngineer()
        enhanced_dfs = []

        # Обрабатываем каждый символ
        for symbol in tqdm(
            df["symbol"].unique(), desc="Enhanced features", disable=self.disable_progress
        ):
            symbol_data = df[df["symbol"] == symbol].copy()

            # Применяем enhanced features
            enhanced_data = enhanced_engineer.create_enhanced_features(
                symbol_data, all_symbols_data if len(all_symbols_data) > 1 else None
            )

            enhanced_dfs.append(enhanced_data)

        # Объединяем результаты
        result_df = pd.concat(enhanced_dfs, ignore_index=True)

        # Логируем статистику новых признаков
        original_cols = set(df.columns)
        new_cols = set(result_df.columns) - original_cols

        if new_cols:
            self.logger.info(f"✅ Добавлено {len(new_cols)} enhanced features")

            # Категоризация новых признаков
            categories = {
                "market_regime": [col for col in new_cols if "regime" in col or "wyckoff" in col],
                "microstructure": [
                    col for col in new_cols if any(x in col for x in ["ofi", "tick", "imbalance"])
                ],
                "cross_asset": [
                    col for col in new_cols if any(x in col for x in ["btc_", "sector_", "beta_"])
                ],
                "sentiment": [
                    col
                    for col in new_cols
                    if any(x in col for x in ["fear_greed", "panic", "euphoria"])
                ],
            }

            for category, cols in categories.items():
                if cols:
                    self.logger.info(f"  - {category}: {len(cols)} признаков")

        return result_df
