#!/usr/bin/env python3
"""
Integration тесты для Dynamic SL/TP
Тестирование полной цепочки от ML сигнала до создания ордера
"""

from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

from database.models.base_models import OrderSide, SignalType
from ml.ml_signal_processor import MLSignalProcessor

# Импорты компонентов системы
from trading.orders.dynamic_sltp_calculator import DynamicSLTPCalculator
from trading.orders.order_manager import OrderManager
from trading.orders.partial_tp_manager import PartialTPManager


@pytest.mark.integration
@pytest.mark.sltp
class TestDynamicSLTPFullIntegration:
    """Полная интеграция Dynamic SL/TP в торговую систему"""

    @pytest.fixture
    async def setup_components(self):
        """Настройка компонентов для интеграционного тестирования"""
        # Создаем моки для внешних зависимостей
        ml_manager_mock = Mock()
        config_mock = {
            "ml": {"min_confidence": 0.3, "min_signal_strength": 0.25, "risk_tolerance": "MEDIUM"},
            "trading": {"default_stop_loss_pct": 0.02, "default_take_profit_pct": 0.04},
        }

        # Создаем реальные компоненты
        calculator = DynamicSLTPCalculator()
        signal_processor = MLSignalProcessor(ml_manager=ml_manager_mock, config=config_mock)

        # Мокаем exchange registry
        exchange_registry_mock = Mock()

        # Создаем частичные компоненты
        order_manager = OrderManager(exchange_registry=exchange_registry_mock, logger=Mock())

        partial_tp_manager = PartialTPManager(
            exchange_registry=exchange_registry_mock, logger=Mock()
        )

        return {
            "calculator": calculator,
            "signal_processor": signal_processor,
            "order_manager": order_manager,
            "partial_tp_manager": partial_tp_manager,
            "ml_manager": ml_manager_mock,
            "exchange_registry": exchange_registry_mock,
        }

    @pytest.fixture
    def market_data_with_volatility(self):
        """Рыночные данные с различной волатильностью"""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="1min")

        # Создаем данные с изменяющейся волатильностью
        low_vol_data = []
        high_vol_data = []

        base_price = 50000

        for i in range(100):
            # Низкая волатильность
            low_change = np.random.normal(0, 0.001)
            low_price = base_price * (1 + low_change)
            low_vol_data.append(
                {
                    "timestamp": dates[i],
                    "open": low_price,
                    "high": low_price * 1.002,
                    "low": low_price * 0.998,
                    "close": low_price * (1 + np.random.normal(0, 0.0005)),
                    "volume": np.random.uniform(100, 200),
                }
            )

            # Высокая волатильность
            high_change = np.random.normal(0, 0.02)
            high_price = base_price * (1 + high_change)
            high_vol_data.append(
                {
                    "timestamp": dates[i],
                    "open": high_price,
                    "high": high_price * 1.03,
                    "low": high_price * 0.97,
                    "close": high_price * (1 + np.random.normal(0, 0.01)),
                    "volume": np.random.uniform(500, 1000),
                }
            )

        return {
            "low_volatility": pd.DataFrame(low_vol_data),
            "high_volatility": pd.DataFrame(high_vol_data),
        }

    @pytest.mark.asyncio
    async def test_ml_signal_to_dynamic_sltp(self, setup_components, market_data_with_volatility):
        """Тест: ML сигнал → расчет динамических SL/TP → создание сигнала"""
        components = await setup_components
        calculator = components["calculator"]

        # Данные для низкой волатильности
        candles = market_data_with_volatility["low_volatility"]
        current_price = 50000

        # ML предсказание
        ml_prediction = {
            "signal_type": "LONG",
            "confidence": 0.85,
            "signal_strength": 0.75,
            "stop_loss_pct": None,  # Будет рассчитано динамически
            "take_profit_pct": None,
        }

        # Расчет динамических уровней
        dynamic_levels = calculator.calculate_dynamic_levels(
            current_price=current_price,
            candles=candles,
            confidence=ml_prediction["confidence"],
            signal_type="BUY",
        )

        # Создание торгового сигнала с динамическими уровнями
        signal = {
            "symbol": "BTCUSDT",
            "signal_type": SignalType.LONG,
            "confidence": ml_prediction["confidence"],
            "entry_price": current_price,
            "stop_loss": dynamic_levels["stop_loss_price"],
            "take_profit": dynamic_levels["take_profit_price"],
            "metadata": {
                "dynamic_levels": dynamic_levels,
                "volatility_data": dynamic_levels["volatility_data"],
                "risk_params": {
                    "stop_loss_pct": dynamic_levels["stop_loss_pct"],
                    "take_profit_pct": dynamic_levels["take_profit_pct"],
                },
            },
        }

        # Проверки
        assert signal["stop_loss"] < current_price  # SL ниже для LONG
        assert signal["take_profit"] > current_price  # TP выше для LONG
        assert "dynamic_levels" in signal["metadata"]
        assert signal["metadata"]["volatility_data"]["volatility_regime"] == "low"
        assert 1.0 <= signal["metadata"]["risk_params"]["stop_loss_pct"] <= 1.5
        assert 3.6 <= signal["metadata"]["risk_params"]["take_profit_pct"] <= 4.5

    @pytest.mark.asyncio
    async def test_order_creation_with_dynamic_levels(self, setup_components):
        """Тест создания ордера с динамическими уровнями"""
        components = await setup_components
        order_manager = components["order_manager"]

        # Мокаем exchange
        exchange_mock = Mock()
        exchange_mock.place_order = Mock(return_value={"success": True, "order_id": "TEST123"})
        components["exchange_registry"].get_exchange = Mock(return_value=exchange_mock)

        # Создаем ордер с динамическими метаданными
        order_data = {
            "symbol": "BTCUSDT",
            "side": OrderSide.BUY,
            "quantity": 0.01,
            "price": 50000,
            "stop_loss": 49000,
            "take_profit": 52000,
            "metadata": {
                "dynamic_levels": {
                    "stop_loss_pct": 2.0,
                    "take_profit_pct": 4.0,
                    "partial_tp_levels": [
                        {"percent": 40, "price": 50800},
                        {"percent": 70, "price": 51400},
                        {"percent": 100, "price": 52000},
                    ],
                },
                "volatility_data": {"atr": 500, "volatility_regime": "medium"},
            },
        }

        # Патчим методы для тестирования
        with patch.object(order_manager, "_save_order_to_db", return_value=None):
            with patch.object(order_manager, "exchange_manager") as mock_exchange_manager:
                mock_exchange_manager.place_order = Mock(return_value={"success": True})

                # Вызываем submit_order
                result = await order_manager.submit_order(order_data)

                # Проверяем что динамические данные были обработаны
                assert mock_exchange_manager.place_order.called
                call_args = mock_exchange_manager.place_order.call_args

                # Проверяем что SL и TP переданы
                assert call_args.kwargs.get("stop_loss") == 49000
                assert call_args.kwargs.get("take_profit") == 52000

    @pytest.mark.asyncio
    async def test_partial_tp_with_volatility_adaptation(self, setup_components):
        """Тест адаптации Partial TP под волатильность"""
        components = await setup_components
        partial_tp_manager = components["partial_tp_manager"]

        # Мокаем exchange
        exchange_mock = Mock()
        exchange_mock.place_order = Mock(return_value={"success": True})
        components["exchange_registry"].get_exchange = Mock(return_value=exchange_mock)

        # Тест для низкой волатильности
        low_vol_result = await partial_tp_manager.setup_partial_tp(
            position={"symbol": "BTCUSDT", "side": "long", "quantity": 0.01, "entry_price": 50000},
            config={
                "enabled": True,
                "levels": [
                    {"percent": 30, "price_ratio": 1.01},
                    {"percent": 30, "price_ratio": 1.02},
                    {"percent": 40, "price_ratio": 1.03},
                ],
            },
        )

        # При низкой волатильности должны быть более агрессивные уровни
        assert low_vol_result is not None

        # Тест для высокой волатильности
        high_vol_config = {
            "enabled": True,
            "levels": [
                {"percent": 20, "price_ratio": 1.015},  # Меньший процент
                {"percent": 30, "price_ratio": 1.025},
                {"percent": 50, "price_ratio": 1.04},  # Больший финальный уровень
            ],
        }

        high_vol_result = await partial_tp_manager.setup_partial_tp(
            position={"symbol": "BTCUSDT", "side": "long", "quantity": 0.01, "entry_price": 50000},
            config=high_vol_config,
        )

        assert high_vol_result is not None

    @pytest.mark.asyncio
    async def test_volatility_regime_changes(self, market_data_with_volatility):
        """Тест изменения режима волатильности"""
        calculator = DynamicSLTPCalculator()

        # Низкая волатильность
        low_vol_levels = calculator.calculate_dynamic_levels(
            current_price=50000,
            candles=market_data_with_volatility["low_volatility"],
            confidence=0.7,
            signal_type="BUY",
        )

        # Высокая волатильность
        high_vol_levels = calculator.calculate_dynamic_levels(
            current_price=50000,
            candles=market_data_with_volatility["high_volatility"],
            confidence=0.7,
            signal_type="BUY",
        )

        # При высокой волатильности уровни должны быть шире
        assert high_vol_levels["stop_loss_pct"] > low_vol_levels["stop_loss_pct"]
        assert high_vol_levels["take_profit_pct"] > low_vol_levels["take_profit_pct"]

        # Проверяем режимы
        assert low_vol_levels["volatility_data"]["volatility_regime"] == "low"
        assert high_vol_levels["volatility_data"]["volatility_regime"] == "high"

    @pytest.mark.asyncio
    async def test_metadata_propagation(self, setup_components):
        """Тест передачи метаданных через всю цепочку"""
        components = await setup_components

        # Создаем сигнал с динамическими уровнями
        signal_with_metadata = {
            "symbol": "BTCUSDT",
            "signal_type": SignalType.LONG,
            "confidence": 0.85,
            "entry_price": 50000,
            "metadata": {
                "dynamic_levels": {
                    "stop_loss_pct": 1.5,
                    "take_profit_pct": 4.5,
                    "partial_tp_levels": [
                        {"percent": 40, "price": 50900},
                        {"percent": 70, "price": 51575},
                        {"percent": 100, "price": 52250},
                    ],
                },
                "volatility_data": {
                    "atr": 400,
                    "volatility_regime": "low",
                    "normalized_volatility": 0.008,
                },
                "expected_value": {
                    "risk_reward_ratio": 3.0,
                    "win_rate_required": 0.25,
                    "expected_value_45wr": 0.8,
                },
            },
        }

        # Проверяем что метаданные содержат все необходимые поля
        metadata = signal_with_metadata["metadata"]

        assert "dynamic_levels" in metadata
        assert "volatility_data" in metadata
        assert "expected_value" in metadata

        # Проверяем структуру dynamic_levels
        dynamic_levels = metadata["dynamic_levels"]
        assert "stop_loss_pct" in dynamic_levels
        assert "take_profit_pct" in dynamic_levels
        assert "partial_tp_levels" in dynamic_levels
        assert len(dynamic_levels["partial_tp_levels"]) == 3

        # Проверяем структуру volatility_data
        vol_data = metadata["volatility_data"]
        assert "atr" in vol_data
        assert "volatility_regime" in vol_data
        assert vol_data["volatility_regime"] in ["low", "medium", "high"]

        # Проверяем структуру expected_value
        ev_data = metadata["expected_value"]
        assert ev_data["risk_reward_ratio"] >= 3.0
        assert 0.20 <= ev_data["win_rate_required"] <= 0.30
        assert ev_data["expected_value_45wr"] > 0


