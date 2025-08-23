"""
Интеграция FeatureEngineer с существующими индикаторами проекта
"""

import logging
from typing import Any, Optional

import numpy as np
import pandas as pd

from ml.logic.feature_engineering_production import ProductionFeatureEngineer as FeatureEngineer

# Отложенный импорт для избежания циклических зависимостей
try:
    from strategies.indicator_strategy.indicators.base import (
        IndicatorBase,
        IndicatorConfig,
        IndicatorResult,
    )
    from strategies.indicator_strategy.indicators.manager import IndicatorManager

    INDICATORS_AVAILABLE = True
except ImportError:
    INDICATORS_AVAILABLE = False
    IndicatorBase = None
    IndicatorConfig = None
    IndicatorResult = None
    IndicatorManager = None

logger = logging.getLogger(__name__)


class FeatureEngineerWithIndicators(FeatureEngineer):
    """
    Расширенный FeatureEngineer с интеграцией существующих индикаторов проекта
    """

    def __init__(self, config=None, indicator_manager: Optional["IndicatorManager"] = None):
        """
        Инициализация с поддержкой indicator manager

        Args:
            config: Конфигурация признаков
            indicator_manager: Менеджер индикаторов проекта
        """
        super().__init__(config)
        self.indicator_manager = indicator_manager
        self._indicator_features = []

    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Создание признаков с использованием существующих индикаторов

        Args:
            df: DataFrame с OHLCV данными

        Returns:
            DataFrame с добавленными признаками
        """
        # Сначала создаем базовые признаки
        result_df = super().create_features(df)

        # Добавляем признаки из indicator manager если доступен
        if self.indicator_manager:
            result_df = self._add_indicator_manager_features(result_df)

        return result_df

    def _add_indicator_manager_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Добавление признаков из indicator manager

        Args:
            df: DataFrame с данными

        Returns:
            DataFrame с добавленными признаками от индикаторов
        """
        logger.info("Добавление признаков из indicator manager")

        # Получаем список активных индикаторов
        active_indicators = self.indicator_manager.get_active_indicators()

        for indicator_name, indicator in active_indicators.items():
            try:
                # Для каждого символа рассчитываем индикатор
                if "symbol" in df.columns:
                    for symbol in df["symbol"].unique():
                        symbol_data = df[df["symbol"] == symbol].copy()
                        self._calculate_indicator_features(symbol_data, indicator, indicator_name)
                        df.loc[df["symbol"] == symbol, symbol_data.columns] = symbol_data
                else:
                    self._calculate_indicator_features(df, indicator, indicator_name)

            except Exception as e:
                logger.error(f"Ошибка при расчете индикатора {indicator_name}: {e}")

        return df

    def _calculate_indicator_features(
        self, df: pd.DataFrame, indicator: IndicatorBase, indicator_name: str
    ) -> pd.DataFrame:
        """
        Расчет признаков для одного индикатора

        Args:
            df: DataFrame с данными
            indicator: Экземпляр индикатора
            indicator_name: Название индикатора
        """
        # Проверяем валидность данных для индикатора
        if not indicator.is_data_valid(df):
            logger.warning(f"Недостаточно данных для индикатора {indicator_name}")
            return df

        # Рассчитываем индикатор для каждой строки
        signals = []
        strengths = []
        values = []

        min_periods = indicator.get_min_periods()

        for i in range(len(df)):
            if i < min_periods - 1:
                signals.append(0)
                strengths.append(0)
                values.append(np.nan)
            else:
                # Берем данные до текущего момента
                data_slice = df.iloc[: i + 1]
                result = indicator.safe_calculate(data_slice)

                if result:
                    signals.append(result.signal)
                    strengths.append(result.strength)

                    # Обрабатываем разные типы значений
                    if isinstance(result.value, dict):
                        values.append(result.value.get("main", np.nan))
                    else:
                        values.append(result.value)
                else:
                    signals.append(0)
                    strengths.append(0)
                    values.append(np.nan)

        # Добавляем признаки в DataFrame
        feature_prefix = f"ind_{indicator_name.lower()}"
        df[f"{feature_prefix}_signal"] = signals
        df[f"{feature_prefix}_strength"] = strengths
        df[f"{feature_prefix}_value"] = values

        # Добавляем в список признаков от индикаторов
        self._indicator_features.extend(
            [
                f"{feature_prefix}_signal",
                f"{feature_prefix}_strength",
                f"{feature_prefix}_value",
            ]
        )

        # Дополнительные признаки на основе индикатора
        if f"{feature_prefix}_signal" in df.columns:
            # Изменение сигнала
            df[f"{feature_prefix}_signal_change"] = df[f"{feature_prefix}_signal"].diff()

            # Консистентность сигнала
            df[f"{feature_prefix}_signal_consistency"] = (
                df[f"{feature_prefix}_signal"].rolling(5).mean()
            )

            # Сила тренда на основе силы сигнала
            df[f"{feature_prefix}_trend_strength"] = (
                df[f"{feature_prefix}_strength"].rolling(10).mean()
            )

            self._indicator_features.extend(
                [
                    f"{feature_prefix}_signal_change",
                    f"{feature_prefix}_signal_consistency",
                    f"{feature_prefix}_trend_strength",
                ]
            )

        return df

    def create_ensemble_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Создание ансамблевых признаков на основе множества индикаторов

        Args:
            df: DataFrame с признаками индикаторов

        Returns:
            DataFrame с ансамблевыми признаками
        """
        # Собираем все сигналы индикаторов
        signal_cols = [
            col for col in df.columns if col.endswith("_signal") and col.startswith("ind_")
        ]
        strength_cols = [
            col for col in df.columns if col.endswith("_strength") and col.startswith("ind_")
        ]

        if signal_cols:
            # Консенсус сигналов
            df["ensemble_signal_sum"] = df[signal_cols].sum(axis=1)
            df["ensemble_signal_mean"] = df[signal_cols].mean(axis=1)

            # Количество бычьих/медвежьих сигналов
            df["ensemble_bullish_count"] = (df[signal_cols] == 1).sum(axis=1)
            df["ensemble_bearish_count"] = (df[signal_cols] == -1).sum(axis=1)
            df["ensemble_neutral_count"] = (df[signal_cols] == 0).sum(axis=1)

            # Доминирующее направление
            df["ensemble_dominant_direction"] = np.sign(df["ensemble_signal_sum"])

        if strength_cols:
            # Средняя сила сигналов
            df["ensemble_strength_mean"] = df[strength_cols].mean(axis=1)
            df["ensemble_strength_max"] = df[strength_cols].max(axis=1)
            df["ensemble_strength_std"] = df[strength_cols].std(axis=1)

            # Взвешенный сигнал по силе
            if signal_cols and len(signal_cols) == len(strength_cols):
                weighted_sum = 0
                weight_sum = 0

                for sig_col, str_col in zip(signal_cols, strength_cols, strict=False):
                    weighted_sum += df[sig_col] * df[str_col]
                    weight_sum += df[str_col]

                df["ensemble_weighted_signal"] = weighted_sum / (weight_sum + 1e-8)

        return df

    def get_indicator_feature_names(self) -> list[str]:
        """Получить список признаков созданных из индикаторов"""
        return self._indicator_features

    def create_custom_indicator_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Создание дополнительных признаков на основе комбинаций индикаторов

        Args:
            df: DataFrame с базовыми признаками индикаторов

        Returns:
            DataFrame с дополнительными признаками
        """
        # Комбинации RSI и MACD
        if "rsi" in df.columns and "macd_diff" in df.columns:
            # RSI + MACD дивергенция
            df["rsi_macd_divergence"] = (
                ((df["rsi"] > 70) & (df["macd_diff"] < 0))
                | ((df["rsi"] < 30) & (df["macd_diff"] > 0))
            ).astype(int)

            # Согласованность сигналов
            df["rsi_macd_agreement"] = (
                ((df["rsi"] > 50) & (df["macd_diff"] > 0))
                | ((df["rsi"] < 50) & (df["macd_diff"] < 0))
            ).astype(int)

        # Комбинации Bollinger Bands и Volume
        if "bb_position" in df.columns and "volume_ratio_5" in df.columns:
            # Прорыв BB с высоким объемом
            df["bb_breakout_volume"] = (
                ((df["bb_position"] > 0.9) | (df["bb_position"] < 0.1))
                & (df["volume_ratio_5"] > 1.5)
            ).astype(int)

        # Комбинации ADX и тренда
        if "adx" in df.columns and "sma_20" in df.columns:
            # Сильный тренд
            df["strong_trend"] = (
                (df["adx"] > 25) & (abs(df["close"] - df["sma_20"]) / df["sma_20"] > 0.02)
            ).astype(int)

        # Моментум и волатильность
        if "momentum_1h" in df.columns and "atr_pct" in df.columns:
            # Высокий моментум с низкой волатильностью (хороший вход)
            df["momentum_volatility_ratio"] = self.safe_divide(
                df["momentum_1h"].abs(), df["atr_pct"] * 100, fill_value=0.0
            )

            df["good_entry_signal"] = (
                (df["momentum_volatility_ratio"] > 2)
                & (df["atr_pct"] < df["atr_pct"].rolling(20).mean())
            ).astype(int)

        return df


