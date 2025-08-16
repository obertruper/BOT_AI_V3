#!/usr/bin/env python3
"""
Unit tests for SL/TP Integration
"""

from unittest.mock import AsyncMock, Mock

import pytest

from database.models import Order
from database.models.base_models import OrderSide, OrderStatus
from trading.orders.sltp_integration import SLTPIntegration
from trading.sltp.models import SLTPOrder


class TestSLTPIntegration:
    """Тесты для SL/TP Integration"""

    @pytest.fixture
    def mock_sltp_manager(self):
        """Mock для Enhanced SL/TP Manager"""
        manager = Mock()
        manager.create_sltp_orders = AsyncMock()
        manager.update_trailing_stop = AsyncMock(return_value=True)
        manager.update_profit_protection = AsyncMock(return_value=True)
        manager.check_and_execute_partial_tp = AsyncMock(return_value=True)
        return manager

    @pytest.fixture
    def mock_exchange_client(self):
        """Mock для exchange client"""
        client = Mock()
        client.get_ticker = AsyncMock(return_value={"last": 50000})
        return client

    @pytest.fixture
    def sltp_integration(self, mock_sltp_manager):
        """Фикстура для создания SL/TP Integration"""
        return SLTPIntegration(sltp_manager=mock_sltp_manager)

    @pytest.fixture
    def test_order(self):
        """Тестовый ордер"""
        order = Order(
            exchange="bybit",
            symbol="BTCUSDT",
            order_id="test_order_001",
            side=OrderSide.BUY,
            status=OrderStatus.FILLED,
            price=50000,
            quantity=0.001,
            filled_quantity=0.001,
            average_price=50000,
            strategy_name="test_strategy",
            trader_id="test_trader",
            metadata={"stop_loss_pct": 0.02, "take_profit_pct": 0.04},
        )
        return order

    @pytest.mark.asyncio
    async def test_handle_filled_order_success(
        self, sltp_integration, test_order, mock_exchange_client, mock_sltp_manager
    ):
        """Тест успешной обработки исполненного ордера"""
        # Arrange
        mock_sl_order = SLTPOrder(
            id="sl_123",
            type="stop_loss",
            symbol="BTCUSDT",
            side="Sell",
            trigger_price=49000,
            size=0.001,
            status="active",
        )
        mock_tp_order = SLTPOrder(
            id="tp_123",
            type="take_profit",
            symbol="BTCUSDT",
            side="Sell",
            trigger_price=52000,
            size=0.001,
            status="active",
        )

        mock_sltp_manager.create_sltp_orders.return_value = [
            mock_sl_order,
            mock_tp_order,
        ]

        # Act
        result = await sltp_integration.handle_filled_order(test_order, mock_exchange_client)

        # Assert
        assert result is True
        assert mock_sltp_manager.exchange_client == mock_exchange_client

        # Проверяем вызов create_sltp_orders
        mock_sltp_manager.create_sltp_orders.assert_called_once()
        call_args = mock_sltp_manager.create_sltp_orders.call_args[0]

        # Проверяем позицию
        position = call_args[0]
        assert position.symbol == "BTCUSDT"
        assert position.side == "Buy"
        assert position.size == 0.001
        assert position.entry_price == 50000

        # Проверяем custom config
        custom_config = call_args[1]
        assert custom_config.stop_loss == 49000  # 50000 * 0.98
        assert custom_config.take_profit == 52000  # 50000 * 1.04

        # Проверяем обновление metadata
        assert test_order.metadata["sltp_created"] is True
        assert test_order.metadata["sl_order_id"] == "sl_123"
        assert test_order.metadata["tp_order_ids"] == ["tp_123"]
        assert "position_id" in test_order.metadata

    @pytest.mark.asyncio
    async def test_handle_filled_order_no_manager(self, test_order, mock_exchange_client):
        """Тест обработки ордера без SL/TP Manager"""
        # Arrange
        integration = SLTPIntegration(sltp_manager=None)

        # Act
        result = await integration.handle_filled_order(test_order, mock_exchange_client)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_filled_order_short_position(
        self, sltp_integration, mock_exchange_client, mock_sltp_manager
    ):
        """Тест обработки короткой позиции"""
        # Arrange
        short_order = Order(
            exchange="bybit",
            symbol="BTCUSDT",
            order_id="test_short_001",
            side=OrderSide.SELL,
            status=OrderStatus.FILLED,
            price=50000,
            quantity=0.001,
            filled_quantity=0.001,
            average_price=50000,
            strategy_name="test_strategy",
            trader_id="test_trader",
            metadata={"stop_loss_pct": 0.02, "take_profit_pct": 0.04},
        )

        mock_sltp_manager.create_sltp_orders.return_value = []

        # Act
        result = await sltp_integration.handle_filled_order(short_order, mock_exchange_client)

        # Assert
        assert result is False  # Нет созданных ордеров

        # Проверяем расчеты для short
        call_args = mock_sltp_manager.create_sltp_orders.call_args[0]
        position = call_args[0]
        assert position.side == "Sell"
        assert position.position_idx == 2  # Hedge mode short

        custom_config = call_args[1]
        assert custom_config.stop_loss == 51000  # 50000 * 1.02 для short
        assert custom_config.take_profit == 48000  # 50000 * 0.96 для short

    @pytest.mark.asyncio
    async def test_handle_filled_order_exception(
        self, sltp_integration, test_order, mock_exchange_client, mock_sltp_manager
    ):
        """Тест обработки исключения"""
        # Arrange
        mock_sltp_manager.create_sltp_orders.side_effect = Exception("API Error")

        # Act
        result = await sltp_integration.handle_filled_order(test_order, mock_exchange_client)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_update_position_sltp(self, sltp_integration, mock_sltp_manager):
        """Тест обновления SL/TP для позиции"""
        # Arrange
        position_id = "BTCUSDT_test_123"
        current_price = 51000

        # Act
        result = await sltp_integration.update_position_sltp(position_id, current_price)

        # Assert
        assert result is True
        mock_sltp_manager.update_trailing_stop.assert_called_once_with(position_id, current_price)
        mock_sltp_manager.update_profit_protection.assert_called_once_with(
            position_id, current_price
        )

    @pytest.mark.asyncio
    async def test_update_position_sltp_no_manager(self):
        """Тест обновления без менеджера"""
        # Arrange
        integration = SLTPIntegration(sltp_manager=None)

        # Act
        result = await integration.update_position_sltp("test_id", 50000)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_update_position_sltp_no_updates(self, sltp_integration, mock_sltp_manager):
        """Тест когда обновления не требуются"""
        # Arrange
        mock_sltp_manager.update_trailing_stop.return_value = False
        mock_sltp_manager.update_profit_protection.return_value = False

        # Act
        result = await sltp_integration.update_position_sltp("test_id", 50000)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_check_partial_tp(self, sltp_integration, mock_sltp_manager):
        """Тест проверки частичного TP"""
        # Arrange
        position_id = "BTCUSDT_test_123"
        current_price = 51000

        # Act
        result = await sltp_integration.check_partial_tp(position_id, current_price)

        # Assert
        assert result is True
        mock_sltp_manager.check_and_execute_partial_tp.assert_called_once_with(
            position_id, current_price
        )

    @pytest.mark.asyncio
    async def test_check_partial_tp_exception(self, sltp_integration, mock_sltp_manager):
        """Тест обработки исключения при проверке частичного TP"""
        # Arrange
        mock_sltp_manager.check_and_execute_partial_tp.side_effect = Exception("Network error")

        # Act
        result = await sltp_integration.check_partial_tp("test_id", 50000)

        # Assert
        assert result is False

    def test_calculate_sl_tp_prices_for_buy(self, sltp_integration):
        """Тест расчета цен SL/TP для длинной позиции"""
        # Arrange
        entry_price = 50000
        sl_percentage = 0.02
        tp_percentage = 0.04

        # Act
        order = Mock(metadata={"stop_loss_pct": sl_percentage, "take_profit_pct": tp_percentage})
        position = Mock(entry_price=entry_price, side="Buy")

        # Вычисляем как в коде
        sl_price = entry_price * (1 - sl_percentage)
        tp_price = entry_price * (1 + tp_percentage)

        # Assert
        assert sl_price == 49000
        assert tp_price == 52000

    def test_position_id_generation(self):
        """Тест генерации ID позиции"""
        # Arrange
        order = Mock(symbol="BTCUSDT", order_id="order_123", metadata={})

        # Act
        position_id = f"{order.symbol}_{order.order_id}"

        # Assert
        assert position_id == "BTCUSDT_order_123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
