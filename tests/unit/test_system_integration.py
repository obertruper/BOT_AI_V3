#!/usr/bin/env python3
"""
Интеграционные тесты для всей системы BOT_AI_V3
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.config.config_manager import ConfigManager
from core.system.orchestrator import SystemOrchestrator
from database.connections.postgres import AsyncPGPool
from exchanges.factory import ExchangeFactory
from ml.logic.patchtst_model import UnifiedPatchTST
from trading.engine import TradingEngine


class TestSystemIntegration:
    """Тесты интеграции системы"""

    @pytest.fixture
    async def config_manager(self):
        """Фикстура для ConfigManager"""
        config = ConfigManager()
        await config.initialize()
        return config

    @pytest.fixture
    async def exchange_factory(self):
        """Фикстура для ExchangeFactory"""
        return ExchangeFactory()

    @pytest.fixture
    async def db_pool(self):
        """Фикстура для подключения к БД"""
        await AsyncPGPool.get_pool()
        yield AsyncPGPool
        await AsyncPGPool.close_pool()

    @pytest.mark.asyncio
    async def test_config_manager_initialization(self, config_manager):
        """Тест инициализации ConfigManager"""
        assert config_manager is not None
        assert hasattr(config_manager, "config")
        assert "trading" in config_manager.config

    @pytest.mark.asyncio
    async def test_exchange_factory_creation(self, exchange_factory):
        """Тест создания ExchangeFactory"""
        assert exchange_factory is not None
        assert hasattr(exchange_factory, "create_client")
        assert hasattr(exchange_factory, "create_exchange")

    @pytest.mark.asyncio
    async def test_ml_model_import(self):
        """Тест импорта ML модели"""
        assert UnifiedPatchTST is not None
        assert hasattr(UnifiedPatchTST, "__init__")

    @pytest.mark.asyncio
    async def test_database_connection(self, db_pool):
        """Тест подключения к базе данных"""
        result = await db_pool.fetch("SELECT 1 as test")
        assert result[0]["test"] == 1

    @pytest.mark.asyncio
    async def test_trading_engine_creation(self, config_manager):
        """Тест создания TradingEngine"""
        with patch("trading.engine.ExchangeRegistry") as mock_registry:
            mock_registry.return_value = AsyncMock()
            engine = TradingEngine(config_manager)
            assert engine is not None
            assert hasattr(engine, "process_signal")

    @pytest.mark.asyncio
    async def test_system_orchestrator_initialization(self, config_manager):
        """Тест инициализации SystemOrchestrator"""
        with patch("core.system.orchestrator.ExchangeRegistry") as mock_registry:
            mock_registry.return_value = AsyncMock()
            orchestrator = SystemOrchestrator(config_manager)
            await orchestrator.initialize()
            assert orchestrator is not None
            assert hasattr(orchestrator, "trader_manager")


class TestTradingOperations:
    """Тесты торговых операций"""

    @pytest.mark.asyncio
    async def test_signal_processing(self):
        """Тест обработки сигналов"""
        from trading.signals.signal_processor import SignalProcessor

        processor = SignalProcessor()
        assert processor is not None
        assert hasattr(processor, "process_signal")

    @pytest.mark.asyncio
    async def test_order_creation(self):
        """Тест создания ордеров"""
        from trading.orders.order_manager import OrderManager

        manager = OrderManager()
        assert manager is not None
        assert hasattr(manager, "create_order_from_signal")

    @pytest.mark.asyncio
    async def test_position_management(self):
        """Тест управления позициями"""
        from trading.positions.position_manager import PositionManager

        manager = PositionManager()
        assert manager is not None
        assert hasattr(manager, "get_positions")


class TestRiskManagement:
    """Тесты управления рисками"""

    @pytest.mark.asyncio
    async def test_risk_calculator(self):
        """Тест калькулятора рисков"""
        from risk_management.calculators import RiskCalculator

        calculator = RiskCalculator()
        assert calculator is not None
        assert hasattr(calculator, "calculate_position_size")

    @pytest.mark.asyncio
    async def test_sltp_manager(self):
        """Тест менеджера SL/TP"""
        from trading.sltp.sltp_manager import SLTPManager

        manager = SLTPManager()
        assert manager is not None
        assert hasattr(manager, "set_stop_loss")


class TestMLSystem:
    """Тесты ML системы"""

    @pytest.mark.asyncio
    async def test_ml_signal_processor(self):
        """Тест ML обработчика сигналов"""
        from ml.ml_signal_processor import MLSignalProcessor

        processor = MLSignalProcessor()
        assert processor is not None
        assert hasattr(processor, "process_ml_signal")

    @pytest.mark.asyncio
    async def test_feature_engineering(self):
        """Тест инженерии признаков"""
        from ml.logic.feature_engineering_v2 import FeatureEngineeringV2

        fe = FeatureEngineeringV2()
        assert fe is not None
        assert hasattr(fe, "calculate_features")


class TestDatabaseOperations:
    """Тесты операций с базой данных"""

    @pytest.mark.asyncio
    async def test_signal_storage(self, db_pool):
        """Тест сохранения сигналов"""
        # Тест создания сигнала
        signal_data = {
            "symbol": "BTCUSDT",
            "signal_type": "LONG",
            "strength": 0.7,
            "confidence": 0.8,
        }

        insert_query = """
        INSERT INTO signals (symbol, signal_type, strength, confidence)
        VALUES ($1, $2, $3, $4)
        RETURNING id
        """

        result = await db_pool.fetchrow(
            insert_query,
            signal_data["symbol"],
            signal_data["signal_type"],
            signal_data["strength"],
            signal_data["confidence"],
        )

        assert result is not None
        assert "id" in result

        # Очистка тестовых данных
        await db_pool.execute("DELETE FROM signals WHERE id = $1", result["id"])

    @pytest.mark.asyncio
    async def test_order_storage(self, db_pool):
        """Тест сохранения ордеров"""
        order_data = {
            "exchange": "bybit",
            "symbol": "ETHUSDT",
            "order_id": "test_order_123",
            "side": "BUY",
            "order_type": "LIMIT",
            "status": "PENDING",
            "quantity": 0.1,
            "price": 2500.0,
        }

        insert_query = """
        INSERT INTO orders (exchange, symbol, order_id, side, order_type, status, quantity, price)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """

        result = await db_pool.fetchrow(
            insert_query,
            order_data["exchange"],
            order_data["symbol"],
            order_data["order_id"],
            order_data["side"],
            order_data["order_type"],
            order_data["status"],
            order_data["quantity"],
            order_data["price"],
        )

        assert result is not None
        assert "id" in result

        # Очистка тестовых данных
        await db_pool.execute("DELETE FROM orders WHERE id = $1", result["id"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