def create_feature_config_from_indicators(
    indicator_configs: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Создание конфигурации признаков на основе конфигураций индикаторов

    Args:
        indicator_configs: Список конфигураций индикаторов

    Returns:
        Словарь с параметрами для FeatureConfig
    """
    config_params = {
        "sma_periods": [],
        "ema_periods": [],
        "rsi_period": 14,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "bb_period": 20,
        "bb_std": 2.0,
        "atr_period": 14,
    }

    for ind_config in indicator_configs:
        if ind_config.get("type") == "sma":
            config_params["sma_periods"].append(ind_config.get("period", 20))
        elif ind_config.get("type") == "ema":
            config_params["ema_periods"].append(ind_config.get("period", 20))
        elif ind_config.get("type") == "rsi":
            config_params["rsi_period"] = ind_config.get("period", 14)
        elif ind_config.get("type") == "macd":
            config_params["macd_fast"] = ind_config.get("fast_period", 12)
            config_params["macd_slow"] = ind_config.get("slow_period", 26)
            config_params["macd_signal"] = ind_config.get("signal_period", 9)
        elif ind_config.get("type") == "bollinger_bands":
            config_params["bb_period"] = ind_config.get("period", 20)
            config_params["bb_std"] = ind_config.get("std_dev", 2.0)
        elif ind_config.get("type") == "atr":
            config_params["atr_period"] = ind_config.get("period", 14)

    # Удаляем дубликаты и сортируем
    config_params["sma_periods"] = sorted(list(set(config_params["sma_periods"]))) or [
        10,
        20,
        50,
    ]
    config_params["ema_periods"] = sorted(list(set(config_params["ema_periods"]))) or [
        10,
        20,
        50,
    ]

    return config_params
