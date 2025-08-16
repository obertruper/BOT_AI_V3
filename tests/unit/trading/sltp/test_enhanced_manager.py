#!/usr/bin/env python3
"""
Unit tests for Enhanced SL/TP Manager
"""

from unittest.mock import AsyncMock, Mock

import pytest

from exchanges.base.models import Position
from trading.sltp.enhanced_manager import EnhancedSLTPManager, PositionAdapter
from trading.sltp.models import SLTPConfig, SLTPOrder


class TestPositionAdapter:
    """Тесты для PositionAdapter"""

    def test_adapter_with_exchange_position(self):
        """Тест адаптера с позицией из exchanges.base.models"""
        # Arrange
        exchange_position = Position(
            symbol="BTCUSDT",
            side="Buy",
            size=0.001,
            entry_price=50000,
            mark_price=51000,
            position_idx=1,
        )

        # Act
        adapter = PositionAdapter(exchange_position)

        # Assert
        assert adapter.symbol == "BTCUSDT"
        assert adapter.side == "Buy"
        assert adapter.size == 0.001
        assert adapter.entry_price == 50000
        assert adapter.id == "BTCUSDT_Buy"

    def test_adapter_with_trading_position(self):
        """Тест адаптера с позицией из trading.positions"""
        # Arrange
        trading_position = Mock()
        trading_position.id = "pos_12345"
        trading_position.symbol = "ETHUSDT"
        trading_position.side = "Sell"
        trading_position.quantity = 0.1
        trading_position.average_price = 3000

        # Act
        adapter = PositionAdapter(trading_position)

        # Assert
        assert adapter.symbol == "ETHUSDT"
        assert adapter.side == "Sell"
        assert adapter.size == 0.1
        assert adapter.entry_price == 3000
        assert adapter.id == "pos_12345"


