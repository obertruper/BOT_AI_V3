#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Order Manager with SL/TP integration
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from database.models import Order
from database.models.base_models import OrderSide, OrderStatus, OrderType, SignalType
from database.models.signal import Signal
from trading.orders.order_manager import OrderManager
from trading.orders.sltp_integration import SLTPIntegration


class TestOrderManagerWithSLTP:
    """Тесты для Order Manager с интеграцией SL/TP"""

    @pytest.fixture
    def mock_exchange_registry(self):
        """Mock для Exchange Registry"""
        registry = Mock()
        registry.get_exchange = AsyncMock()
        return registry

    @pytest.fixture
    def mock_sltp_manager(self):
        """Mock для Enhanced SL/TP Manager"""
        manager = Mock()
        manager.create_sltp_orders = AsyncMock()
        return manager

    @pytest.fixture
    def order_manager(self, mock_exchange_registry, mock_sltp_manager):
        """Фикстура для создания Order Manager с SL/TP"""
        return OrderManager(
            exchange_registry=mock_exchange_registry, sltp_manager=mock_sltp_manager
        )

    @pytest.fixture
    def test_signal(self):
        """Тестовый торговый сигнал"""
        signal = Signal(
            id=1,
            strategy_name="test_strategy",
            symbol="BTCUSDT",
            exchange="bybit",
            signal_type=SignalType.LONG,
            strength=0.8,
            confidence=0.9,
            suggested_price=50000,
            suggested_quantity=0.001,
            suggested_stop_loss=49000,
            suggested_take_profit=52000,
        )
        return signal

    @pytest.fixture
    def test_order(self):
        """Тестовый ордер"""
        order = Order(
            exchange="bybit",
            symbol="BTCUSDT",
            order_id="test_order_001",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            status=OrderStatus.OPEN,
            price=50000,
            quantity=0.001,
            strategy_name="test_strategy",
            trader_id="test_trader",
        )
        return order

    @pytest.mark.asyncio
    async def test_init_with_sltp_manager(
        self, mock_exchange_registry, mock_sltp_manager
    ):
        """Тест инициализации с SL/TP Manager"""
        # Act
        order_manager = OrderManager(
            exchange_registry=mock_exchange_registry, sltp_manager=mock_sltp_manager
        )

        # Assert
        assert order_manager.sltp_integration is not None
        assert isinstance(order_manager.sltp_integration, SLTPIntegration)
        assert order_manager.sltp_integration.sltp_manager == mock_sltp_manager

    @pytest.mark.asyncio
    async def test_init_without_sltp_manager(self, mock_exchange_registry):
        """Тест инициализации без SL/TP Manager"""
        # Act
        order_manager = OrderManager(
            exchange_registry=mock_exchange_registry, sltp_manager=None
        )

        # Assert
        assert order_manager.sltp_integration is None

    @pytest.mark.asyncio
    async def test_create_order_from_signal(self, order_manager, test_signal):
        """Тест создания ордера из сигнала"""
        # Arrange
        with patch("trading.orders.order_manager.get_async_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_db

            # Act
            order = await order_manager.create_order_from_signal(
                test_signal, "test_trader"
            )

            # Assert
            assert order is not None
            assert order.symbol == "BTCUSDT"
            assert order.side == OrderSide.BUY
            assert order.price == 50000
            assert order.quantity == 0.001
            assert order.stop_loss == 49000
            assert order.take_profit == 52000
            assert order.order_id in order_manager._active_orders

            # Проверяем сохранение в БД
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_order_status_to_filled_with_sltp(
        self, order_manager, test_order, mock_exchange_registry
    ):
        """Тест обновления статуса на FILLED с созданием SL/TP"""
        # Arrange
        order_manager._active_orders[test_order.order_id] = test_order
        order_manager._order_locks[test_order.order_id] = asyncio.Lock()

        mock_exchange = Mock()
        mock_exchange_registry.get_exchange.return_value = mock_exchange

        # Mock SL/TP integration
        order_manager.sltp_integration.handle_filled_order = AsyncMock(
            return_value=True
        )

        with patch("trading.orders.order_manager.get_async_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_db

            # Act
            await order_manager.update_order_status(
                order_id=test_order.order_id,
                new_status=OrderStatus.FILLED,
                filled_quantity=0.001,
                average_price=50000,
            )

            # Assert
            assert test_order.status == OrderStatus.FILLED
            assert test_order.filled_quantity == 0.001
            assert test_order.average_price == 50000
            assert test_order.filled_at is not None

            # Проверяем вызов SL/TP integration
            order_manager.sltp_integration.handle_filled_order.assert_called_once_with(
                test_order, mock_exchange
            )

            # Проверяем удаление из активных
            assert test_order.order_id not in order_manager._active_orders

    @pytest.mark.asyncio
    async def test_update_order_status_to_filled_without_sltp(
        self, mock_exchange_registry
    ):
        """Тест обновления статуса без SL/TP Manager"""
        # Arrange
        order_manager = OrderManager(
            exchange_registry=mock_exchange_registry, sltp_manager=None
        )

        test_order = Order(
            exchange="bybit",
            symbol="BTCUSDT",
            order_id="test_order_002",
            side=OrderSide.BUY,
            status=OrderStatus.OPEN,
            price=50000,
            quantity=0.001,
            strategy_name="test_strategy",
            trader_id="test_trader",
        )

        order_manager._active_orders[test_order.order_id] = test_order
        order_manager._order_locks[test_order.order_id] = asyncio.Lock()

        with patch("trading.orders.order_manager.get_async_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_db

            # Act
            await order_manager.update_order_status(
                order_id=test_order.order_id,
                new_status=OrderStatus.FILLED,
                filled_quantity=0.001,
                average_price=50000,
            )

            # Assert
            assert test_order.status == OrderStatus.FILLED
            # SL/TP не должно вызываться
            assert order_manager.sltp_integration is None

    @pytest.mark.asyncio
    async def test_submit_order_success(self, order_manager, test_order):
        """Тест успешной отправки ордера"""
        # Arrange
        order_manager._active_orders[test_order.order_id] = test_order
        order_manager._order_locks[test_order.order_id] = asyncio.Lock()

        with patch("trading.orders.order_manager.ExchangeFactory") as MockFactory:
            mock_factory = Mock()
            MockFactory.return_value = mock_factory

            mock_exchange = Mock()
            mock_exchange.initialize = AsyncMock()
            mock_exchange.place_order = AsyncMock(
                return_value=Mock(success=True, order_id="exchange_order_123")
            )

            mock_factory.create_and_connect = AsyncMock(return_value=mock_exchange)

            with patch("trading.orders.order_manager.get_async_db") as mock_get_db:
                mock_db = AsyncMock()
                mock_get_db.return_value.__aenter__.return_value = mock_db

                with patch.dict(
                    "os.environ",
                    {"BYBIT_API_KEY": "test_key", "BYBIT_API_SECRET": "test_secret"},
                ):
                    # Act
                    result = await order_manager.submit_order(test_order)

                    # Assert
                    assert result is True
                    assert test_order.order_id == "exchange_order_123"
                    assert test_order.status == OrderStatus.OPEN
                    mock_exchange.place_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_order(
        self, order_manager, test_order, mock_exchange_registry
    ):
        """Тест отмены ордера"""
        # Arrange
        order_manager._active_orders[test_order.order_id] = test_order
        order_manager._order_locks[test_order.order_id] = asyncio.Lock()

        mock_exchange = Mock()
        mock_exchange.cancel_order = AsyncMock(return_value=True)
        mock_exchange_registry.get_exchange.return_value = mock_exchange

        with patch("trading.orders.order_manager.get_async_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_db

            # Act
            result = await order_manager.cancel_order(test_order.order_id)

            # Assert
            assert result is True
            assert test_order.status == OrderStatus.CANCELLED
            assert test_order.order_id not in order_manager._active_orders
            mock_exchange.cancel_order.assert_called_once_with(
                test_order.order_id, test_order.symbol
            )

    @pytest.mark.asyncio
    async def test_get_active_orders_filtered(self, order_manager):
        """Тест получения активных ордеров с фильтрацией"""
        # Arrange
        order1 = Mock(order_id="1", exchange="bybit", symbol="BTCUSDT")
        order2 = Mock(order_id="2", exchange="binance", symbol="BTCUSDT")
        order3 = Mock(order_id="3", exchange="bybit", symbol="ETHUSDT")

        order_manager._active_orders = {"1": order1, "2": order2, "3": order3}

        # Act - фильтр по бирже
        bybit_orders = await order_manager.get_active_orders(exchange="bybit")

        # Assert
        assert len(bybit_orders) == 2
        assert order1 in bybit_orders
        assert order3 in bybit_orders

        # Act - фильтр по символу
        btc_orders = await order_manager.get_active_orders(symbol="BTCUSDT")

        # Assert
        assert len(btc_orders) == 2
        assert order1 in btc_orders
        assert order2 in btc_orders

    @pytest.mark.asyncio
    async def test_sync_orders_with_exchange(
        self, order_manager, mock_exchange_registry
    ):
        """Тест синхронизации ордеров с биржей"""
        # Arrange
        test_order = Mock(
            order_id="test_123",
            exchange="bybit",
            symbol="BTCUSDT",
            status=OrderStatus.OPEN,
        )

        order_manager._active_orders = {"test_123": test_order}

        mock_exchange = Mock()
        mock_exchange.get_open_orders = AsyncMock(
            return_value=[
                {
                    "id": "test_123",
                    "status": "filled",
                    "filled": 0.001,
                    "average_price": 50000,
                }
            ]
        )
        mock_exchange_registry.get_exchange.return_value = mock_exchange

        order_manager.update_order_status = AsyncMock()

        # Act
        await order_manager.sync_orders_with_exchange("bybit")

        # Assert
        order_manager.update_order_status.assert_called_once_with(
            "test_123", OrderStatus.FILLED, 0.001, 50000
        )

    def test_get_order_side_mapping(self, order_manager):
        """Тест маппинга типов сигналов на стороны ордеров"""
        # Test mappings
        assert order_manager._get_order_side(SignalType.LONG) == OrderSide.BUY
        assert order_manager._get_order_side(SignalType.SHORT) == OrderSide.SELL
        assert order_manager._get_order_side(SignalType.CLOSE_LONG) == OrderSide.SELL
        assert order_manager._get_order_side(SignalType.CLOSE_SHORT) == OrderSide.BUY

    def test_generate_order_id(self, order_manager):
        """Тест генерации уникального ID ордера"""
        # Act
        order_id1 = order_manager._generate_order_id()
        order_id2 = order_manager._generate_order_id()

        # Assert
        assert order_id1 != order_id2
        assert order_id1.startswith("BOT_")
        assert len(order_id1.split("_")) == 3

    def test_map_exchange_status(self, order_manager):
        """Тест маппинга статусов биржи"""
        # Test mappings
        assert order_manager._map_exchange_status("new") == OrderStatus.OPEN
        assert order_manager._map_exchange_status("open") == OrderStatus.OPEN
        assert (
            order_manager._map_exchange_status("partially_filled")
            == OrderStatus.PARTIALLY_FILLED
        )
        assert order_manager._map_exchange_status("filled") == OrderStatus.FILLED
        assert order_manager._map_exchange_status("canceled") == OrderStatus.CANCELLED
        assert order_manager._map_exchange_status("rejected") == OrderStatus.REJECTED
        assert order_manager._map_exchange_status("expired") == OrderStatus.EXPIRED
        assert (
            order_manager._map_exchange_status("unknown") == OrderStatus.OPEN
        )  # default


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
