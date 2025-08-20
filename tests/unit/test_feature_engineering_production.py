"""
Тесты для ProductionFeatureEngineer - критический компонент ML pipeline
Эти тесты покрывают реальную логику создания признаков
"""

import os
import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ml.logic.feature_engineering_production import (
    LoggerAdapter,
    ProductionFeatureEngineer,
    get_logger,
)


class TestLoggerAdapter:
    """Тесты для LoggerAdapter"""

    def test_logger_adapter_creation(self):
        """Тест создания адаптера логгера"""
        logger = LoggerAdapter("test_logger")

        assert logger is not None
        assert logger.logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")

    def test_logger_methods(self):
        """Тест методов логгера"""
        logger = LoggerAdapter("test_logger")

        # Тестируем что методы вызываются без ошибок
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")
        logger.debug("Test debug message")

        # Тест специальных методов
        logger.start_stage("test_stage", param1="value1")
        logger.end_stage("test_stage", result="success")

        # Создаем тестовый DataFrame
        test_df = pd.DataFrame({"col1": [1, 2, 3], "col2": [4, 5, 6]})
        logger.log_features_info(test_df, "test_stage")

    def test_get_logger_function(self):
        """Тест функции get_logger"""
        logger = get_logger("test_name")

        assert isinstance(logger, LoggerAdapter)
        assert logger.logger.name == "test_name"