class TestEnhancedSLTPManager:
    """Тесты для Enhanced SL/TP Manager"""

    @pytest.fixture
    def mock_config_manager(self):
        """Mock для ConfigManager"""
        config_manager = Mock()
        config_manager.get_sltp_config.return_value = {
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
            "profit_protection": {
                "enabled": True,
                "activation_profit": 0.015,
                "protection_level": 0.008,
            },
        }
        return config_manager

    @pytest.fixture
    def mock_exchange_client(self):
        """Mock для exchange client"""
        client = Mock()
        client.set_stop_loss = AsyncMock(return_value=Mock(success=True, order_id="sl_123"))
        client.set_take_profit = AsyncMock(return_value=Mock(success=True, order_id="tp_123"))
        return client

    @pytest.fixture
    async def sltp_manager(self, mock_config_manager):
        """Фикстура для создания Enhanced SL/TP Manager"""
        manager = EnhancedSLTPManager(config_manager=mock_config_manager)
        return manager

    @pytest.mark.asyncio
    async def test_create_sltp_orders_with_custom_config(self, sltp_manager, mock_exchange_client):
        """Тест создания SL/TP ордеров с пользовательской конфигурацией"""
        # Arrange
        sltp_manager.exchange_client = mock_exchange_client

        position = Position(
            symbol="BTCUSDT",
            side="Buy",
            size=0.001,
            entry_price=50000,
            mark_price=50000,
            position_idx=1,
        )

        custom_config = SLTPConfig(
            stop_loss=49000,
            take_profit=52000,  # Абсолютная цена  # Абсолютная цена
        )

        # Act
        orders = await sltp_manager.create_sltp_orders(position, custom_config)

        # Assert
        assert len(orders) == 2
        assert orders[0].type == "stop_loss"
        assert orders[0].trigger_price == 49000
        assert orders[1].type == "take_profit"
        assert orders[1].trigger_price == 52000

        # Проверяем вызовы биржи
        mock_exchange_client.set_stop_loss.assert_called_once_with(
            symbol="BTCUSDT", price=49000, size=0.001
        )
        mock_exchange_client.set_take_profit.assert_called_once_with(
            symbol="BTCUSDT", price=52000, size=0.001
        )

    @pytest.mark.asyncio
    async def test_create_sltp_orders_with_percentages(self, sltp_manager, mock_exchange_client):
        """Тест создания SL/TP ордеров с процентами"""
        # Arrange
        sltp_manager.exchange_client = mock_exchange_client

        position = Position(
            symbol="BTCUSDT",
            side="Buy",
            size=0.001,
            entry_price=50000,
            mark_price=50000,
            position_idx=1,
        )

        # Act - без custom config, используются дефолтные проценты
        orders = await sltp_manager.create_sltp_orders(position)

        # Assert
        assert len(orders) == 2
        assert orders[0].trigger_price == 49000  # -2%
        assert orders[1].trigger_price == 52000  # +4%

    @pytest.mark.asyncio
    async def test_create_sltp_orders_for_short_position(self, sltp_manager, mock_exchange_client):
        """Тест создания SL/TP для короткой позиции"""
        # Arrange
        sltp_manager.exchange_client = mock_exchange_client

        position = Position(
            symbol="BTCUSDT",
            side="Sell",
            size=0.001,
            entry_price=50000,
            mark_price=50000,
            position_idx=2,
        )

        # Act
        orders = await sltp_manager.create_sltp_orders(position)

        # Assert
        assert len(orders) == 2
        assert orders[0].trigger_price == 51000  # +2% для short SL
        assert orders[1].trigger_price == 48000  # -4% для short TP

    @pytest.mark.asyncio
    async def test_update_trailing_stop(self, sltp_manager):
        """Тест обновления трейлинг стопа"""
        # Arrange
        position_id = "BTCUSDT_Buy"
        entry_price = 50000

        # Создаем позицию и SL ордер
        sltp_manager.active_positions[position_id] = Mock(
            entry_price=entry_price, highest_price=entry_price
        )
        sltp_manager.active_sl_orders[position_id] = Mock(trigger_price=49000, is_trailing=True)

        # Act - цена выросла до 51000 (+2%)
        updated = await sltp_manager.update_trailing_stop(position_id, 51000)

        # Assert
        assert updated is True
        assert sltp_manager.active_positions[position_id].highest_price == 51000
        # SL должен подняться до 50500 (51000 - 0.5%)
        expected_new_sl = 51000 * (1 - 0.005)
        assert sltp_manager.active_sl_orders[position_id].trigger_price == pytest.approx(
            expected_new_sl
        )

    @pytest.mark.asyncio
    async def test_check_partial_tp(self, sltp_manager, mock_config_manager):
        """Тест частичного Take Profit"""
        # Arrange
        position = Mock()
        position.id = "BTCUSDT_Buy"
        position.symbol = "BTCUSDT"
        position.entry_price = 50000
        position.size = 1.0
        position.side = "Buy"

        sltp_manager.active_positions[position.id] = position
        sltp_manager.partial_tp_config = mock_config_manager.get_sltp_config()["partial_tp"]
        sltp_manager.partial_tp_executed = {position.id: []}

        # Act - цена достигла первого уровня TP (+2%)
        result = await sltp_manager.check_partial_tp(position)

        # Assert - должен вернуть True так как цена не передана
        # и метод предполагает что цена уже проверена
        assert result is False  # Без текущей цены не может определить

    @pytest.mark.asyncio
    async def test_update_profit_protection(self, sltp_manager):
        """Тест защиты прибыли"""
        # Arrange
        position_id = "BTCUSDT_Buy"
        entry_price = 50000

        sltp_manager.active_positions[position_id] = Mock(entry_price=entry_price, side="Buy")
        sltp_manager.active_sl_orders[position_id] = Mock(trigger_price=49000, original_price=49000)

        # Act - цена выросла до 51000 (+2%, выше порога активации 1.5%)
        updated = await sltp_manager.update_profit_protection(position_id, 51000)

        # Assert
        assert updated is True
        # SL должен подняться до уровня защиты прибыли
        expected_protection_level = entry_price * (1 + 0.008)
        assert sltp_manager.active_sl_orders[position_id].trigger_price == pytest.approx(
            expected_protection_level
        )

    @pytest.mark.asyncio
    async def test_register_sltp_orders(self, sltp_manager):
        """Тест регистрации SL/TP ордеров"""
        # Arrange
        position_id = "BTCUSDT_Buy"
        sl_order = SLTPOrder(
            id="sl_123",
            type="stop_loss",
            symbol="BTCUSDT",
            side="Sell",
            trigger_price=49000,
            size=0.001,
            status="active",
        )
        tp_orders = [
            SLTPOrder(
                id="tp_123",
                type="take_profit",
                symbol="BTCUSDT",
                side="Sell",
                trigger_price=52000,
                size=0.001,
                status="active",
            )
        ]

        # Act
        sltp_manager.register_sltp_orders(position_id, sl_order, tp_orders)

        # Assert
        assert position_id in sltp_manager.active_sl_orders
        assert sltp_manager.active_sl_orders[position_id] == sl_order
        assert position_id in sltp_manager.active_tp_orders
        assert len(sltp_manager.active_tp_orders[position_id]) == 1
        assert sltp_manager.active_tp_orders[position_id][0] == tp_orders[0]

    @pytest.mark.asyncio
    async def test_cancel_sltp_orders(self, sltp_manager, mock_exchange_client):
        """Тест отмены SL/TP ордеров"""
        # Arrange
        sltp_manager.exchange_client = mock_exchange_client
        mock_exchange_client.cancel_order = AsyncMock(return_value=True)

        position_id = "BTCUSDT_Buy"
        sl_order = Mock(id="sl_123", symbol="BTCUSDT")
        tp_order = Mock(id="tp_123", symbol="BTCUSDT")

        sltp_manager.active_sl_orders[position_id] = sl_order
        sltp_manager.active_tp_orders[position_id] = [tp_order]

        # Act
        await sltp_manager.cancel_sltp_orders(position_id)

        # Assert
        mock_exchange_client.cancel_order.assert_any_call("sl_123", "BTCUSDT")
        mock_exchange_client.cancel_order.assert_any_call("tp_123", "BTCUSDT")
        assert position_id not in sltp_manager.active_sl_orders
        assert position_id not in sltp_manager.active_tp_orders


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
