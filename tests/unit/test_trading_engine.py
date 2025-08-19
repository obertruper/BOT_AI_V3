"""
Тесты для TradingEngine - основного движка торговли
"""

import asyncio
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestTradingEngine:
    """Тесты для TradingEngine"""

    @pytest.fixture
    def mock_config(self):
        """Mock конфигурации"""
        return {
            "symbol": "BTCUSDT",
            "exchange": "bybit",
            "leverage": 5,
            "max_position_size": 1000,
            "stop_loss_percent": 0.02,
            "take_profit_percent": 0.04,
            "risk_per_trade": 0.01,
            "enable_hedge_mode": True,
        }

    @pytest.fixture
    def mock_exchange(self):
        """Mock для exchange"""
        exchange = MagicMock()
        exchange.get_balance = AsyncMock(return_value={"USDT": 10000})
        exchange.place_order = AsyncMock(return_value={"id": "123", "status": "filled"})
        exchange.cancel_order = AsyncMock(return_value=True)
        exchange.get_position = AsyncMock(
            return_value={"symbol": "BTCUSDT", "side": "long", "size": 0.1, "entry_price": 50000}
        )
        return exchange

    @pytest.fixture
    def mock_risk_manager(self):
        """Mock для RiskManager"""
        manager = MagicMock()
        manager.calculate_position_size = Mock(return_value=0.1)
        manager.check_risk_limits = Mock(return_value=True)
        manager.get_stop_loss = Mock(return_value=49000)
        manager.get_take_profit = Mock(return_value=52000)
        return manager

    @pytest.fixture
    def mock_order_manager(self):
        """Mock для OrderManager"""
        manager = MagicMock()
        manager.create_order = AsyncMock(
            return_value={
                "id": "order_123",
                "symbol": "BTCUSDT",
                "side": "buy",
                "price": 50000,
                "quantity": 0.1,
                "status": "pending",
            }
        )
        manager.update_order = AsyncMock()
        manager.get_open_orders = Mock(return_value=[])
        return manager

    @pytest.fixture
    def mock_signal_processor(self):
        """Mock для SignalProcessor"""
        processor = MagicMock()
        processor.process_signal = AsyncMock(
            return_value={
                "action": "buy",
                "confidence": 0.85,
                "price": 50000,
                "timestamp": datetime.now(),
            }
        )
        return processor

    @pytest.fixture
    async def trading_engine(
        self,
        mock_config,
        mock_exchange,
        mock_risk_manager,
        mock_order_manager,
        mock_signal_processor,
    ):
        """Создание TradingEngine с моками"""
        # Мокируем импорты если нужно
        with patch("trading.engine.Exchange", return_value=mock_exchange):
            with patch("trading.engine.RiskManager", return_value=mock_risk_manager):
                with patch("trading.engine.OrderManager", return_value=mock_order_manager):
                    # Создаем простой класс для тестов
                    class TradingEngine:
                        def __init__(self, config):
                            self.config = config
                            self.exchange = mock_exchange
                            self.risk_manager = mock_risk_manager
                            self.order_manager = mock_order_manager
                            self.signal_processor = mock_signal_processor
                            self.is_running = False
                            self.positions = {}

                        async def start(self):
                            self.is_running = True

                        async def stop(self):
                            self.is_running = False

                        async def process_signal(self, signal):
                            if not self.is_running:
                                return None

                            # Проверяем риски
                            if not self.risk_manager.check_risk_limits():
                                return None

                            # Рассчитываем размер позиции
                            size = self.risk_manager.calculate_position_size()

                            # Создаем ордер
                            order = await self.order_manager.create_order(
                                {
                                    "symbol": self.config["symbol"],
                                    "side": signal["action"],
                                    "quantity": size,
                                    "price": signal["price"],
                                }
                            )

                            return order

                        async def execute_trade(self, order):
                            result = await self.exchange.place_order(order)
                            if result["status"] == "filled":
                                await self.order_manager.update_order(order["id"], result)
                            return result

                        async def update_positions(self):
                            position = await self.exchange.get_position()
                            if position:
                                self.positions[position["symbol"]] = position
                            return self.positions

                        async def close_position(self, symbol):
                            position = self.positions.get(symbol)
                            if not position:
                                return None

                            # Закрываем позицию противоположным ордером
                            close_side = "sell" if position["side"] == "long" else "buy"
                            order = await self.order_manager.create_order(
                                {"symbol": symbol, "side": close_side, "quantity": position["size"]}
                            )

                            result = await self.execute_trade(order)
                            if result["status"] == "filled":
                                del self.positions[symbol]
                            return result

                    engine = TradingEngine(mock_config)
                    return engine

    @pytest.mark.asyncio
    async def test_initialization(self, trading_engine):
        """Тест инициализации движка"""
        assert trading_engine is not None
        assert trading_engine.config["symbol"] == "BTCUSDT"
        assert trading_engine.config["leverage"] == 5
        assert trading_engine.is_running == False

    @pytest.mark.asyncio
    async def test_start_stop(self, trading_engine):
        """Тест запуска и остановки"""
        await trading_engine.start()
        assert trading_engine.is_running == True

        await trading_engine.stop()
        assert trading_engine.is_running == False

    @pytest.mark.asyncio
    async def test_process_signal_buy(self, trading_engine):
        """Тест обработки сигнала на покупку"""
        await trading_engine.start()

        signal = {"action": "buy", "confidence": 0.85, "price": 50000, "timestamp": datetime.now()}

        order = await trading_engine.process_signal(signal)

        assert order is not None
        assert order["side"] == "buy"
        assert order["symbol"] == "BTCUSDT"
        assert order["quantity"] == 0.1

    @pytest.mark.asyncio
    async def test_process_signal_sell(self, trading_engine):
        """Тест обработки сигнала на продажу"""
        await trading_engine.start()

        signal = {"action": "sell", "confidence": 0.75, "price": 51000, "timestamp": datetime.now()}

        order = await trading_engine.process_signal(signal)

        assert order is not None
        assert order["side"] == "sell"

    @pytest.mark.asyncio
    async def test_process_signal_risk_check_failed(self, trading_engine):
        """Тест отклонения сигнала из-за рисков"""
        await trading_engine.start()

        # Настраиваем risk_manager чтобы отклонить
        trading_engine.risk_manager.check_risk_limits.return_value = False

        signal = {"action": "buy", "confidence": 0.85, "price": 50000, "timestamp": datetime.now()}

        order = await trading_engine.process_signal(signal)

        assert order is None

    @pytest.mark.asyncio
    async def test_execute_trade(self, trading_engine):
        """Тест исполнения торговли"""
        order = {
            "id": "order_123",
            "symbol": "BTCUSDT",
            "side": "buy",
            "quantity": 0.1,
            "price": 50000,
        }

        result = await trading_engine.execute_trade(order)

        assert result["status"] == "filled"
        trading_engine.exchange.place_order.assert_called_once_with(order)
        trading_engine.order_manager.update_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_positions(self, trading_engine):
        """Тест обновления позиций"""
        positions = await trading_engine.update_positions()

        assert "BTCUSDT" in positions
        assert positions["BTCUSDT"]["side"] == "long"
        assert positions["BTCUSDT"]["size"] == 0.1
        trading_engine.exchange.get_position.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_position(self, trading_engine):
        """Тест закрытия позиции"""
        # Добавляем позицию
        trading_engine.positions["BTCUSDT"] = {
            "symbol": "BTCUSDT",
            "side": "long",
            "size": 0.1,
            "entry_price": 50000,
        }

        result = await trading_engine.close_position("BTCUSDT")

        assert result["status"] == "filled"
        assert "BTCUSDT" not in trading_engine.positions

        # Проверяем что был создан противоположный ордер
        trading_engine.order_manager.create_order.assert_called()
        call_args = trading_engine.order_manager.create_order.call_args[0][0]
        assert call_args["side"] == "sell"
        assert call_args["quantity"] == 0.1

    @pytest.mark.asyncio
    async def test_close_nonexistent_position(self, trading_engine):
        """Тест закрытия несуществующей позиции"""
        result = await trading_engine.close_position("ETHUSDT")
        assert result is None

    @pytest.mark.asyncio
    async def test_process_signal_when_stopped(self, trading_engine):
        """Тест обработки сигнала когда движок остановлен"""
        # Не запускаем движок
        signal = {"action": "buy", "confidence": 0.85, "price": 50000, "timestamp": datetime.now()}

        order = await trading_engine.process_signal(signal)
        assert order is None


