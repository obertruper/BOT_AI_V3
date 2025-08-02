#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit тесты для PatchTST ML стратегии
"""

import pickle
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
import torch
from sklearn.preprocessing import StandardScaler

from database.models import Signal, SignalType
from strategies.ml_strategy.patchtst_strategy import PatchTSTStrategy


@pytest.fixture
def mock_model_files(tmp_path):
    """Создание временных файлов модели для тестов"""
    model_dir = tmp_path / "models" / "patchtst"
    model_dir.mkdir(parents=True)

    # Mock config
    config = {
        "model": {
            "input_size": 240,
            "context_window": 96,
            "output_size": 20,
            "d_model": 256,
            "n_heads": 4,
            "e_layers": 3,
        }
    }
    with open(model_dir / "config.pkl", "wb") as f:
        pickle.dump(config, f)

    # Mock scaler
    scaler = StandardScaler()
    # Фиктивные данные для fit
    fake_data = np.random.randn(1000, 240)
    scaler.fit(fake_data)
    with open(model_dir / "scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)

    # Mock model weights (пустой файл для теста)
    torch.save({}, model_dir / "model.pth")

    return model_dir


@pytest.fixture
def strategy_params(mock_model_files):
    """Параметры для инициализации стратегии"""
    return {
        "model_path": str(mock_model_files / "model.pth"),
        "scaler_path": str(mock_model_files / "scaler.pkl"),
        "config_path": str(mock_model_files / "config.pkl"),
        "min_confidence": 0.6,
        "min_profit_probability": 0.65,
        "max_risk_threshold": 0.03,
    }


@pytest.fixture
def market_data():
    """Тестовые рыночные данные"""
    candles = []
    base_price = 50000.0

    for i in range(100):
        timestamp = datetime.utcnow() - timedelta(minutes=15 * (99 - i))
        price = base_price + np.random.randn() * 100

        candles.append(
            {
                "timestamp": timestamp,
                "open": price,
                "high": price + abs(np.random.randn()) * 50,
                "low": price - abs(np.random.randn()) * 50,
                "close": price + np.random.randn() * 30,
                "volume": 100 + abs(np.random.randn()) * 50,
            }
        )

    return {"candles": candles}


class TestPatchTSTStrategy:
    """Тесты для PatchTST стратегии"""

    @pytest.mark.asyncio
    async def test_initialization(self, strategy_params):
        """Тест инициализации стратегии"""
        strategy = PatchTSTStrategy(
            name="Test_ML",
            symbol="BTC/USDT",
            exchange="binance",
            parameters=strategy_params,
        )

        assert strategy.name == "Test_ML"
        assert strategy.symbol == "BTC/USDT"
        assert strategy.exchange == "binance"
        assert strategy.timeframe == "15m"
        assert strategy.min_confidence == 0.6
        assert strategy.min_profit_probability == 0.65

    @pytest.mark.asyncio
    async def test_model_loading(self, strategy_params):
        """Тест загрузки модели"""
        strategy = PatchTSTStrategy(parameters=strategy_params)

        # Mock модель
        with patch(
            "strategies.ml_strategy.patchtst_strategy.UnifiedPatchTSTForTrading"
        ) as mock_model:
            mock_instance = MagicMock()
            mock_model.return_value = mock_instance

            await strategy._load_models()

            assert strategy.model is not None
            assert strategy.scaler is not None
            assert strategy.model_config is not None

    def test_price_buffer_update(self, strategy_params, market_data):
        """Тест обновления буфера цен"""
        strategy = PatchTSTStrategy(parameters=strategy_params)

        # Изначально буфер пустой
        assert len(strategy.price_buffer) == 0

        # Обновляем буфер
        strategy._update_price_buffer(market_data)

        # Проверяем что добавилась последняя свеча
        assert len(strategy.price_buffer) == 1
        assert strategy.price_buffer[0]["close"] == market_data["candles"][-1]["close"]

    @pytest.mark.asyncio
    async def test_feature_preparation(self, strategy_params):
        """Тест подготовки признаков"""
        strategy = PatchTSTStrategy(parameters=strategy_params)

        # Создаем фиктивный буфер
        for i in range(100):
            strategy.price_buffer.append(
                {
                    "datetime": datetime.utcnow() - timedelta(minutes=15 * i),
                    "open": 50000 + np.random.randn() * 100,
                    "high": 50100 + np.random.randn() * 100,
                    "low": 49900 + np.random.randn() * 100,
                    "close": 50000 + np.random.randn() * 100,
                    "volume": 100 + abs(np.random.randn()) * 10,
                    "symbol": "BTC/USDT",
                }
            )

        # Mock FeatureEngineer
        with patch.object(strategy, "feature_engineer") as mock_fe:
            mock_fe.create_features.return_value = pd.DataFrame(
                np.random.randn(100, 240), columns=[f"feature_{i}" for i in range(240)]
            )
            mock_fe.get_feature_names.return_value = [
                f"feature_{i}" for i in range(240)
            ]

            features_df = strategy._prepare_features()

            assert features_df is not None
            assert len(features_df) == 96  # min_buffer_size
            assert features_df.shape[1] == 240  # количество признаков

    @pytest.mark.asyncio
    async def test_model_predictions(self, strategy_params):
        """Тест получения предсказаний от модели"""
        strategy = PatchTSTStrategy(parameters=strategy_params)

        # Mock компоненты
        strategy.model = MagicMock()
        strategy.scaler = MagicMock()
        strategy.device = torch.device("cpu")

        # Подготовка данных
        features_df = pd.DataFrame(np.random.randn(96, 240))
        strategy.scaler.transform.return_value = features_df.values

        # Mock выход модели
        mock_output = torch.randn(1, 20)
        strategy.model.return_value = mock_output

        predictions = await strategy._get_model_predictions(features_df)

        assert predictions is not None
        assert predictions.shape == (20,)

    def test_analyze_predictions_long_signal(self, strategy_params, market_data):
        """Тест анализа предсказаний - LONG сигнал"""
        strategy = PatchTSTStrategy(parameters=strategy_params)

        # Создаем предсказания для LONG сигнала
        predictions = np.zeros(20)
        # Future returns положительные
        predictions[0:4] = [0.002, 0.005, 0.01, 0.015]
        # Directions: большинство LONG (0)
        predictions[4:8] = [0, 0, 0, 2]  # 3 LONG, 1 FLAT
        # Long probabilities высокие
        predictions[8:12] = [2.0, 2.5, 1.8, 2.2]  # Будут >0.8 после sigmoid
        # Risk metrics низкие
        predictions[16:20] = [0.01, 0.005, 0.015, 0.008]

        signal = strategy._analyze_predictions(predictions, market_data)

        assert signal is not None
        assert signal.signal_type == SignalType.LONG
        assert signal.confidence > 0.6
        assert signal.stop_loss < market_data["candles"][-1]["close"]
        assert signal.take_profit > market_data["candles"][-1]["close"]

    def test_analyze_predictions_short_signal(self, strategy_params, market_data):
        """Тест анализа предсказаний - SHORT сигнал"""
        strategy = PatchTSTStrategy(parameters=strategy_params)

        # Создаем предсказания для SHORT сигнала
        predictions = np.zeros(20)
        # Future returns отрицательные
        predictions[0:4] = [-0.002, -0.005, -0.01, -0.015]
        # Directions: большинство SHORT (1)
        predictions[4:8] = [1, 1, 1, 2]  # 3 SHORT, 1 FLAT
        # Short probabilities высокие
        predictions[12:16] = [2.0, 2.5, 1.8, 2.2]  # Будут >0.8 после sigmoid
        # Risk metrics низкие
        predictions[16:20] = [0.005, 0.01, 0.008, 0.015]

        signal = strategy._analyze_predictions(predictions, market_data)

        assert signal is not None
        assert signal.signal_type == SignalType.SHORT
        assert signal.confidence > 0.6
        assert signal.stop_loss > market_data["candles"][-1]["close"]
        assert signal.take_profit < market_data["candles"][-1]["close"]

    def test_analyze_predictions_no_signal(self, strategy_params, market_data):
        """Тест анализа предсказаний - нет сигнала"""
        strategy = PatchTSTStrategy(parameters=strategy_params)

        # Создаем предсказания для FLAT
        predictions = np.zeros(20)
        # Смешанные направления
        predictions[4:8] = [0, 1, 2, 2]  # Нет явного большинства
        # Низкие вероятности прибыли
        predictions[8:16] = [-2.0] * 8  # Будут <0.2 после sigmoid

        signal = strategy._analyze_predictions(predictions, market_data)

        assert signal is None

    def test_signal_strength_calculation(self, strategy_params):
        """Тест расчета силы сигнала"""
        strategy = PatchTSTStrategy(parameters=strategy_params)

        # Тест с высокими показателями
        strength = strategy._calculate_signal_strength(
            direction_confidence=0.9,
            profit_probability=0.8,
            risk_level=0.01,
            future_returns=np.array([0.02, 0.03, 0.04, 0.05]),
        )

        assert 0.7 < strength <= 1.0

        # Тест с низкими показателями
        strength = strategy._calculate_signal_strength(
            direction_confidence=0.5,
            profit_probability=0.4,
            risk_level=0.05,
            future_returns=np.array([0.001, 0.001, 0.001, 0.001]),
        )

        assert 0.0 <= strength < 0.5

    @pytest.mark.asyncio
    async def test_position_sizing_kelly(self, strategy_params):
        """Тест расчета размера позиции - Kelly Criterion"""
        strategy = PatchTSTStrategy(parameters=strategy_params)
        strategy.parameters["position_sizing_mode"] = "kelly"
        strategy.parameters["kelly_safety_factor"] = 0.25

        # Создаем сигнал с метаданными
        signal = Signal(
            symbol="BTC/USDT",
            exchange="binance",
            signal_type=SignalType.LONG,
            strength=0.8,
            confidence=0.7,
            stop_loss=49000.0,
            take_profit=51000.0,
            metadata={
                "profit_probabilities": {
                    "1pct_4h": 0.7,
                    "2pct_4h": 0.6,
                    "3pct_12h": 0.5,
                    "5pct_12h": 0.4,
                }
            },
        )

        # Mock текущую цену
        strategy._price_history = [{"close": 50000.0}]

        position_size = await strategy.calculate_position_size(
            signal,
            Decimal("10000.00"),  # $10,000 баланс
        )

        assert position_size > 0
        assert position_size <= Decimal("1000.00")  # Не более 10%

    @pytest.mark.asyncio
    async def test_position_sizing_fixed(self, strategy_params):
        """Тест расчета размера позиции - фиксированный риск"""
        strategy = PatchTSTStrategy(parameters=strategy_params)
        strategy.parameters["position_sizing_mode"] = "fixed"
        strategy.parameters["fixed_risk_pct"] = 0.02

        signal = Signal(
            symbol="BTC/USDT",
            exchange="binance",
            signal_type=SignalType.LONG,
            strength=1.0,
            confidence=0.8,
        )

        position_size = await strategy.calculate_position_size(
            signal, Decimal("10000.00")
        )

        # 2% * strength(1.0) = 2% от баланса
        assert position_size == Decimal("200.00")

    def test_calculate_levels(self, strategy_params):
        """Тест расчета уровней stop-loss и take-profit"""
        strategy = PatchTSTStrategy(parameters=strategy_params)
        strategy.parameters["risk_multiplier"] = 1.5
        strategy.parameters["min_risk_reward_ratio"] = 2.0

        # Тест для LONG
        current_price = 50000.0
        risk_values = np.array([0.01, 0.015])  # 1% и 1.5% риск
        profit_probs = np.array(
            [0.6, 0.8, 0.7, 0.5]
        )  # Макс вероятность для 2% (индекс 1)

        stop_loss, take_profit = strategy._calculate_levels(
            "LONG", current_price, risk_values, profit_probs
        )

        assert stop_loss < current_price
        assert take_profit > current_price
        assert (take_profit - current_price) >= 2 * (
            current_price - stop_loss
        )  # RR >= 2

    @pytest.mark.asyncio
    async def test_full_analyze_flow(self, strategy_params, market_data):
        """Тест полного процесса анализа"""
        strategy = PatchTSTStrategy(parameters=strategy_params)

        # Mock все компоненты
        with patch.object(strategy, "_load_models") as mock_load:
            await strategy.on_start()
            mock_load.assert_called_once()

        # Mock модель и компоненты
        strategy.model = MagicMock()
        strategy.scaler = MagicMock()
        strategy.feature_engineer = MagicMock()
        strategy.device = torch.device("cpu")

        # Заполняем буфер
        for _ in range(96):
            strategy._update_price_buffer(market_data)

        # Mock feature engineering
        strategy.feature_engineer.create_features.return_value = pd.DataFrame(
            np.random.randn(100, 240), columns=[f"feature_{i}" for i in range(240)]
        )
        strategy.feature_engineer.get_feature_names.return_value = [
            f"feature_{i}" for i in range(240)
        ]

        # Mock scaler
        strategy.scaler.transform.return_value = np.random.randn(96, 240)

        # Mock model predictions
        predictions = torch.zeros(1, 20)
        predictions[0, 4:8] = torch.tensor([0, 0, 0, 2])  # LONG направление
        predictions[0, 8:12] = torch.tensor([2.0, 2.0, 2.0, 2.0])  # Высокие вероятности
        strategy.model.return_value = predictions

        # Запускаем анализ
        signal = await strategy.analyze(market_data)

        assert signal is not None
        assert isinstance(signal, Signal)
        assert signal.metadata is not None
        assert "model" in signal.metadata
        assert signal.metadata["model"] == "PatchTST"

    def test_get_metrics(self, strategy_params):
        """Тест получения метрик производительности"""
        strategy = PatchTSTStrategy(parameters=strategy_params)

        # Обновляем статистику
        strategy.prediction_stats["total_predictions"] = 100
        strategy.prediction_stats["correct_directions"] = 65
        strategy.prediction_stats["avg_confidence"] = 0.75

        metrics = strategy.get_metrics()

        assert "prediction_accuracy" in metrics
        assert metrics["prediction_accuracy"] == 0.65
        assert metrics["avg_prediction_confidence"] == 0.75
        assert metrics["total_ml_predictions"] == 100
        assert metrics["model_device"] == str(strategy.device)

    @pytest.mark.asyncio
    async def test_error_handling(self, strategy_params):
        """Тест обработки ошибок"""
        strategy = PatchTSTStrategy(parameters=strategy_params)

        # Тест с пустыми рыночными данными
        signal = await strategy.analyze({})
        assert signal is None

        # Тест с недостаточным количеством данных
        strategy.min_buffer_size = 100
        signal = await strategy.analyze({"candles": [{"close": 50000}]})
        assert signal is None

    @pytest.mark.asyncio
    async def test_memory_cleanup(self, strategy_params):
        """Тест очистки памяти при остановке"""
        strategy = PatchTSTStrategy(parameters=strategy_params)

        # Mock модель
        strategy.model = MagicMock()
        strategy.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Если GPU доступен, проверяем очистку
        if strategy.device.type == "cuda":
            with patch("torch.cuda.empty_cache") as mock_empty_cache:
                await strategy.on_stop()
                mock_empty_cache.assert_called_once()
        else:
            # На CPU просто проверяем что метод выполняется без ошибок
            await strategy.on_stop()

        assert strategy.model is None or strategy.device.type == "cpu"