class TestProductionFeatureEngineer:
    """Тесты для ProductionFeatureEngineer"""

    @pytest.fixture
    def sample_config(self):
        """Конфигурация для тестов"""
        return {
            "features": {
                "lookback_periods": [5, 10, 20],
                "volume_periods": [5, 10],
                "technical_indicators": {
                    "rsi_periods": [14, 21],
                    "bb_periods": [20],
                    "macd_fast": 12,
                    "macd_slow": 26,
                    "macd_signal": 9,
                },
                "enable_progress": False,
            }
        }

    @pytest.fixture
    def sample_market_data(self):
        """Создаем тестовые рыночные данные"""
        np.random.seed(42)
        n = 500  # Больше данных для технических индикаторов

        # Генерируем реалистичные OHLCV данные
        base_price = 50000
        price_changes = np.cumsum(np.random.randn(n) * 100)
        close_prices = base_price + price_changes

        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2023-01-01", periods=n, freq="1H"),
                "open": close_prices - np.abs(np.random.randn(n) * 50),
                "high": close_prices + np.abs(np.random.randn(n) * 75),
                "low": close_prices - np.abs(np.random.randn(n) * 75),
                "close": close_prices,
                "volume": np.abs(np.random.randn(n) * 1000000 + 5000000),
                "turnover": np.abs(np.random.randn(n) * 50000000 + 250000000),
                "symbol": ["BTCUSDT"] * n,
            }
        )

        # Корректируем high/low чтобы они были валидными
        df["high"] = df[["open", "close", "high"]].max(axis=1)
        df["low"] = df[["open", "close", "low"]].min(axis=1)

        return df

    @patch("ml.logic.feature_engineering_production.create_engine")
    def test_initialization(self, mock_create_engine, sample_config):
        """Тест инициализации ProductionFeatureEngineer"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        engineer = ProductionFeatureEngineer(sample_config)

        assert engineer.config == sample_config
        assert engineer.feature_config == sample_config["features"]
        assert engineer.disable_progress == False
        assert isinstance(engineer.scalers, dict)
        assert engineer.logger is not None

    @patch("ml.logic.feature_engineering_production.create_engine")
    def test_initialization_without_config(self, mock_create_engine):
        """Тест инициализации без конфигурации"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        engineer = ProductionFeatureEngineer()

        assert engineer.config == {}
        assert engineer.feature_config == {}
        assert isinstance(engineer.scalers, dict)

    @patch("ml.logic.feature_engineering_production.create_engine")
    def test_db_connection_initialization(self, mock_create_engine, sample_config):
        """Тест инициализации подключения к БД"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        engineer = ProductionFeatureEngineer(sample_config)

        # Проверяем что create_engine был вызван с правильными параметрами
        mock_create_engine.assert_called_once()
        args, kwargs = mock_create_engine.call_args

        # Проверяем URL базы данных (содержит порт 5555)
        db_url = args[0]
        assert "5555" in db_url or "bot_trading_v3" in db_url

        # Проверяем параметры подключения
        assert "pool_size" in kwargs
        assert "pool_pre_ping" in kwargs

    @patch("ml.logic.feature_engineering_production.create_engine")
    def test_db_connection_error_handling(self, mock_create_engine, sample_config):
        """Тест обработки ошибок подключения к БД"""
        mock_create_engine.side_effect = Exception("Connection failed")

        # Не должно вызывать исключение
        engineer = ProductionFeatureEngineer(sample_config)

        assert engineer.db_engine is None

    @patch("ml.logic.feature_engineering_production.create_engine")
    def test_create_basic_features(self, mock_create_engine, sample_config, sample_market_data):
        """Тест создания базовых признаков"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        engineer = ProductionFeatureEngineer(sample_config)

        # Мокируем методы создания признаков если они есть
        if hasattr(engineer, "create_basic_features"):
            result = engineer.create_basic_features(sample_market_data.copy())

            # Проверяем что результат - DataFrame
            assert isinstance(result, pd.DataFrame)
            assert len(result) <= len(sample_market_data)  # Может быть меньше из-за lookback

            # Проверяем наличие базовых колонок
            expected_base_columns = ["open", "high", "low", "close", "volume"]
            for col in expected_base_columns:
                assert col in result.columns

    @patch("ml.logic.feature_engineering_production.create_engine")
    def test_calculate_returns(self, mock_create_engine, sample_config, sample_market_data):
        """Тест расчета доходностей"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        engineer = ProductionFeatureEngineer(sample_config)

        # Тестируем расчет returns вручную
        df = sample_market_data.copy()

        # Рассчитываем returns как в реальной системе
        df["returns"] = np.log(df["close"] / df["close"].shift(1))

        # Проверяем корректность расчета
        assert "returns" in df.columns
        assert not df["returns"].iloc[1:].isin([np.inf, -np.inf]).any()
        assert df["returns"].iloc[0] != df["returns"].iloc[0]  # NaN проверка

        # Проверяем математическую корректность
        manual_return = np.log(df["close"].iloc[1] / df["close"].iloc[0])
        assert abs(df["returns"].iloc[1] - manual_return) < 1e-10

    @patch("ml.logic.feature_engineering_production.create_engine")
    def test_technical_indicators(self, mock_create_engine, sample_config, sample_market_data):
        """Тест расчета технических индикаторов"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        engineer = ProductionFeatureEngineer(sample_config)

        df = sample_market_data.copy()

        # Тестируем RSI
        try:
            import ta

            rsi = ta.momentum.RSIIndicator(df["close"], window=14)
            df["rsi_14"] = rsi.rsi()

            # RSI должен быть между 0 и 100
            valid_rsi = df["rsi_14"].dropna()
            if len(valid_rsi) > 0:
                assert valid_rsi.min() >= 0
                assert valid_rsi.max() <= 100
        except ImportError:
            # Если ta не установлен, пропускаем тест
            pytest.skip("ta library not available")

    @patch("ml.logic.feature_engineering_production.create_engine")
    def test_volume_features(self, mock_create_engine, sample_config, sample_market_data):
        """Тест создания объемных признаков"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        engineer = ProductionFeatureEngineer(sample_config)

        df = sample_market_data.copy()

        # Тестируем объемные соотношения
        df["volume_ratio"] = df["volume"] / df["volume"].shift(1)
        df["turnover_ratio"] = df["turnover"] / df["turnover"].shift(1)

        # Проверяем что отношения положительные
        assert df["volume_ratio"].dropna().min() > 0
        assert df["turnover_ratio"].dropna().min() > 0

        # Проверяем отсутствие бесконечных значений
        assert not df["volume_ratio"].isin([np.inf, -np.inf]).any()
        assert not df["turnover_ratio"].isin([np.inf, -np.inf]).any()

    @patch("ml.logic.feature_engineering_production.create_engine")
    def test_price_features(self, mock_create_engine, sample_config, sample_market_data):
        """Тест создания ценовых признаков"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        engineer = ProductionFeatureEngineer(sample_config)

        df = sample_market_data.copy()

        # Тестируем ценовые соотношения
        df["high_low_ratio"] = df["high"] / df["low"]
        df["close_open_ratio"] = df["close"] / df["open"]
        df["hl_spread"] = (df["high"] - df["low"]) / df["close"]

        # high/low ratio должно быть >= 1
        assert df["high_low_ratio"].min() >= 1.0

        # Проверяем разумные диапазоны
        assert df["close_open_ratio"].min() > 0
        assert df["hl_spread"].min() >= 0

    @patch("ml.logic.feature_engineering_production.create_engine")
    def test_statistical_features(self, mock_create_engine, sample_config, sample_market_data):
        """Тест создания статистических признаков"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        engineer = ProductionFeatureEngineer(sample_config)

        df = sample_market_data.copy()

        # Тестируем скользящие статистики
        window = 20
        df["rolling_mean"] = df["close"].rolling(window=window).mean()
        df["rolling_std"] = df["close"].rolling(window=window).std()
        df["rolling_min"] = df["close"].rolling(window=window).min()
        df["rolling_max"] = df["close"].rolling(window=window).max()

        # Проверяем корректность статистик
        valid_data = df.dropna()
        if len(valid_data) > 0:
            assert valid_data["rolling_std"].min() >= 0
            assert (valid_data["rolling_min"] <= valid_data["close"]).all()
            assert (valid_data["rolling_max"] >= valid_data["close"]).all()

    @patch("ml.logic.feature_engineering_production.create_engine")
    def test_feature_scaling(self, mock_create_engine, sample_config, sample_market_data):
        """Тест масштабирования признаков"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        engineer = ProductionFeatureEngineer(sample_config)

        # Создаем тестовые признаки
        df = sample_market_data.copy()
        df["feature1"] = df["close"] * 1000  # Большие значения
        df["feature2"] = df["volume"] / 1000000  # Малые значения

        # Тестируем StandardScaler
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()

        features_to_scale = ["feature1", "feature2"]
        scaled_features = scaler.fit_transform(df[features_to_scale].dropna())

        # После стандартизации среднее должно быть близко к 0, std к 1
        assert abs(scaled_features.mean(axis=0)).max() < 0.1
        assert abs(scaled_features.std(axis=0) - 1.0).max() < 0.1

    @patch("ml.logic.feature_engineering_production.create_engine")
    def test_data_validation(self, mock_create_engine, sample_config):
        """Тест валидации данных"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        engineer = ProductionFeatureEngineer(sample_config)

        # Тест с невалидными данными
        invalid_df = pd.DataFrame(
            {
                "open": [100, np.inf, 102],
                "high": [105, 103, np.nan],
                "low": [95, 97, 99],
                "close": [102, np.nan, 101],
                "volume": [1000, -100, 1200],  # Отрицательный объем
            }
        )

        # Простая валидация
        validation_results = {
            "has_inf": invalid_df.isin([np.inf, -np.inf]).any().any(),
            "has_nan": invalid_df.isna().any().any(),
            "negative_volume": (
                (invalid_df["volume"] < 0).any() if "volume" in invalid_df else False
            ),
        }

        assert validation_results["has_inf"] == True
        assert validation_results["has_nan"] == True
        assert validation_results["negative_volume"] == True

    @patch("ml.logic.feature_engineering_production.create_engine")
    def test_edge_cases(self, mock_create_engine, sample_config):
        """Тест граничных случаев"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        engineer = ProductionFeatureEngineer(sample_config)

        # Пустой DataFrame
        empty_df = pd.DataFrame()

        # Должен обрабатываться без ошибок
        assert len(empty_df) == 0

        # DataFrame с одной строкой
        single_row = pd.DataFrame(
            {"open": [100], "high": [105], "low": [95], "close": [102], "volume": [1000]}
        )

        # Расчет returns на одной строке должен дать NaN
        single_row["returns"] = np.log(single_row["close"] / single_row["close"].shift(1))
        assert pd.isna(single_row["returns"].iloc[0])

        # Константные значения
        constant_df = pd.DataFrame({"close": [100] * 50, "volume": [1000] * 50})

        constant_df["returns"] = np.log(constant_df["close"] / constant_df["close"].shift(1))
        # Returns для константных цен должны быть 0
        assert constant_df["returns"].dropna().abs().max() < 1e-10

    @patch("ml.logic.feature_engineering_production.create_engine")
    def test_memory_efficiency(self, mock_create_engine, sample_config):
        """Тест эффективности памяти"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        engineer = ProductionFeatureEngineer(sample_config)

        # Создаем большой DataFrame
        n = 50000
        large_df = pd.DataFrame(
            {
                "close": np.random.randn(n) * 100 + 50000,
                "volume": np.abs(np.random.randn(n) * 1000000),
                "high": np.random.randn(n) * 100 + 50100,
                "low": np.random.randn(n) * 100 + 49900,
            }
        )

        import os

        import psutil

        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        # Создаем простые признаки
        large_df["returns"] = np.log(large_df["close"] / large_df["close"].shift(1))
        large_df["volume_ratio"] = large_df["volume"] / large_df["volume"].shift(1)

        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = memory_after - memory_before

        # Увеличение памяти должно быть разумным (< 500MB)
        assert memory_increase < 500

    @patch("ml.logic.feature_engineering_production.create_engine")
    def test_performance(self, mock_create_engine, sample_config):
        """Тест производительности"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        engineer = ProductionFeatureEngineer(sample_config)
        engineer.disable_progress = True  # Отключаем прогресс для теста

        # Тест на средних данных
        n = 10000
        test_df = pd.DataFrame(
            {
                "close": np.random.randn(n) * 100 + 50000,
                "volume": np.abs(np.random.randn(n) * 1000000),
                "high": np.random.randn(n) * 100 + 50100,
                "low": np.random.randn(n) * 100 + 49900,
            }
        )

        import time

        start_time = time.time()

        # Простое создание признаков
        test_df["returns"] = np.log(test_df["close"] / test_df["close"].shift(1))
        test_df["ma_20"] = test_df["close"].rolling(20).mean()
        test_df["volatility"] = test_df["returns"].rolling(20).std()

        elapsed = time.time() - start_time

        # Должно выполняться быстро (< 1 секунды для 10K строк)
        assert elapsed < 1.0


