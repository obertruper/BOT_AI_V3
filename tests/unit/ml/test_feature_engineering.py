"""
Тесты для модуля feature engineering
"""

import numpy as np
import pandas as pd
import pytest

from ml.logic.feature_engineering import FeatureEngineer


@pytest.mark.unit
@pytest.mark.ml
class TestFeatureEngineer:
    """Тесты для класса FeatureEngineer"""

    @pytest.fixture
    def sample_ohlcv_data(self):
        """Создает примерные OHLCV данные для тестов"""
        # Генерируем 100 свечей
        dates = pd.date_range(start="2024-01-01", periods=100, freq="15min")

        # Базовая цена с трендом
        base_price = 50000
        trend = np.linspace(0, 1000, 100)
        noise = np.random.normal(0, 100, 100)

        close_prices = base_price + trend + noise

        # Генерируем OHLCV
        data = {
            "datetime": dates,
            "open": close_prices + np.random.normal(0, 50, 100),
            "high": close_prices + np.abs(np.random.normal(100, 50, 100)),
            "low": close_prices - np.abs(np.random.normal(100, 50, 100)),
            "close": close_prices,
            "volume": np.random.uniform(1000, 10000, 100),
            "symbol": "BTCUSDT",
        }

        df = pd.DataFrame(data)

        # Корректируем OHLC чтобы были валидными
        df["high"] = df[["open", "close", "high"]].max(axis=1)
        df["low"] = df[["open", "close", "low"]].min(axis=1)

        # Добавляем turnover
        df["turnover"] = df["close"] * df["volume"]

        return df

    @pytest.fixture
    def feature_engineer(self):
        """Создает экземпляр FeatureEngineer"""
        config = {
            "features": {
                "technical": [
                    {"name": "sma", "periods": [10, 20]},
                    {"name": "ema", "periods": [10, 20]},
                    {"name": "rsi", "period": 14},
                    {"name": "macd", "fast": 12, "slow": 26, "signal": 9},
                    {"name": "bollinger", "period": 20, "std": 2},
                    {"name": "atr", "period": 14},
                    {"name": "stoch", "window": 14, "smooth_window": 3},
                    {"name": "adx", "period": 14},
                ],
                "volume": {
                    "ma_periods": [5, 10, 20],
                    "obv": True,
                    "mfi": True,
                    "cmf": True,
                },
                "statistical": {
                    "volatility_windows": [5, 10, 20],
                    "skew_window": 20,
                    "kurt_window": 20,
                    "zscore_window": 20,
                    "max_min_windows": [10, 20, 50],
                },
                "microstructure": {
                    "realized_vol_periods": ["1h", "4h", "12h"],
                    "amihud_window": 5,
                    "kyle_lambda_window": 20,
                },
                "temporal": {
                    "hour_encoding": "sincos",
                    "day_encoding": "sincos",
                    "sessions": ["asian", "europe", "us"],
                },
                "pattern": {
                    "volatility_squeeze_threshold": 0.5,
                    "volume_spike_multiplier": 2.0,
                    "momentum_window": "1h",
                },
            }
        }
        return FeatureEngineer(config)

    def test_initialization(self, feature_engineer):
        """Тест инициализации"""
        assert feature_engineer is not None
        assert feature_engineer.config is not None
        assert feature_engineer.feature_config is not None
        assert len(feature_engineer.scalers) == 0

    def test_safe_divide(self, feature_engineer):
        """Тест безопасного деления"""
        # Обычное деление
        numerator = pd.Series([10, 20, 30])
        denominator = pd.Series([2, 4, 5])
        result = feature_engineer.safe_divide(numerator, denominator)
        expected = pd.Series([5.0, 5.0, 6.0])
        pd.testing.assert_series_equal(result, expected)

        # Деление на ноль
        denominator_with_zero = pd.Series([2, 0, 5])
        result = feature_engineer.safe_divide(numerator, denominator_with_zero)
        # Функция ограничивает результат max_value (по умолчанию 1000.0)
        assert result[1] == 1000.0  # Ограничено max_value

        # Деление с inf
        numerator_inf = pd.Series([10, np.inf, 30])
        result = feature_engineer.safe_divide(numerator_inf, denominator)
        assert not np.isinf(result).any()

    def test_create_basic_features(self, feature_engineer, sample_ohlcv_data):
        """Тест создания базовых признаков"""
        df = feature_engineer._create_basic_features(sample_ohlcv_data.copy())

        # Проверяем наличие основных признаков
        assert "returns" in df.columns
        assert "high_low_ratio" in df.columns
        assert "close_open_ratio" in df.columns
        assert "close_position" in df.columns
        assert "vwap" in df.columns
        assert "close_vwap_ratio" in df.columns

        # Проверяем валидность значений
        assert df["close_position"].between(0, 1).all()
        assert df["high_low_ratio"].gt(0.99).all()  # high >= low
        assert not df["returns"].isna()[1:].any()  # Кроме первого

    def test_create_technical_indicators(self, feature_engineer, sample_ohlcv_data):
        """Тест создания технических индикаторов"""
        df = feature_engineer._create_technical_indicators(sample_ohlcv_data.copy())

        # Проверяем наличие индикаторов
        assert "sma_10" in df.columns
        assert "ema_10" in df.columns
        assert "rsi" in df.columns
        assert "macd" in df.columns
        assert "bb_upper" in df.columns
        assert "atr" in df.columns
        assert "stoch_k" in df.columns
        assert "adx" in df.columns

        # Проверяем валидность RSI
        assert df["rsi"].dropna().between(0, 100).all()

        # Проверяем Bollinger Bands
        assert (df["bb_upper"] >= df["bb_lower"]).all()
        assert df["bb_position"].between(0, 1).all()

    def test_create_volume_features(self, feature_engineer, sample_ohlcv_data):
        """Тест создания объемных признаков"""
        df = feature_engineer._create_volume_features(sample_ohlcv_data.copy())

        # Проверяем наличие признаков
        assert "volume_ma_5" in df.columns
        assert "volume_ratio_5" in df.columns
        assert "directed_volume" in df.columns
        assert "obv" in df.columns
        assert "mfi" in df.columns
        assert "cmf" in df.columns

        # Проверяем MFI
        assert df["mfi"].dropna().between(0, 100).all()

    def test_create_statistical_features(self, feature_engineer, sample_ohlcv_data):
        """Тест создания статистических признаков"""
        # Сначала нужны returns
        df = feature_engineer._create_basic_features(sample_ohlcv_data.copy())
        df = feature_engineer._create_statistical_features(df)

        # Проверяем наличие признаков
        assert "volatility_5" in df.columns
        assert "returns_skew" in df.columns
        assert "returns_kurt" in df.columns
        assert "high_max_10" in df.columns
        assert "position_in_range_10" in df.columns
        assert "close_zscore" in df.columns

        # Проверяем position_in_range
        assert df["position_in_range_10"].dropna().between(0, 1).all()

    def test_create_microstructure_features(self, feature_engineer, sample_ohlcv_data):
        """Тест создания микроструктурных признаков"""
        # Сначала нужны returns
        df = feature_engineer._create_basic_features(sample_ohlcv_data.copy())
        df = feature_engineer._create_microstructure_features(df)

        # Проверяем наличие признаков
        assert "hl_spread" in df.columns
        assert "price_impact" in df.columns
        assert "amihud_illiquidity" in df.columns
        assert "kyle_lambda" in df.columns
        assert "realized_vol_1h" in df.columns
        assert "price_efficiency" in df.columns

    def test_create_temporal_features(self, feature_engineer, sample_ohlcv_data):
        """Тест создания временных признаков"""
        df = feature_engineer._create_temporal_features(sample_ohlcv_data.copy())

        # Проверяем наличие признаков
        assert "hour" in df.columns
        assert "dayofweek" in df.columns
        assert "is_weekend" in df.columns
        assert "asian_session" in df.columns
        assert "hour_sin" in df.columns
        assert "hour_cos" in df.columns

        # Проверяем валидность
        assert df["hour"].between(0, 23).all()
        assert df["dayofweek"].between(0, 6).all()
        assert df["is_weekend"].isin([0, 1]).all()

    def test_create_pattern_features(self, feature_engineer, sample_ohlcv_data):
        """Тест создания паттернов"""
        # Подготавливаем данные с необходимыми признаками
        df = feature_engineer._create_basic_features(sample_ohlcv_data.copy())
        df = feature_engineer._create_technical_indicators(df)
        df = feature_engineer._create_statistical_features(df)
        df = feature_engineer._create_pattern_features(df)

        # Проверяем наличие признаков
        assert "volatility_squeeze" in df.columns
        assert "uptrend_structure" in df.columns
        assert "momentum_1h" in df.columns
        assert "volume_spike" in df.columns
        assert "pivot" in df.columns

        # Проверяем бинарные признаки
        assert df["volatility_squeeze"].isin([0, 1]).all()
        assert df["uptrend_structure"].isin([0, 1]).all()

    def test_create_target_variables(self, feature_engineer, sample_ohlcv_data):
        """Тест создания целевых переменных"""
        df = feature_engineer.create_target_variables(sample_ohlcv_data.copy())

        # Проверяем наличие всех 20 целевых переменных
        # Базовые возвраты (4)
        assert "future_return_15m" in df.columns
        assert "future_return_1h" in df.columns
        assert "future_return_4h" in df.columns
        assert "future_return_12h" in df.columns

        # Направления (4)
        assert "direction_15m" in df.columns
        assert "direction_1h" in df.columns
        assert "direction_4h" in df.columns
        assert "direction_12h" in df.columns

        # LONG уровни (4)
        assert "long_will_reach_1pct_4h" in df.columns
        assert "long_will_reach_2pct_4h" in df.columns
        assert "long_will_reach_3pct_12h" in df.columns
        assert "long_will_reach_5pct_12h" in df.columns

        # SHORT уровни (4)
        assert "short_will_reach_1pct_4h" in df.columns
        assert "short_will_reach_2pct_4h" in df.columns
        assert "short_will_reach_3pct_12h" in df.columns
        assert "short_will_reach_5pct_12h" in df.columns

        # Риск метрики (4)
        assert "max_drawdown_1h" in df.columns
        assert "max_drawdown_4h" in df.columns
        assert "max_rally_1h" in df.columns
        assert "max_rally_4h" in df.columns

        # Проверяем типы данных
        for col in ["long_will_reach_1pct_4h", "short_will_reach_1pct_4h"]:
            assert df[col].dropna().isin([0, 1]).all()

    def test_create_features_full_pipeline(self, feature_engineer, sample_ohlcv_data):
        """Тест полного пайплайна создания признаков"""
        df = feature_engineer.create_features(sample_ohlcv_data)

        # Проверяем, что добавлено много признаков
        original_cols = len(sample_ohlcv_data.columns)
        new_cols = len(df.columns)
        assert new_cols > original_cols + 150  # Ожидаем 200+ признаков

        # Проверяем отсутствие NaN в большинстве колонок
        nan_ratio = df.isna().sum() / len(df)
        assert (nan_ratio < 0.5).sum() > len(
            df.columns
        ) * 0.8  # 80% колонок имеют <50% NaN

        # Проверяем, что feature_names обновлены
        assert feature_engineer._initialized
        assert len(feature_engineer.feature_names) > 150

    def test_handle_missing_values(self, feature_engineer, sample_ohlcv_data):
        """Тест обработки пропущенных значений"""
        # Добавляем искусственные NaN и inf
        df = sample_ohlcv_data.copy()
        df.loc[10:20, "close"] = np.nan
        df.loc[30:40, "volume"] = np.inf

        df = feature_engineer._create_basic_features(df)
        df = feature_engineer._handle_missing_values(df)

        # Проверяем отсутствие inf
        assert not np.isinf(df.select_dtypes(include=[np.number])).any().any()

        # Проверяем, что NaN заполнены
        assert df["close"].notna().all()

    def test_multi_symbol_data(self, feature_engineer):
        """Тест работы с данными нескольких символов"""
        # Создаем данные для двух символов
        dates = pd.date_range(start="2024-01-01", periods=50, freq="15min")

        data1 = {
            "datetime": dates,
            "symbol": "BTCUSDT",
            "open": np.random.uniform(49000, 51000, 50),
            "high": np.random.uniform(50000, 52000, 50),
            "low": np.random.uniform(48000, 50000, 50),
            "close": np.random.uniform(49000, 51000, 50),
            "volume": np.random.uniform(1000, 5000, 50),
            "turnover": np.random.uniform(1e6, 5e6, 50),
        }

        data2 = {
            "datetime": dates,
            "symbol": "ETHUSDT",
            "open": np.random.uniform(2900, 3100, 50),
            "high": np.random.uniform(3000, 3200, 50),
            "low": np.random.uniform(2800, 3000, 50),
            "close": np.random.uniform(2900, 3100, 50),
            "volume": np.random.uniform(5000, 15000, 50),
            "turnover": np.random.uniform(1e6, 3e6, 50),
        }

        df = pd.concat([pd.DataFrame(data1), pd.DataFrame(data2)])

        # Создаем признаки
        result = feature_engineer.create_features(df)

        # Проверяем, что признаки созданы для обоих символов
        assert len(result[result["symbol"] == "BTCUSDT"]) == 50
        assert len(result[result["symbol"] == "ETHUSDT"]) == 50

        # Проверяем, что returns рассчитаны правильно по группам
        btc_data = result[result["symbol"] == "BTCUSDT"].sort_values("datetime")
        assert btc_data["returns"].iloc[0] != btc_data["returns"].iloc[0]  # Первый NaN
        assert not np.isnan(btc_data["returns"].iloc[1])  # Второй не NaN

    def test_get_feature_names(self, feature_engineer, sample_ohlcv_data):
        """Тест получения списка признаков"""
        # До создания признаков должна быть ошибка
        with pytest.raises(ValueError):
            feature_engineer.get_feature_names()

        # После создания признаков
        df = feature_engineer.create_features(sample_ohlcv_data)
        feature_names = feature_engineer.get_feature_names()

        assert isinstance(feature_names, list)
        assert len(feature_names) > 150
        assert "returns" in feature_names
        assert "rsi" in feature_names
        assert "volume_ma_5" in feature_names

        # Проверяем, что целевые переменные не включены
        assert "future_return_1h" not in feature_names
        assert "direction_1h" not in feature_names
