#!/usr/bin/env python3
"""
End-to-End тесты для Dynamic SL/TP
Полный сценарий от WebSocket данных до размещения ордера
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import numpy as np
import pandas as pd
import pytest

from database.models.base_models import OrderSide, SignalType
from ml.ml_signal_processor import MLSignalProcessor
from trading.orders.dynamic_sltp_calculator import DynamicSLTPCalculator


@pytest.mark.integration
@pytest.mark.sltp
@pytest.mark.e2e
class TestDynamicSLTPEndToEnd:
    """End-to-End тесты для полной цепочки Dynamic SL/TP"""

    @pytest.fixture
    async def full_system_setup(self):
        """Полная настройка системы для E2E тестирования"""
        # Создание моков для внешних сервисов

        # Мок WebSocket данных
        websocket_mock = Mock()
        websocket_mock.get_market_data = AsyncMock()

        # Мок базы данных
        database_mock = Mock()
        database_mock.fetch_market_data = AsyncMock()
        database_mock.save_signal = AsyncMock()
        database_mock.save_order = AsyncMock()

        # Мок биржи
        exchange_mock = Mock()
        exchange_mock.place_order = AsyncMock()
        exchange_mock.get_positions = AsyncMock(return_value=[])
        exchange_mock.get_ticker = AsyncMock()

        # Реальные компоненты
        calculator = DynamicSLTPCalculator()

        # ML Manager с мокированным предсказанием
        ml_manager_mock = Mock()
        ml_manager_mock.predict = AsyncMock()

        config = {
            "ml": {"min_confidence": 0.3, "min_signal_strength": 0.25},
            "trading": {"default_stop_loss_pct": 0.02, "default_take_profit_pct": 0.04},
        }

        signal_processor = MLSignalProcessor(ml_manager=ml_manager_mock, config=config)

        return {
            "calculator": calculator,
            "signal_processor": signal_processor,
            "websocket_mock": websocket_mock,
            "database_mock": database_mock,
            "exchange_mock": exchange_mock,
            "ml_manager_mock": ml_manager_mock,
        }

    @pytest.fixture
    def realistic_market_data(self):
        """Реалистичные рыночные данные для E2E тестов"""
        # Создаем данные, имитирующие реальные рыночные условия
        dates = pd.date_range(
            start=datetime.now() - timedelta(hours=2), end=datetime.now(), freq="1min"
        )

        # Генерируем цену с трендом и волатильностью
        base_price = 50000
        trend = 0.0001  # Небольшой восходящий тренд
        volatility = 0.002  # 0.2% волатильность

        prices = []
        current_price = base_price

        for i, timestamp in enumerate(dates):
            # Трендовое движение + случайные колебания
            price_change = trend + np.random.normal(0, volatility)
            current_price *= 1 + price_change

            # OHLCV данные
            high = current_price * (1 + abs(np.random.normal(0, 0.001)))
            low = current_price * (1 - abs(np.random.normal(0, 0.001)))
            open_price = current_price * (1 + np.random.normal(0, 0.0005))
            close_price = current_price
            volume = np.random.uniform(50, 500)

            prices.append(
                {
                    "timestamp": timestamp,
                    "symbol": "BTCUSDT",
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close_price,
                    "volume": volume,
                }
            )

        return pd.DataFrame(prices)

    @pytest.mark.asyncio
    async def test_full_trading_pipeline(self, full_system_setup, realistic_market_data):
        """Тест полного торгового pipeline с Dynamic SL/TP"""
        setup = await full_system_setup

        # Шаг 1: Получение рыночных данных
        market_data = realistic_market_data
        current_price = market_data["close"].iloc[-1]

        # Мокируем получение данных из БД
        setup["database_mock"].fetch_market_data.return_value = market_data.to_dict("records")

        # Шаг 2: ML предсказание
        ml_prediction = {
            "signal_type": "LONG",
            "confidence": 0.85,
            "signal_strength": 0.78,
            "stop_loss_pct": None,  # Будет рассчитано динамически
            "take_profit_pct": None,
            "metadata": {"model_version": "v2.1", "features_used": 240},
        }

        setup["ml_manager_mock"].predict.return_value = ml_prediction

        # Шаг 3: Расчет динамических SL/TP
        dynamic_levels = setup["calculator"].calculate_dynamic_levels(
            current_price=current_price,
            candles=market_data.tail(100),  # Последние 100 свечей
            confidence=ml_prediction["confidence"],
            signal_type="BUY",
        )

        # Шаг 4: Создание торгового сигнала
        trading_signal = {
            "symbol": "BTCUSDT",
            "signal_type": SignalType.LONG,
            "confidence": ml_prediction["confidence"],
            "entry_price": current_price,
            "stop_loss": dynamic_levels["stop_loss_price"],
            "take_profit": dynamic_levels["take_profit_price"],
            "quantity": 0.01,
            "metadata": {
                "dynamic_levels": dynamic_levels,
                "volatility_data": dynamic_levels["volatility_data"],
                "ml_prediction": ml_prediction,
                "created_at": datetime.now().isoformat(),
            },
        }

        # Шаг 5: Создание и размещение ордера
        order_data = {
            "symbol": trading_signal["symbol"],
            "side": OrderSide.BUY,
            "quantity": trading_signal["quantity"],
            "order_type": "MARKET",
            "stop_loss": trading_signal["stop_loss"],
            "take_profit": trading_signal["take_profit"],
            "metadata": trading_signal["metadata"],
        }

        # Мокируем успешное размещение ордера
        setup["exchange_mock"].place_order.return_value = {
            "success": True,
            "order_id": "TEST_ORDER_123",
            "filled_price": current_price,
            "filled_quantity": 0.01,
            "status": "FILLED",
        }

        # Выполняем размещение ордера
        order_result = await setup["exchange_mock"].place_order(
            symbol=order_data["symbol"],
            side=order_data["side"].value,
            quantity=order_data["quantity"],
            order_type=order_data["order_type"],
            stop_loss=order_data["stop_loss"],
            take_profit=order_data["take_profit"],
        )

        # Проверки E2E pipeline

        # 1. ML предсказание получено
        setup["ml_manager_mock"].predict.assert_called_once()

        # 2. Динамические уровни рассчитаны
        assert dynamic_levels is not None
        assert "stop_loss_pct" in dynamic_levels
        assert "take_profit_pct" in dynamic_levels
        assert dynamic_levels["volatility_data"]["volatility_regime"] in ["low", "medium", "high"]

        # 3. Торговый сигнал создан с правильными уровнями
        assert trading_signal["stop_loss"] < current_price  # SL ниже для LONG
        assert trading_signal["take_profit"] > current_price  # TP выше для LONG

        # 4. Ордер успешно размещен
        setup["exchange_mock"].place_order.assert_called_once()
        assert order_result["success"] == True
        assert order_result["order_id"] == "TEST_ORDER_123"

        # 5. Метаданные содержат все необходимые поля
        metadata = trading_signal["metadata"]
        assert "dynamic_levels" in metadata
        assert "volatility_data" in metadata
        assert "ml_prediction" in metadata

        print("\n✅ E2E Test Results:")
        print(f"   Symbol: {trading_signal['symbol']}")
        print(f"   Entry Price: ${current_price:.2f}")
        print(
            f"   Dynamic SL: ${trading_signal['stop_loss']:.2f} ({dynamic_levels['stop_loss_pct']:.2f}%)"
        )
        print(
            f"   Dynamic TP: ${trading_signal['take_profit']:.2f} ({dynamic_levels['take_profit_pct']:.2f}%)"
        )
        print(f"   Volatility: {dynamic_levels['volatility_data']['volatility_regime']}")
        print(f"   Risk/Reward: {dynamic_levels['expected_value']['risk_reward_ratio']:.2f}")

    @pytest.mark.asyncio
    async def test_volatility_adaptation_scenario(self, full_system_setup):
        """Тест адаптации к изменению волатильности в реальном времени"""
        setup = await full_system_setup

        # Сценарий 1: Низкая волатильность
        low_vol_data = self._create_market_data_with_volatility("low", 100)

        low_vol_levels = setup["calculator"].calculate_dynamic_levels(
            current_price=50000, candles=low_vol_data, confidence=0.75, signal_type="BUY"
        )

        # Сценарий 2: Резкое увеличение волатильности (новости, events)
        high_vol_data = self._create_market_data_with_volatility("high", 100)

        high_vol_levels = setup["calculator"].calculate_dynamic_levels(
            current_price=50000, candles=high_vol_data, confidence=0.75, signal_type="BUY"
        )

        # Проверки адаптации
        assert low_vol_levels["volatility_data"]["volatility_regime"] == "low"
        assert high_vol_levels["volatility_data"]["volatility_regime"] == "high"

        # При высокой волатильности уровни должны быть шире
        assert high_vol_levels["stop_loss_pct"] > low_vol_levels["stop_loss_pct"]
        assert high_vol_levels["take_profit_pct"] > low_vol_levels["take_profit_pct"]

        print("\n🌊 Volatility Adaptation Test:")
        print(
            f"   Low Vol  - SL: {low_vol_levels['stop_loss_pct']:.2f}%, TP: {low_vol_levels['take_profit_pct']:.2f}%"
        )
        print(
            f"   High Vol - SL: {high_vol_levels['stop_loss_pct']:.2f}%, TP: {high_vol_levels['take_profit_pct']:.2f}%"
        )
        print(
            f"   Adaptation: SL +{high_vol_levels['stop_loss_pct'] - low_vol_levels['stop_loss_pct']:.2f}%, TP +{high_vol_levels['take_profit_pct'] - low_vol_levels['take_profit_pct']:.2f}%"
        )

    @pytest.mark.asyncio
    async def test_partial_tp_execution_flow(self, full_system_setup):
        """Тест выполнения частичных закрытий в реальном времени"""
        setup = await full_system_setup

        # Создаем позицию с динамическими уровнями
        market_data = self._create_market_data_with_volatility("medium", 50)
        current_price = 50000

        dynamic_levels = setup["calculator"].calculate_dynamic_levels(
            current_price=current_price, candles=market_data, confidence=0.8, signal_type="BUY"
        )

        # Симуляция частичных закрытий
        position = {
            "symbol": "BTCUSDT",
            "side": "long",
            "quantity": 0.1,
            "entry_price": current_price,
            "current_pnl": 0,
        }

        # Получаем уровни частичного закрытия
        partial_levels = dynamic_levels["partial_tp_levels"]

        # Симулируем движение цены и срабатывание уровней
        price_movements = [
            current_price * 1.008,  # +0.8% - не достигает первого уровня
            partial_levels[0]["price"],  # Достигает Level 1 (40% от TP)
            partial_levels[1]["price"],  # Достигает Level 2 (70% от TP)
            partial_levels[2]["price"],  # Достигает Level 3 (100% от TP)
        ]

        executed_partials = []
        remaining_quantity = position["quantity"]

        for i, price in enumerate(price_movements):
            # Проверяем какие уровни сработали
            for level in partial_levels:
                if price >= level["price"] and level not in executed_partials:
                    # Рассчитываем количество для закрытия
                    close_qty = position["quantity"] * (level["percent"] / 100)

                    # Мокируем выполнение частичного закрытия
                    setup["exchange_mock"].place_order.return_value = {
                        "success": True,
                        "order_id": f'PARTIAL_{level["percent"]}_{i}',
                        "filled_quantity": close_qty,
                    }

                    executed_partials.append(level)
                    remaining_quantity -= close_qty

                    print(f"   📊 Partial TP {level['percent']}% executed at ${price:.2f}")

        # Проверки
        assert len(executed_partials) > 0, "Should execute at least one partial TP"
        assert remaining_quantity >= 0, "Remaining quantity should be non-negative"

        # Если все уровни сработали, позиция должна быть полностью закрыта
        if len(executed_partials) == 3:
            assert abs(remaining_quantity) < 0.0001, "Position should be fully closed"

        print("\n🎯 Partial TP Execution Results:")
        print(f"   Entry Price: ${current_price:.2f}")
        print(f"   Executed Levels: {len(executed_partials)}/3")
        print(f"   Remaining Quantity: {remaining_quantity:.4f}")

    @pytest.mark.asyncio
    async def test_error_handling_and_fallback(self, full_system_setup):
        """Тест обработки ошибок и fallback на фиксированные уровни"""
        setup = await full_system_setup

        # Сценарий 1: Недостаточно исторических данных
        insufficient_data = pd.DataFrame(
            {
                "timestamp": pd.date_range(start="2024-01-01", periods=5, freq="1min"),
                "open": [50000] * 5,
                "high": [50100] * 5,
                "low": [49900] * 5,
                "close": [50050] * 5,
                "volume": [100] * 5,
            }
        )

        result_insufficient = setup["calculator"].calculate_dynamic_levels(
            current_price=50000, candles=insufficient_data, confidence=0.7, signal_type="BUY"
        )

        # Должен использовать значения по умолчанию
        assert result_insufficient["volatility_data"]["reason"] == "insufficient_data"
        assert result_insufficient["volatility_data"]["volatility_regime"] == "medium"

        # Сценарий 2: Поврежденные данные
        corrupted_data = pd.DataFrame(
            {
                "timestamp": pd.date_range(start="2024-01-01", periods=50, freq="1min"),
                "open": [np.nan] * 50,  # NaN значения
                "high": [50100] * 50,
                "low": [49900] * 50,
                "close": [None] * 50,  # None значения
                "volume": [100] * 50,
            }
        )

        result_corrupted = setup["calculator"].calculate_dynamic_levels(
            current_price=50000, candles=corrupted_data, confidence=0.7, signal_type="BUY"
        )

        # Система должна gracefully обработать ошибки
        assert result_corrupted is not None
        assert result_corrupted["stop_loss_pct"] > 0
        assert result_corrupted["take_profit_pct"] > 0

        print("\n🛠️  Error Handling Test:")
        print(
            f"   Insufficient data fallback: {result_insufficient['volatility_data']['volatility_regime']}"
        )
        print(
            f"   Corrupted data recovery: SL={result_corrupted['stop_loss_pct']:.2f}%, TP={result_corrupted['take_profit_pct']:.2f}%"
        )

    def _create_market_data_with_volatility(
        self, volatility_level: str, periods: int
    ) -> pd.DataFrame:
        """Создание тестовых данных с заданной волатильностью"""
        dates = pd.date_range(start="2024-01-01", periods=periods, freq="1min")

        # Параметры волатильности
        volatility_params = {
            "low": {"std": 0.001, "range": 0.002},
            "medium": {"std": 0.005, "range": 0.01},
            "high": {"std": 0.015, "range": 0.03},
        }

        params = volatility_params[volatility_level]
        base_price = 50000
        prices = []

        for i in range(periods):
            change = np.random.normal(0, params["std"])
            price = base_price * (1 + change)

            prices.append(
                {
                    "timestamp": dates[i],
                    "open": price,
                    "high": price * (1 + params["range"] / 2),
                    "low": price * (1 - params["range"] / 2),
                    "close": price * (1 + np.random.normal(0, params["std"] / 2)),
                    "volume": np.random.uniform(100, 1000),
                }
            )

        return pd.DataFrame(prices)
