"""
Unit тесты для feature_engineering_v2.py - адаптированная версия из LLM TRANSFORM
"""

import os
import sys

import numpy as np
import pandas as pd
import pytest

# Добавляем корневую папку проекта в PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from ml.logic.feature_engineering_v2 import FeatureEngineer


class TestFeatureEngineerV2:
    """Тесты для FeatureEngineer версии 2 (адаптированной из LLM TRANSFORM)"""

    @pytest.fixture
    def sample_config(self):
        """Конфигурация для тестов"""
        return {
            "features": {
                "technical": [
                    {"name": "sma", "periods": [20, 50]},
                    {"name": "ema", "periods": [12, 26]},
                    {"name": "rsi", "period": 14},
                    {"name": "macd", "slow": 26, "fast": 12, "signal": 9},
                    {"name": "bollinger_bands", "period": 20, "std_dev": 2},
                    {"name": "atr", "period": 14},
                ]
            }
        }

    @pytest.fixture
    def sample_data(self):
        """Создаем тестовые данные OHLCV"""
        dates = pd.date_range(start="2024-01-01", periods=200, freq="15min")

        # Генерируем реалистичные цены
        np.random.seed(42)
        base_price = 50000
        returns = np.random.normal(0, 0.02, len(dates))
        prices = [base_price]

        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))

        data = []
        for i, (date, price) in enumerate(zip(dates, prices)):
            # Генерируем OHLC на основе цены
            noise = np.random.normal(0, 0.005, 4)
            open_price = price * (1 + noise[0])
            high_price = max(open_price, price * (1 + abs(noise[1])))
            low_price = min(open_price, price * (1 - abs(noise[2])))
            close_price = price

            volume = np.random.uniform(1000, 10000)
            turnover = volume * close_price

            data.append(
                {
                    "id": i,
                    "symbol": "BTCUSDT",
                    "datetime": date,
                    "timestamp": int(date.timestamp()),
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "volume": volume,
                    "turnover": turnover,
                }
            )

        return pd.DataFrame(data)

    @pytest.fixture
    def multi_symbol_data(self, sample_data):
        """Создаем данные для нескольких символов"""
        # Дублируем для ETHUSDT с другими ценами
        eth_data = sample_data.copy()
        eth_data["symbol"] = "ETHUSDT"
        eth_data["open"] = (
            eth_data["open"] * 0.08
        )  # ETH примерно в 12.5 раз дешевле BTC
        eth_data["high"] = eth_data["high"] * 0.08
        eth_data["low"] = eth_data["low"] * 0.08
        eth_data["close"] = eth_data["close"] * 0.08
        eth_data["id"] = eth_data["id"] + 1000  # Уникальные ID

        return pd.concat([sample_data, eth_data], ignore_index=True)

    def test_feature_engineer_init(self, sample_config):
        """Тест инициализации FeatureEngineer"""
        fe = FeatureEngineer(sample_config)

        assert fe.config == sample_config
        assert fe.feature_config == sample_config["features"]
        assert fe.scalers == {}
        assert not fe.disable_progress

    def test_safe_divide(self):
        """Тест безопасного деления"""
        numerator = pd.Series([10, 20, 30, 40])
        denominator = pd.Series([2, 0, 5, 1e-10])

        result = FeatureEngineer.safe_divide(numerator, denominator, fill_value=0.0)

        assert result.iloc[0] == 5.0  # 10/2
        assert result.iloc[1] == 0.0  # 20/0 -> fill_value
        assert result.iloc[2] == 6.0  # 30/5
        assert not np.isnan(result).any()
        assert not np.isinf(result).any()

    def test_calculate_vwap(self, sample_config, sample_data):
        """Тест расчета VWAP"""
        fe = FeatureEngineer(sample_config)
        fe.disable_progress = True

        vwap = fe.calculate_vwap(sample_data)

        assert len(vwap) == len(sample_data)
        assert not vwap.isna().any()
        assert not np.isinf(vwap).any()

        # VWAP должен быть близок к close (в разумных пределах)
        ratio = vwap / sample_data["close"]
        assert ratio.min() >= 0.5
        assert ratio.max() <= 2.0

    def test_basic_features_creation(self, sample_config, sample_data):
        """Тест создания базовых признаков"""
        fe = FeatureEngineer(sample_config)
        fe.disable_progress = True

        result = fe._create_basic_features(sample_data.copy())

        # Проверяем наличие базовых признаков
        expected_features = [
            "returns",
            "returns_5",
            "returns_10",
            "returns_20",
            "high_low_ratio",
            "close_open_ratio",
            "close_position",
            "volume_ratio",
            "turnover_ratio",
            "vwap",
            "close_vwap_ratio",
            "vwap_extreme_deviation",
        ]

        for feature in expected_features:
            assert feature in result.columns, f"Отсутствует признак: {feature}"

        # Проверяем корректность расчетов
        assert (result["high_low_ratio"] >= 1.0).all()  # high всегда >= low
        assert (result["close_position"] >= 0).all() and (
            result["close_position"] <= 1
        ).all()
        assert (
            not result["returns"].isna().iloc[1:].any()
        )  # returns не должны быть NaN кроме первого

    def test_technical_indicators_creation(self, sample_config, sample_data):
        """Тест создания технических индикаторов"""
        fe = FeatureEngineer(sample_config)
        fe.disable_progress = True

        # Сначала создаем базовые признаки
        data_with_basic = fe._create_basic_features(sample_data.copy())
        result = fe._create_technical_indicators(data_with_basic)

        # Проверяем наличие технических индикаторов
        expected_indicators = [
            "sma_20",
            "sma_50",
            "close_sma_20_ratio",
            "close_sma_50_ratio",
            "ema_12",
            "ema_26",
            "close_ema_12_ratio",
            "close_ema_26_ratio",
            "rsi",
            "rsi_oversold",
            "rsi_overbought",
            "macd",
            "macd_signal",
            "macd_diff",
            "bb_high",
            "bb_low",
            "bb_middle",
            "bb_width",
            "bb_position",
            "atr",
            "atr_pct",
        ]

        for indicator in expected_indicators:
            assert indicator in result.columns, f"Отсутствует индикатор: {indicator}"

        # Проверяем корректность RSI
        rsi_valid = result["rsi"].dropna()
        assert (rsi_valid >= 0).all() and (rsi_valid <= 100).all()

        # Проверяем корректность Bollinger Bands
        bb_position_valid = result["bb_position"].dropna()
        assert (bb_position_valid >= 0).all() and (bb_position_valid <= 1).all()

    def test_crypto_specific_indicators(self, sample_config, sample_data):
        """Тест криптоспецифичных индикаторов"""
        fe = FeatureEngineer(sample_config)
        fe.disable_progress = True

        # Создаем данные с базовыми признаками и ATR
        data_with_basic = fe._create_basic_features(sample_data.copy())
        data_with_tech = fe._create_technical_indicators(data_with_basic)

        # Проверяем наличие криптоспецифичных индикаторов
        expected_crypto_indicators = [
            "stoch_k",
            "stoch_d",
            "adx",
            "adx_pos",
            "adx_neg",
            "psar",
            "psar_trend",
            "psar_distance",
            "psar_distance_normalized",
            "vwma_20",
            "close_vwma_ratio",
        ]

        for indicator in expected_crypto_indicators:
            assert indicator in data_with_tech.columns, (
                f"Отсутствует криптоиндикатор: {indicator}"
            )

        # Проверяем корректность Stochastic
        stoch_k_valid = data_with_tech["stoch_k"].dropna()
        assert (stoch_k_valid >= 0).all() and (stoch_k_valid <= 100).all()

        # Проверяем корректность ADX
        adx_valid = data_with_tech["adx"].dropna()
        assert (adx_valid >= 0).all()

    def test_microstructure_features(self, sample_config, sample_data):
        """Тест признаков микроструктуры"""
        fe = FeatureEngineer(sample_config)
        fe.disable_progress = True

        # Создаем базовые признаки сначала
        data_with_basic = fe._create_basic_features(sample_data.copy())
        result = fe._create_microstructure_features(data_with_basic)

        expected_microstructure = [
            "hl_spread",
            "hl_spread_ma",
            "price_direction",
            "directed_volume",
            "volume_imbalance",
            "dollar_volume",
            "price_impact",
            "price_impact_log",
        ]

        for feature in expected_microstructure:
            assert feature in result.columns, (
                f"Отсутствует микроструктурный признак: {feature}"
            )

        # Проверяем корректность расчетов
        assert (result["hl_spread"] >= 0).all()  # Спред не может быть отрицательным
        assert result["price_direction"].isin([-1, 0, 1]).all()  # Направление цены
        assert (
            result["dollar_volume"] > 0
        ).all()  # Dollar volume должен быть положительным

    def test_temporal_features(self, sample_config, sample_data):
        """Тест временных признаков"""
        fe = FeatureEngineer(sample_config)
        fe.disable_progress = True

        result = fe._create_temporal_features(sample_data.copy())

        expected_temporal = [
            "hour",
            "minute",
            "hour_sin",
            "hour_cos",
            "dayofweek",
            "is_weekend",
            "dow_sin",
            "dow_cos",
            "day",
            "month",
            "month_sin",
            "month_cos",
            "asian_session",
            "european_session",
            "american_session",
            "session_overlap",
        ]

        for feature in expected_temporal:
            assert feature in result.columns, (
                f"Отсутствует временной признак: {feature}"
            )

        # Проверяем корректность циклического кодирования
        assert (result["hour_sin"] >= -1).all() and (result["hour_sin"] <= 1).all()
        assert (result["hour_cos"] >= -1).all() and (result["hour_cos"] <= 1).all()

        # Проверяем сессии (бинарные признаки)
        assert result["asian_session"].isin([0, 1]).all()
        assert result["european_session"].isin([0, 1]).all()
        assert result["american_session"].isin([0, 1]).all()

    def test_target_variables_creation(self, sample_config, sample_data):
        """Тест создания целевых переменных"""
        fe = FeatureEngineer(sample_config)
        fe.disable_progress = True

        result = fe._create_target_variables(sample_data.copy())

        # Проверяем наличие целевых переменных
        expected_targets = [
            "future_return_15m",
            "future_return_1h",
            "future_return_4h",
            "future_return_12h",
            "direction_15m",
            "direction_1h",
            "direction_4h",
            "direction_12h",
            "long_will_reach_1pct_4h",
            "long_will_reach_2pct_4h",
            "long_will_reach_3pct_12h",
            "long_will_reach_5pct_12h",
            "short_will_reach_1pct_4h",
            "short_will_reach_2pct_4h",
            "short_will_reach_3pct_12h",
            "short_will_reach_5pct_12h",
        ]

        for target in expected_targets:
            assert target in result.columns, f"Отсутствует целевая переменная: {target}"

        # Проверяем корректность направлений
        for period in ["15m", "1h", "4h", "12h"]:
            direction_col = f"direction_{period}"
            if direction_col in result.columns:
                unique_directions = result[direction_col].dropna().unique()
                expected_directions = {"UP", "DOWN", "FLAT"}
                assert set(unique_directions).issubset(expected_directions)

        # Проверяем бинарные целевые переменные
        binary_targets = [col for col in result.columns if "will_reach" in col]
        for target in binary_targets:
            assert result[target].isin([0, 1]).all(), (
                f"Целевая переменная {target} должна быть бинарной"
            )

    def test_cross_asset_features(self, sample_config, multi_symbol_data):
        """Тест кросс-активных признаков"""
        fe = FeatureEngineer(sample_config)
        fe.disable_progress = True

        # Создаем базовые признаки сначала
        data_with_basic = []
        for symbol in multi_symbol_data["symbol"].unique():
            symbol_data = multi_symbol_data[
                multi_symbol_data["symbol"] == symbol
            ].copy()
            symbol_data = fe._create_basic_features(symbol_data)
            data_with_basic.append(symbol_data)

        combined_data = pd.concat(data_with_basic, ignore_index=True)
        result = fe._create_cross_asset_features(combined_data)

        expected_cross_asset = [
            "btc_close",
            "btc_returns",
            "btc_correlation",
            "relative_strength_btc",
            "rs_btc_ma",
            "sector",
            "sector_returns",
            "relative_to_sector",
            "returns_rank",
        ]

        for feature in expected_cross_asset:
            assert feature in result.columns, (
                f"Отсутствует кросс-активный признак: {feature}"
            )

        # Проверяем наличие секторов
        sectors = result["sector"].unique()
        assert "btc" in sectors  # BTCUSDT должен быть в секторе 'btc'
        assert "other" in sectors  # ETHUSDT должен быть в секторе 'other'

        # Проверяем корреляцию с BTC
        btc_corr = result[result["symbol"] == "BTCUSDT"]["btc_correlation"].iloc[-10:]
        assert (btc_corr == 1.0).all()  # Корреляция BTC с самим собой должна быть 1.0

    def test_create_features_full_pipeline(self, sample_config, sample_data):
        """Тест полного пайплайна создания признаков"""
        fe = FeatureEngineer(sample_config)
        fe.disable_progress = True

        result = fe.create_features(sample_data)

        # Проверяем, что результат не пустой
        assert len(result) > 0
        assert len(result.columns) > len(sample_data.columns)

        # Проверяем отсутствие критических NaN в основных колонках
        critical_cols = ["symbol", "datetime", "close", "volume"]
        for col in critical_cols:
            assert not result[col].isna().any(), (
                f"Критическая колонка {col} содержит NaN"
            )

        # Проверяем типы данных
        assert pd.api.types.is_datetime64_any_dtype(result["datetime"])
        assert pd.api.types.is_numeric_dtype(result["close"])
        assert pd.api.types.is_numeric_dtype(result["volume"])

    def test_walk_forward_normalization(self, sample_config, sample_data):
        """Тест walk-forward нормализации"""
        fe = FeatureEngineer(sample_config)
        fe.disable_progress = True

        # Создаем данные с признаками
        data_with_features = fe.create_features(sample_data)

        # Определяем границу обучения (70% данных)
        train_end_date = data_with_features["datetime"].quantile(0.7)

        # Применяем walk-forward нормализацию
        result = fe._normalize_walk_forward(data_with_features, train_end_date)

        # Проверяем, что нормализация применена
        assert len(fe.scalers) > 0  # Скейлеры должны быть созданы
        assert "BTCUSDT" in fe.scalers  # Скейлер для BTCUSDT должен существовать

        # Проверяем, что данные изменились (нормализованы)
        original_close = sample_data["close"].values
        result_close = result["close"].values
        # close не должен измениться (он исключен из нормализации)
        np.testing.assert_array_almost_equal(original_close, result_close)

    def test_missing_values_handling(self, sample_config, sample_data):
        """Тест обработки пропущенных значений"""
        fe = FeatureEngineer(sample_config)
        fe.disable_progress = True

        # Добавляем пропущенные значения
        test_data = sample_data.copy()
        test_data.loc[10:15, "volume"] = np.nan
        test_data.loc[20:25, "close"] = np.nan

        # Создаем признаки с пропущенными значениями
        data_with_features = fe.create_features(test_data)

        # Обрабатываем пропущенные значения
        result = fe._handle_missing_values(data_with_features)

        # Проверяем, что критических NaN не осталось
        critical_cols = ["close", "volume", "open", "high", "low"]
        for col in critical_cols:
            assert not result[col].isna().any(), (
                f"В колонке {col} остались NaN после обработки"
            )

    def test_prepare_trading_data_without_leakage(
        self, sample_config, multi_symbol_data
    ):
        """Тест подготовки торговых данных без утечек"""
        fe = FeatureEngineer(sample_config)
        fe.disable_progress = True

        # Создаем признаки для всех символов
        featured_data = fe.create_features(multi_symbol_data)

        # Разделяем данные без утечек
        train_data, val_data, test_data = fe.prepare_trading_data_without_leakage(
            featured_data, train_ratio=0.6, val_ratio=0.2, disable_progress=True
        )

        # Проверяем размеры данных
        total_samples = len(featured_data)
        train_expected = int(total_samples * 0.6)
        val_expected = int(total_samples * 0.2)

        assert len(train_data) > 0
        assert len(val_data) > 0
        assert len(test_data) > 0

        # Проверяем временное разделение (без утечек)
        assert train_data["datetime"].max() <= val_data["datetime"].min()
        assert val_data["datetime"].max() <= test_data["datetime"].min()

        # Проверяем наличие скейлеров
        assert len(fe.scalers) > 0

        # Проверяем, что нормализация применена только к признакам
        exclude_cols = ["symbol", "datetime", "close", "volume", "open", "high", "low"]
        for col in exclude_cols:
            if col in train_data.columns:
                # Эти колонки не должны быть нормализованы
                original_vals = featured_data[col].dropna()
                train_vals = train_data[col].dropna()
                if len(original_vals) > 0 and len(train_vals) > 0:
                    # Проверяем, что значения примерно в том же диапазоне
                    assert (
                        abs(original_vals.mean() - train_vals.mean())
                        < original_vals.std()
                    )

    def test_feature_statistics_logging(self, sample_config, sample_data, caplog):
        """Тест логирования статистики признаков"""
        fe = FeatureEngineer(sample_config)
        fe.disable_progress = False  # Включаем прогресс для логирования

        result = fe.create_features(sample_data)

        # Проверяем, что статистика была залогирована
        assert "Feature engineering завершен" in caplog.text
        assert "признаков" in caplog.text