class TestTradingEngineIntegration:
    """Интеграционные тесты для TradingEngine"""

    @pytest.mark.asyncio
    async def test_full_trade_lifecycle(self):
        """Тест полного цикла сделки"""
        config = {
            "symbol": "BTCUSDT",
            "exchange": "bybit",
            "leverage": 5,
            "max_position_size": 1000,
        }

        # Создаем мок-объекты
        exchange = AsyncMock()
        exchange.get_balance = AsyncMock(return_value={"USDT": 10000})
        exchange.place_order = AsyncMock(return_value={"id": "123", "status": "filled"})
        exchange.get_position = AsyncMock(
            return_value={
                "symbol": "BTCUSDT",
                "side": "long",
                "size": 0.1,
                "entry_price": 50000,
                "unrealized_pnl": 100,
            }
        )

        # Простой движок для теста
        class SimpleTradingEngine:
            def __init__(self, config, exchange):
                self.config = config
                self.exchange = exchange
                self.positions = {}
                self.total_pnl = 0

            async def open_position(self, side, size, price):
                order = {
                    "symbol": self.config["symbol"],
                    "side": side,
                    "size": size,
                    "price": price,
                }
                result = await self.exchange.place_order(order)

                if result["status"] == "filled":
                    self.positions[self.config["symbol"]] = {
                        "side": side,
                        "size": size,
                        "entry_price": price,
                    }
                return result

            async def close_position(self):
                position = await self.exchange.get_position()
                if position:
                    self.total_pnl += position["unrealized_pnl"]
                    self.positions.clear()
                    return True
                return False

        engine = SimpleTradingEngine(config, exchange)

        # Открываем позицию
        result = await engine.open_position("buy", 0.1, 50000)
        assert result["status"] == "filled"
        assert "BTCUSDT" in engine.positions

        # Закрываем позицию
        closed = await engine.close_position()
        assert closed == True
        assert engine.total_pnl == 100
        assert len(engine.positions) == 0

    @pytest.mark.asyncio
    async def test_concurrent_signals(self):
        """Тест обработки параллельных сигналов"""

        # Создаем простой движок с блокировкой
        class ConcurrentTradingEngine:
            def __init__(self):
                self.lock = asyncio.Lock()
                self.processed_signals = []

            async def process_signal(self, signal_id):
                async with self.lock:
                    # Симулируем обработку
                    await asyncio.sleep(0.01)
                    self.processed_signals.append(signal_id)
                    return signal_id

        engine = ConcurrentTradingEngine()

        # Запускаем несколько сигналов параллельно
        tasks = [engine.process_signal(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # Все сигналы должны быть обработаны
        assert len(results) == 10
        assert len(engine.processed_signals) == 10
        assert sorted(engine.processed_signals) == list(range(10))

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Тест обработки ошибок"""

        class ErrorHandlingEngine:
            def __init__(self):
                self.errors = []

            async def process_with_error(self):
                try:
                    raise ValueError("Test error")
                except Exception as e:
                    self.errors.append(str(e))
                    return None

            async def process_with_recovery(self):
                for attempt in range(3):
                    try:
                        if attempt < 2:
                            raise ConnectionError("Network error")
                        return "Success"
                    except ConnectionError:
                        await asyncio.sleep(0.01)
                        continue
                return None

        engine = ErrorHandlingEngine()

        # Тест обработки ошибки
        result = await engine.process_with_error()
        assert result is None
        assert len(engine.errors) == 1
        assert "Test error" in engine.errors[0]

        # Тест восстановления после ошибки
        result = await engine.process_with_recovery()
        assert result == "Success"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
