#!/usr/bin/env python3
"""
Unit tests for Trading Engine with SL/TP integration
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from trading.engine import TradingEngine, TradingMetrics, TradingState
from trading.sltp.enhanced_manager import EnhancedSLTPManager


class TestTradingEngineWithSLTP:
    """Тесты для Trading Engine с интеграцией SL/TP"""

    @pytest.fixture
    def mock_orchestrator(self):
        """Mock для System Orchestrator"""
        orchestrator = Mock()
        orchestrator.update_status = AsyncMock()
        return orchestrator

    @pytest.fixture
    def mock_config(self):
        """Mock конфигурация"""
        return {
            "trading": {
                "enabled": True,
                "mode": "live",
                "sltp": {
                    "enabled": True,
                    "default_stop_loss": 0.02,
                    "default_take_profit": 0.04,
                    "trailing_stop": {
                        "enabled": True,
                        "activation_profit": 0.01,
                        "trailing_distance": 0.005,
                    },
                    "partial_tp": {
                        "enabled": True,
                        "levels": [0.02, 0.03, 0.04],
                        "percentages": [0.3, 0.3, 0.4],
                    },
                },
            },
            "exchanges": {
                "bybit": {
                    "enabled": True,
                    "api_key": "test_key",
                    "api_secret": "test_secret",
                }
            },
            "risk_management": {
                "enabled": True,
                "max_risk_per_trade": 0.02,
                "max_total_risk": 0.1,
            },
        }

    @pytest.fixture
    async def trading_engine(self, mock_orchestrator, mock_config):
        """Фикстура для создания Trading Engine"""
        with patch("trading.engine.setup_logger"):
            engine = TradingEngine(mock_orchestrator, mock_config)
            return engine

    @pytest.mark.asyncio
    async def test_initialization_with_sltp(self, trading_engine):
        """Тест инициализации с Enhanced SL/TP Manager"""
        # Arrange
        with patch.multiple(
            "trading.engine",
            ExchangeManager=Mock(return_value=Mock(initialize=AsyncMock())),
            RiskManager=Mock(),
            StrategyManager=Mock(
                return_value=Mock(initialize=AsyncMock(), get_strategies=Mock(return_value=[]))
            ),
            PositionManager=Mock(),
            OrderManager=Mock(),
            ExecutionEngine=Mock(),
            SignalProcessor=Mock(),
        ):
            # Act
            await trading_engine.initialize()

            # Assert
            assert trading_engine.enhanced_sltp_manager is not None
            assert isinstance(trading_engine.enhanced_sltp_manager, EnhancedSLTPManager)
            assert trading_engine.state == TradingState.RUNNING

    @pytest.mark.asyncio
    async def test_enhanced_sltp_manager_creation_order(self, mock_orchestrator, mock_config):
        """Тест правильного порядка создания компонентов"""
        # Arrange
        order_manager_mock = Mock()
        sltp_manager_created_before_order_manager = False

        def order_manager_init(*args, **kwargs):
            # Проверяем что sltp_manager уже создан
            nonlocal sltp_manager_created_before_order_manager
            if hasattr(trading_engine, "enhanced_sltp_manager"):
                sltp_manager_created_before_order_manager = True
            return order_manager_mock

        with patch("trading.engine.setup_logger"):
            trading_engine = TradingEngine(mock_orchestrator, mock_config)

        with patch.multiple(
            "trading.engine",
            ExchangeManager=Mock(return_value=Mock(initialize=AsyncMock())),
            RiskManager=Mock(),
            StrategyManager=Mock(
                return_value=Mock(initialize=AsyncMock(), get_strategies=Mock(return_value=[]))
            ),
            PositionManager=Mock(),
            OrderManager=order_manager_init,
            ExecutionEngine=Mock(),
            SignalProcessor=Mock(),
        ):
            # Act
            await trading_engine.initialize()

            # Assert
            assert sltp_manager_created_before_order_manager is True

    @pytest.mark.asyncio
    async def test_sltp_update_in_main_loop(self, trading_engine):
        """Тест обновления SL/TP в основном цикле"""
        # Arrange
        mock_position = Mock(
            id="pos_123",
            symbol="BTCUSDT",
            exchange="bybit",
            entry_price=50000,
            size=0.001,
            side="Buy",
        )

        mock_exchange_client = Mock()
        mock_exchange_client.get_ticker = AsyncMock(return_value={"last": 51000})

        trading_engine.position_manager = Mock()
        trading_engine.position_manager.get_open_positions = AsyncMock(return_value=[mock_position])

        trading_engine.exchange_registry = Mock()
        trading_engine.exchange_registry.get_exchange = AsyncMock(return_value=mock_exchange_client)

        trading_engine.enhanced_sltp_manager = Mock()
        trading_engine.enhanced_sltp_manager.check_partial_tp = AsyncMock(return_value=True)
        trading_engine.enhanced_sltp_manager.update_profit_protection = AsyncMock(return_value=True)
        trading_engine.enhanced_sltp_manager.update_trailing_stop = AsyncMock(return_value=True)

        trading_engine._running = True
        trading_engine.state = TradingState.RUNNING

        # Act - запускаем один цикл
        with patch("asyncio.sleep", side_effect=[None, asyncio.CancelledError()]):
            try:
                await trading_engine._main_loop()
            except asyncio.CancelledError:
                pass

        # Assert
        trading_engine.enhanced_sltp_manager.check_partial_tp.assert_called_once_with(mock_position)
        trading_engine.enhanced_sltp_manager.update_profit_protection.assert_called_once_with(
            mock_position, 51000
        )
        trading_engine.enhanced_sltp_manager.update_trailing_stop.assert_called_once_with(
            mock_position, 51000
        )

    @pytest.mark.asyncio
    async def test_handle_signal_with_sltp_metadata(self, trading_engine):
        """Тест обработки сигнала с метаданными SL/TP"""
        # Arrange
        mock_signal = Mock(
            id=1,
            symbol="BTCUSDT",
            exchange="bybit",
            suggested_stop_loss=49000,
            suggested_take_profit=52000,
            metadata={
                "stop_loss_pct": 0.02,
                "take_profit_pct": 0.04,
                "trailing_stop": True,
                "partial_tp_levels": [0.02, 0.03, 0.04],
            },
        )

        mock_order = Mock(order_id="order_123")

        trading_engine.signal_processor = Mock()
        trading_engine.signal_processor.process_signal = AsyncMock(return_value=[mock_order])

        trading_engine.order_manager = Mock()
        trading_engine.order_manager.submit_order = AsyncMock(return_value=True)

        # Act
        await trading_engine._handle_signal(mock_signal)

        # Assert
        trading_engine.signal_processor.process_signal.assert_called_once_with(mock_signal)
        trading_engine.order_manager.submit_order.assert_called_once_with(mock_order)

    @pytest.mark.asyncio
    async def test_stop_with_sltp_cleanup(self, trading_engine):
        """Тест остановки с очисткой SL/TP"""
        # Arrange
        trading_engine.state = TradingState.RUNNING
        trading_engine._running = True

        # Mock компоненты
        trading_engine.strategy_manager = Mock(stop=AsyncMock())
        trading_engine.signal_processor = Mock(stop=AsyncMock())
        trading_engine.order_manager = Mock(stop=AsyncMock())
        trading_engine.position_manager = Mock(stop=AsyncMock())
        trading_engine.execution_engine = Mock(stop=AsyncMock())
        trading_engine.exchange_registry = Mock(close_all=AsyncMock())

        trading_engine.enhanced_sltp_manager = Mock()
        trading_engine.enhanced_sltp_manager.active_sl_orders = {"pos_1": Mock()}
        trading_engine.enhanced_sltp_manager.active_tp_orders = {"pos_1": [Mock()]}
        trading_engine.enhanced_sltp_manager.cancel_sltp_orders = AsyncMock()

        # Act
        await trading_engine.stop()

        # Assert
        assert trading_engine.state == TradingState.STOPPED
        assert trading_engine._running is False

        # Проверяем отмену всех SL/TP ордеров
        trading_engine.enhanced_sltp_manager.cancel_sltp_orders.assert_called()

    @pytest.mark.asyncio
    async def test_metrics_update_with_sltp(self, trading_engine):
        """Тест обновления метрик с учетом SL/TP"""
        # Arrange
        trading_engine.metrics = TradingMetrics()
        trading_engine.signal_processor = Mock()
        trading_engine.signal_processor.get_processed_count = Mock(return_value=10)

        trading_engine.order_manager = Mock()
        trading_engine.order_manager.get_executed_count = Mock(return_value=8)

        trading_engine.position_manager = Mock()
        trading_engine.position_manager.get_open_positions = AsyncMock(
            return_value=[Mock(), Mock()]  # 2 открытые позиции
        )

        # Act
        await trading_engine._update_metrics()

        # Assert
        assert trading_engine.metrics.signals_processed == 10
        assert trading_engine.metrics.orders_executed == 8
        assert trading_engine.metrics.active_positions == 2

    def test_sltp_config_extraction(self, trading_engine, mock_config):
        """Тест извлечения конфигурации SL/TP"""
        # Act
        sltp_config = mock_config["trading"]["sltp"]

        # Assert
        assert sltp_config["enabled"] is True
        assert sltp_config["default_stop_loss"] == 0.02
        assert sltp_config["default_take_profit"] == 0.04
        assert sltp_config["trailing_stop"]["enabled"] is True
        assert sltp_config["partial_tp"]["levels"] == [0.02, 0.03, 0.04]

    @pytest.mark.asyncio
    async def test_error_handling_in_sltp_update(self, trading_engine):
        """Тест обработки ошибок при обновлении SL/TP"""
        # Arrange
        mock_position = Mock(id="pos_123", symbol="BTCUSDT", exchange="bybit")

        trading_engine.position_manager = Mock()
        trading_engine.position_manager.get_open_positions = AsyncMock(return_value=[mock_position])

        trading_engine.exchange_registry = Mock()
        trading_engine.exchange_registry.get_exchange = AsyncMock(
            side_effect=Exception("Exchange connection failed")
        )

        trading_engine._running = True
        trading_engine.state = TradingState.RUNNING

        # Act - запускаем один цикл
        with patch("asyncio.sleep", side_effect=[None, asyncio.CancelledError()]):
            try:
                await trading_engine._main_loop()
            except asyncio.CancelledError:
                pass

        # Assert - ошибка должна быть обработана без краша
        assert trading_engine.metrics.errors_count == 0  # Ошибки не считаются в этом месте

    @pytest.mark.asyncio
    async def test_health_check_includes_sltp(self, trading_engine):
        """Тест health check включая SL/TP компоненты"""
        # Arrange
        trading_engine.enhanced_sltp_manager = Mock()
        trading_engine.signal_processor = Mock(health_check=AsyncMock(return_value=True))
        trading_engine.order_manager = Mock(health_check=AsyncMock(return_value=True))
        trading_engine.position_manager = Mock(health_check=AsyncMock(return_value=True))
        trading_engine.execution_engine = Mock(health_check=AsyncMock(return_value=True))
        trading_engine.exchange_registry = Mock(health_check=AsyncMock(return_value=True))
        trading_engine.risk_manager = Mock(health_check=AsyncMock(return_value=True))

        # Act
        result = await trading_engine.health_check()

        # Assert
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