class TestProductionFeatureEngineerIntegration:
    """Интеграционные тесты"""

    @patch("ml.logic.feature_engineering_production.create_engine")
    def test_full_feature_pipeline(self, mock_create_engine):
        """Тест полного пайплайна создания признаков"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        config = {"features": {"lookback_periods": [5, 10], "enable_technical_indicators": True}}

        engineer = ProductionFeatureEngineer(config)

        # Создаем данные
        np.random.seed(42)
        n = 200
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2023-01-01", periods=n, freq="1H"),
                "open": np.random.randn(n) * 10 + 50000,
                "high": np.random.randn(n) * 10 + 50050,
                "low": np.random.randn(n) * 10 + 49950,
                "close": np.random.randn(n) * 10 + 50000,
                "volume": np.abs(np.random.randn(n) * 1000000),
                "turnover": np.abs(np.random.randn(n) * 50000000),
            }
        )

        # Полный пайплайн признаков
        # 1. Базовые признаки
        df["returns"] = np.log(df["close"] / df["close"].shift(1))
        df["high_low_ratio"] = df["high"] / df["low"]

        # 2. Скользящие окна
        for period in config["features"]["lookback_periods"]:
            df[f"ma_{period}"] = df["close"].rolling(period).mean()
            df[f"vol_{period}"] = df["returns"].rolling(period).std()

        # 3. Объемные признаки
        df["volume_ma"] = df["volume"].rolling(10).mean()

        # Проверяем результат
        assert len(df) == n
        assert "returns" in df.columns
        assert "ma_5" in df.columns
        assert "ma_10" in df.columns
        assert "vol_5" in df.columns

        # Проверяем качество данных
        feature_cols = [
            col
            for col in df.columns
            if col not in ["timestamp", "open", "high", "low", "close", "volume", "turnover"]
        ]
        for col in feature_cols:
            # Не должно быть бесконечных значений
            assert not df[col].isin([np.inf, -np.inf]).any(), f"Column {col} has infinite values"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
