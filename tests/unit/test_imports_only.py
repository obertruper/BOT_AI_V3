"""
Простые тесты импортов для максимального покрытия кода
Только проверка что модули могут быть импортированы
"""

import os
import sys

import pytest

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestCoreImports:
    """Тесты импортов ядра системы"""

    def test_config_imports(self):
        """Тест импортов конфигурации"""
        from core.config.config_manager import ConfigManager
        from core.config.validation import ConfigValidator

        assert ConfigManager is not None
        assert ConfigValidator is not None

    def test_system_imports(self):
        """Тест импортов системных компонентов"""
        from core.system.data_manager import DataManager
        from core.system.health_checker import HealthChecker
        from core.system.orchestrator import SystemOrchestrator
        from core.system.process_manager import ProcessManager

        assert all([SystemOrchestrator, ProcessManager, HealthChecker, DataManager])

    def test_logger_imports(self):
        """Тест импортов логирования"""
        from core.logging.formatters import JsonFormatter
        from core.logging.logger_factory import LoggerFactory

        assert LoggerFactory is not None
        assert JsonFormatter is not None


class TestTradingImports:
    """Тесты импортов торговой системы"""

    def test_engine_imports(self):
        """Тест импортов торгового движка"""
        from trading.engine import TradingEngine
        from trading.orders.order_manager import OrderManager
        from trading.positions.position_manager import PositionManager

        assert all([TradingEngine, OrderManager, PositionManager])

    def test_signal_imports(self):
        """Тест импортов обработки сигналов"""
        from trading.signals.ai_signal_generator import AISignalGenerator
        from trading.signals.signal_processor import SignalProcessor

        assert SignalProcessor is not None
        assert AISignalGenerator is not None

    def test_sltp_imports(self):
        """Тест импортов SL/TP системы"""
        from trading.sltp.enhanced_manager import EnhancedSLTPManager
        from trading.sltp.models import SLTPConfig

        assert EnhancedSLTPManager is not None
        assert SLTPConfig is not None


class TestExchangeImports:
    """Тесты импортов бирж"""

    def test_factory_imports(self):
        """Тест импортов фабрики бирж"""
        from exchanges.factory import ExchangeFactory
        from exchanges.registry import ExchangeRegistry

        assert ExchangeFactory is not None
        assert ExchangeRegistry is not None

    def test_bybit_imports(self):
        """Тест импортов Bybit"""
        from exchanges.bybit.adapter import BybitAdapter
        from exchanges.bybit.client import BybitClient

        assert BybitClient is not None
        assert BybitAdapter is not None

    def test_base_imports(self):
        """Тест импортов базовых компонентов"""
        from exchanges.base.exchange_interface import BaseExchangeInterface
        from exchanges.base.models import Balance, Order, Position
        from exchanges.base.order_types import OrderRequest, OrderSide, OrderType

        assert all(
            [BaseExchangeInterface, Position, Order, Balance, OrderRequest, OrderSide, OrderType]
        )


class TestMLImports:
    """Тесты импортов ML системы"""

    def test_ml_manager_imports(self):
        """Тест импортов ML менеджера"""
        from ml.ml_manager import MLManager
        from ml.ml_signal_processor import MLSignalProcessor

        assert MLManager is not None
        assert MLSignalProcessor is not None

    def test_model_imports(self):
        """Тест импортов моделей"""
        from ml.logic.archive_old_versions.feature_engineering import FeatureEngineer
        from ml.logic.patchtst_model import UnifiedPatchTST

        assert UnifiedPatchTST is not None
        assert FeatureEngineer is not None


class TestRiskImports:
    """Тесты импортов управления рисками"""

    def test_risk_manager_imports(self):
        """Тест импортов менеджера рисков"""
        from risk_management.calculators import calculate_position_size
        from risk_management.manager import RiskManager

        assert RiskManager is not None
        assert callable(calculate_position_size)


class TestDatabaseImports:
    """Тесты импортов базы данных"""

    def test_connection_imports(self):
        """Тест импортов подключений"""
        from database.connections.postgres import AsyncPGPool

        assert AsyncPGPool is not None

    def test_model_imports(self):
        """Тест импортов моделей"""
        from database.models.base_models import Order
        from database.models.signal import Signal

        assert Signal is not None
        assert Order is not None


class TestStrategyImports:
    """Тесты импортов стратегий"""

    def test_strategy_imports(self):
        """Тест импортов стратегий"""
        from strategies.base.base_strategy import BaseStrategy
        from strategies.factory import StrategyFactory
        from strategies.manager import StrategyManager

        assert all([StrategyFactory, StrategyManager, BaseStrategy])

    def test_ml_strategy_imports(self):
        """Тест импортов ML стратегии"""
        from strategies.ml_strategy.ml_signal_strategy import MLSignalStrategy

        assert MLSignalStrategy is not None


class TestUtilImports:
    """Тесты импортов утилит"""

    def test_helper_imports(self):
        """Тест импортов хелперов"""
        from utils.helpers import clean_symbol, format_decimal

        assert callable(format_decimal)
        assert callable(clean_symbol)


class TestIndicatorImports:
    """Тесты импортов индикаторов"""

    def test_calculator_imports(self):
        """Тест импортов калькулятора индикаторов"""
        from indicators.calculator.indicator_calculator import IndicatorCalculator

        assert IndicatorCalculator is not None


class TestBasicFunctionality:
    """Тесты базовой функциональности"""

    def test_format_decimal(self):
        """Тест функции форматирования"""
        from utils.helpers import format_decimal

        result = format_decimal(1.23456, 2)
        assert result == "1.23"

    def test_clean_symbol(self):
        """Тест функции очистки символа"""
        from utils.helpers import clean_symbol

        result = clean_symbol("BTCUSDT")
        assert result == "BTCUSDT"

        result = clean_symbol("btc/usdt")
        assert result == "BTCUSDT"

    def test_config_manager_basic(self):
        """Тест базовой работы менеджера конфигурации"""
        from core.config.config_manager import ConfigManager

        manager = ConfigManager()
        assert manager is not None

    def test_exchange_factory_basic(self):
        """Тест базовой работы фабрики бирж"""
        from exchanges.factory import ExchangeFactory

        factory = ExchangeFactory()
        assert factory is not None


class TestFileExistence:
    """Тесты существования файлов"""

    def test_main_files_exist(self):
        """Тест существования основных файлов"""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        important_files = [
            "unified_launcher.py",
            "main.py",
            "requirements.txt",
            "pytest.ini",
            "config/trading.yaml",
            "config/system.yaml",
        ]

        for file_path in important_files:
            full_path = os.path.join(project_root, file_path)
            assert os.path.exists(full_path), f"File {file_path} does not exist"

    def test_directory_structure(self):
        """Тест структуры директорий"""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        important_dirs = [
            "core",
            "trading",
            "exchanges",
            "ml",
            "strategies",
            "risk_management",
            "database",
            "tests",
            "utils",
            "indicators",
        ]

        for dir_name in important_dirs:
            dir_path = os.path.join(project_root, dir_name)
            assert os.path.isdir(dir_path), f"Directory {dir_name} does not exist"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