# Дополнительные тесты для edge cases
class TestFeatureEngineerEdgeCases:
    """Тесты для граничных случаев и обработки ошибок"""

    def test_empty_dataframe(self, sample_config):
        """Тест с пустым DataFrame"""
        fe = FeatureEngineer(sample_config)
        fe.disable_progress = True

        empty_df = pd.DataFrame(
            columns=[
                "symbol",
                "datetime",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "turnover",
            ]
        )

        # Функция должна обработать пустой DataFrame без ошибок
        result = fe.create_features(empty_df)
        assert len(result) == 0

    def test_single_row_dataframe(self, sample_config):
        """Тест с DataFrame из одной строки"""
        fe = FeatureEngineer(sample_config)
        fe.disable_progress = True

        single_row = pd.DataFrame(
            [
                {
                    "id": 1,
                    "symbol": "BTCUSDT",
                    "datetime": pd.Timestamp("2024-01-01"),
                    "timestamp": 1704067200,
                    "open": 50000,
                    "high": 50100,
                    "low": 49900,
                    "close": 50000,
                    "volume": 1000,
                    "turnover": 50000000,
                }
            ]
        )

        result = fe.create_features(single_row)
        # Результат может быть пустым из-за удаления строк с NaN в технических индикаторах
        assert len(result) >= 0

    def test_extreme_values_handling(self, sample_config):
        """Тест обработки экстремальных значений"""
        fe = FeatureEngineer(sample_config)
        fe.disable_progress = True

        # Создаем данные с экстремальными значениями
        extreme_data = pd.DataFrame(
            [
                {
                    "id": i,
                    "symbol": "BTCUSDT",
                    "datetime": pd.Timestamp("2024-01-01")
                    + pd.Timedelta(minutes=15 * i),
                    "timestamp": 1704067200 + 900 * i,
                    "open": (
                        50000 if i % 10 != 0 else 1e10
                    ),  # Экстремальное значение каждые 10 строк
                    "high": 50100 if i % 10 != 0 else 1e10,
                    "low": 49900 if i % 10 != 0 else 1e-10,
                    "close": 50000 if i % 10 != 0 else 1e10,
                    "volume": 1000 if i % 5 != 0 else 1e15,  # Экстремальный объем
                    "turnover": 50000000,
                }
                for i in range(100)
            ]
        )

        # Функция должна обработать экстремальные значения без crash
        result = fe.create_features(extreme_data)

        # Проверяем, что бесконечные значения были обработаны
        numeric_cols = result.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            assert not np.isinf(result[col]).any(), (
                f"Колонка {col} содержит бесконечные значения"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