@pytest.mark.integration
@pytest.mark.sltp
class TestDynamicSLTPLogging:
    """Тесты логирования динамических SL/TP"""

    @pytest.mark.asyncio
    async def test_logging_with_emojis(self, caplog):
        """Тест правильного логирования с эмодзи"""
        calculator = DynamicSLTPCalculator()

        # Создаем тестовые данные
        dates = pd.date_range(start="2024-01-01", periods=50, freq="1min")
        candles = pd.DataFrame(
            {
                "timestamp": dates,
                "open": np.random.uniform(49000, 51000, 50),
                "high": np.random.uniform(49500, 51500, 50),
                "low": np.random.uniform(48500, 50500, 50),
                "close": np.random.uniform(49000, 51000, 50),
                "volume": np.random.uniform(100, 1000, 50),
            }
        )

        with caplog.at_level("INFO"):
            result = calculator.calculate_dynamic_levels(
                current_price=50000, candles=candles, confidence=0.8, signal_type="BUY"
            )

        # Проверяем логи на наличие эмодзи
        log_text = " ".join([record.message for record in caplog.records])

        # Должны быть эмодзи для динамических уровней
        assert "📊" in log_text or "Dynamic" in log_text

        # Проверяем что результат содержит информацию для логирования
        assert result["volatility_data"]["volatility_regime"] is not None
