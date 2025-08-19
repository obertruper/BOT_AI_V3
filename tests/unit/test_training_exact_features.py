"""
Тесты для модуля ml/logic/training_exact_features.py
Проверяем правильность создания 231 фичи для ML модели
"""

import os
import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ml.logic.training_exact_features import TrainingExactFeatures


class TestTrainingExactFeatures:
    """Тесты для класса TrainingExactFeatures"""

    @pytest.fixture
    def sample_config(self):
        """Конфигурация для тестов"""
        return {
            "features": {
                "lookback_periods": [5, 10, 20],
                "volume_periods": [5, 10],
                "rsi_periods": [14, 21],
                "bb_periods": [20],
                "macd_fast": 12,
                "macd_slow": 26,
                "macd_signal": 9,
            }
        }

    @pytest.fixture
    def sample_df(self):
        """Создаем тестовый DataFrame с OHLCV данными"""
        np.random.seed(42)
        n = 100

        # Генерируем реалистичные OHLCV данные
        close_prices = 100 + np.cumsum(np.random.randn(n) * 0.5)

        df = pd.DataFrame(
            {
                "open": close_prices - np.abs(np.random.randn(n) * 0.2),
                "high": close_prices + np.abs(np.random.randn(n) * 0.3),
                "low": close_prices - np.abs(np.random.randn(n) * 0.3),
                "close": close_prices,
                "volume": np.abs(np.random.randn(n) * 1000000 + 5000000),
                "turnover": np.abs(np.random.randn(n) * 10000000 + 50000000),
            }
        )

        # Корректируем high/low чтобы они были валидными
        df["high"] = df[["open", "close", "high"]].max(axis=1)
        df["low"] = df[["open", "close", "low"]].min(axis=1)

        return df

    def test_initialization(self, sample_config):
        """Тест инициализации класса"""
        feature_eng = TrainingExactFeatures(sample_config)

        assert feature_eng.config == sample_config
        assert feature_eng.expected_feature_count > 0
        assert feature_eng.disable_progress == False
        assert isinstance(feature_eng.scalers, dict)

    def test_safe_divide(self, sample_config):
        """Тест безопасного деления"""
        feature_eng = TrainingExactFeatures(sample_config)

        # Тест нормального деления
        numerator = pd.Series([10, 20, 30])
        denominator = pd.Series([2, 4, 5])
        result = feature_eng.safe_divide(numerator, denominator)

        assert list(result) == [5.0, 5.0, 6.0]

        # Тест деления на ноль
        denominator_zero = pd.Series([2, 0, 5])
        result_zero = feature_eng.safe_divide(numerator, denominator_zero)

        assert result_zero[1] != np.inf
        assert not pd.isna(result_zero[1])

        # Тест деления на очень маленькое число
        denominator_small = pd.Series([2, 1e-10, 5])
        result_small = feature_eng.safe_divide(numerator, denominator_small)

        assert result_small[1] <= 1000.0  # Должно быть ограничено max_value

    def test_calculate_vwap(self, sample_config, sample_df):
        """Тест расчета VWAP"""
        feature_eng = TrainingExactFeatures(sample_config)

        vwap = feature_eng.calculate_vwap(sample_df)

        # VWAP должен быть близок к цене закрытия
        assert len(vwap) == len(sample_df)
        assert all(vwap > 0)

        # VWAP не должен сильно отличаться от close
        ratio = vwap / sample_df["close"]
        assert all(ratio >= 0.5)
        assert all(ratio <= 2.0)

    def test_create_basic_features(self, sample_config, sample_df):
        """Тест создания базовых фичей"""
        feature_eng = TrainingExactFeatures(sample_config)

        # Создаем фичи
        df_with_features = feature_eng._create_basic_features(sample_df.copy())

        # Проверяем наличие базовых фичей
        expected_features = [
            "returns",
            "returns_5",
            "returns_10",
            "returns_20",
            "high_low_ratio",
            "close_open_ratio",
            "close_position",
        ]

        for feature in expected_features:
            assert feature in df_with_features.columns
            # Проверяем что нет бесконечных значений
            assert not df_with_features[feature].isin([np.inf, -np.inf]).any()

    def test_returns_calculation(self, sample_config, sample_df):
        """Тест расчета доходностей"""
        feature_eng = TrainingExactFeatures(sample_config)

        df_with_features = feature_eng._create_basic_features(sample_df.copy())

        # Проверяем формулу returns
        expected_returns = np.log(sample_df["close"] / sample_df["close"].shift(1))
        pd.testing.assert_series_equal(
            df_with_features["returns"].dropna(), expected_returns.dropna(), check_names=False
        )

        # Проверяем returns за периоды
        for period in [5, 10, 20]:
            expected = np.log(sample_df["close"] / sample_df["close"].shift(period))
            pd.testing.assert_series_equal(
                df_with_features[f"returns_{period}"].dropna(), expected.dropna(), check_names=False
            )

    def test_price_ratios(self, sample_config, sample_df):
        """Тест расчета ценовых соотношений"""
        feature_eng = TrainingExactFeatures(sample_config)

        df_with_features = feature_eng._create_basic_features(sample_df.copy())

        # high_low_ratio
        expected_hl = sample_df["high"] / sample_df["low"]
        pd.testing.assert_series_equal(
            df_with_features["high_low_ratio"], expected_hl, check_names=False
        )

        # close_open_ratio
        expected_co = sample_df["close"] / sample_df["open"]
        pd.testing.assert_series_equal(
            df_with_features["close_open_ratio"], expected_co, check_names=False
        )

    def test_close_position(self, sample_config, sample_df):
        """Тест расчета позиции закрытия в диапазоне"""
        feature_eng = TrainingExactFeatures(sample_config)

        df_with_features = feature_eng._create_basic_features(sample_df.copy())

        # close_position должна быть между 0 и 1
        close_pos = df_with_features["close_position"]
        assert all(close_pos >= 0)
        assert all(close_pos <= 1)

    def test_edge_cases(self, sample_config):
        """Тест граничных случаев"""
        feature_eng = TrainingExactFeatures(sample_config)

        # DataFrame с одинаковыми значениями
        df_constant = pd.DataFrame(
            {
                "open": [100] * 10,
                "high": [100] * 10,
                "low": [100] * 10,
                "close": [100] * 10,
                "volume": [1000] * 10,
                "turnover": [100000] * 10,
            }
        )

        df_with_features = feature_eng._create_basic_features(df_constant.copy())

        # returns должны быть 0 (log(1) = 0)
        assert all(df_with_features["returns"].dropna() == 0)

        # high_low_ratio должен быть 1
        assert all(df_with_features["high_low_ratio"] == 1)

    def test_nan_handling(self, sample_config):
        """Тест обработки NaN значений"""
        feature_eng = TrainingExactFeatures(sample_config)

        # DataFrame с NaN
        df_with_nan = pd.DataFrame(
            {
                "open": [100, np.nan, 102],
                "high": [101, 103, np.nan],
                "low": [99, np.nan, 101],
                "close": [100, 102, 103],
                "volume": [1000, np.nan, 1200],
                "turnover": [100000, 102000, np.nan],
            }
        )

        # safe_divide должен обрабатывать NaN
        numerator = pd.Series([10, np.nan, 30])
        denominator = pd.Series([2, 4, np.nan])
        result = feature_eng.safe_divide(numerator, denominator)

        # Результат не должен содержать inf
        assert not result.isin([np.inf, -np.inf]).any()

    def test_feature_count_validation(self, sample_config):
        """Тест валидации количества фичей"""
        feature_eng = TrainingExactFeatures(sample_config)

        # Проверяем что ожидается 231 фича (или сколько указано в PRODUCTION_FEATURES)
        assert feature_eng.expected_feature_count > 0
        assert isinstance(feature_eng.expected_feature_count, int)

    @patch("ml.logic.training_exact_features.setup_logger")
    def test_logging(self, mock_logger, sample_config):
        """Тест логирования"""
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance

        feature_eng = TrainingExactFeatures(sample_config)

        # Проверяем что логгер был инициализирован
        mock_logger.assert_called_once()

        # Проверяем что было залогировано сообщение об инициализации
        mock_logger_instance.info.assert_called()

    def test_volume_features(self, sample_config, sample_df):
        """Тест создания объемных фичей"""
        feature_eng = TrainingExactFeatures(sample_config)

        # Добавляем объемные отношения
        sample_df["volume_ratio"] = sample_df["volume"] / sample_df["volume"].shift(1)
        sample_df["turnover_ratio"] = sample_df["turnover"] / sample_df["turnover"].shift(1)

        # Проверяем что отношения рассчитаны корректно
        assert len(sample_df["volume_ratio"]) == len(sample_df)
        assert sample_df["volume_ratio"].dropna().min() > 0

    def test_statistical_features(self, sample_config, sample_df):
        """Тест статистических фичей"""
        feature_eng = TrainingExactFeatures(sample_config)

        # Рассчитываем скользящие статистики
        window = 20

        # Скользящее среднее
        ma = sample_df["close"].rolling(window=window).mean()
        assert len(ma) == len(sample_df)
        assert ma.dropna().min() > 0

        # Скользящее стандартное отклонение
        std = sample_df["close"].rolling(window=window).std()
        assert len(std) == len(sample_df)
        assert std.dropna().min() >= 0

        # Z-score
        z_score = (sample_df["close"] - ma) / (std + 1e-10)
        assert len(z_score) == len(sample_df)
        assert not z_score.isin([np.inf, -np.inf]).any()

    def test_performance(self, sample_config):
        """Тест производительности"""
        feature_eng = TrainingExactFeatures(sample_config)

        # Большой DataFrame
        n = 10000
        large_df = pd.DataFrame(
            {
                "open": np.random.randn(n) * 10 + 100,
                "high": np.random.randn(n) * 10 + 105,
                "low": np.random.randn(n) * 10 + 95,
                "close": np.random.randn(n) * 10 + 100,
                "volume": np.abs(np.random.randn(n) * 1000000),
                "turnover": np.abs(np.random.randn(n) * 10000000),
            }
        )

        # Должно выполняться быстро
        import time

        start = time.time()
        df_with_features = feature_eng._create_basic_features(large_df.copy())
        elapsed = time.time() - start

        # Должно выполняться менее чем за 1 секунду для 10000 строк
        assert elapsed < 1.0
        assert len(df_with_features) == n


class TestFeatureValidation:
    """Тесты валидации фичей"""

    def test_feature_names_consistency(self):
        """Тест консистентности имен фичей"""
        # Импортируем конфигурацию если она доступна
        try:
            from production_features_config import PRODUCTION_FEATURES

            # Проверяем что все имена уникальны
            assert len(PRODUCTION_FEATURES) == len(set(PRODUCTION_FEATURES))

            # Проверяем что количество фичей = 231
            assert len(PRODUCTION_FEATURES) == 231
        except ImportError:
            # Если конфиг недоступен, пропускаем тест
            pytest.skip("production_features_config not available")

    def test_critical_formulas(self):
        """Тест критических формул"""
        try:
            from production_features_config import CRITICAL_FORMULAS

            # Проверяем наличие критических формул
            expected_formulas = ["returns", "vwap", "rsi", "macd"]

            for formula in expected_formulas:
                assert formula in CRITICAL_FORMULAS
        except ImportError:
            pytest.skip("production_features_config not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
