"""
Тесты системных компонентов BOT_AI_V3
Тесты для процессов, мониторинга и координации
"""

import os
import sys
from unittest.mock import Mock

import pytest

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestSystemHealth:
    """Тесты мониторинга системы"""

    def test_health_checker_import(self):
        """Тест импорта проверки здоровья системы"""
        from core.system.health_checker import HealthChecker

        assert HealthChecker is not None

    def test_health_monitor_import(self):
        """Тест импорта монитора здоровья"""
        from core.system.health_monitor import HealthMonitor

        assert HealthMonitor is not None

    def test_health_checker_creation(self):
        """Тест создания проверки здоровья"""
        from core.system.health_checker import HealthChecker

        checker = HealthChecker()
        assert checker is not None
        assert hasattr(checker, "check_system_health")


class TestProcessManagement:
    """Тесты управления процессами"""

    def test_process_manager_creation(self):
        """Тест создания менеджера процессов"""
        from core.system.process_manager import ProcessManager

        manager = ProcessManager()
        assert manager is not None
        assert hasattr(manager, "start_process")
        assert hasattr(manager, "stop_process")

    def test_process_monitor_import(self):
        """Тест импорта монитора процессов"""
        from core.system.process_monitor import ProcessMonitor

        assert ProcessMonitor is not None


class TestDataManagement:
    """Тесты управления данными"""

    def test_data_manager_import(self):
        """Тест импорта менеджера данных"""
        from core.system.data_manager import DataManager

        assert DataManager is not None

    def test_smart_data_manager_import(self):
        """Тест импорта умного менеджера данных"""
        from core.system.smart_data_manager import SmartDataManager

        assert SmartDataManager is not None


class TestPerformanceComponents:
    """Тесты компонентов производительности"""

    def test_performance_cache_import(self):
        """Тест импорта кеша производительности"""
        from core.system.performance_cache import PerformanceCache

        assert PerformanceCache is not None

    def test_rate_limiter_import(self):
        """Тест импорта ограничителя скорости"""
        from core.system.rate_limiter import RateLimiter

        assert RateLimiter is not None

    def test_rate_limiter_creation(self):
        """Тест создания ограничителя скорости"""
        from core.system.rate_limiter import RateLimiter

        limiter = RateLimiter(max_requests=100, time_window=60)
        assert limiter is not None
        assert hasattr(limiter, "is_allowed")


class TestSignalProcessing:
    """Тесты обработки сигналов"""

    def test_signal_deduplicator_import(self):
        """Тест импорта дедупликатора сигналов"""
        from core.system.signal_deduplicator import SignalDeduplicator

        assert SignalDeduplicator is not None

    def test_unified_signal_processor_import(self):
        """Тест импорта унифицированного процессора сигналов"""
        from core.signals.unified_signal_processor import UnifiedSignalProcessor

        assert UnifiedSignalProcessor is not None


class TestWorkerCoordination:
    """Тесты координации воркеров"""

    def test_worker_coordinator_import(self):
        """Тест импорта координатора воркеров"""
        from core.system.worker_coordinator import WorkerCoordinator

        assert WorkerCoordinator is not None

    def test_balance_manager_import(self):
        """Тест импорта менеджера баланса"""
        from core.system.balance_manager import BalanceManager

        assert BalanceManager is not None


class TestLoggingSystem:
    """Тесты системы логирования"""

    def test_logger_factory_import(self):
        """Тест импорта фабрики логгеров"""
        from core.logging.logger_factory import LoggerFactory

        assert LoggerFactory is not None

    def test_trade_logger_import(self):
        """Тест импорта логгера торгов"""
        from core.logging.trade_logger import TradeLogger

        assert TradeLogger is not None

    def test_formatters_import(self):
        """Тест импорта форматтеров"""
        from core.logging.formatters import JsonFormatter

        assert JsonFormatter is not None


class TestCacheSystem:
    """Тесты системы кеширования"""

    def test_market_data_cache_import(self):
        """Тест импорта кеша рыночных данных"""
        from core.cache.market_data_cache import MarketDataCache

        assert MarketDataCache is not None


class TestTraderComponents:
    """Тесты компонентов трейдеров"""

    def test_trader_factory_import(self):
        """Тест импорта фабрики трейдеров"""
        from core.traders.trader_factory import TraderFactory

        assert TraderFactory is not None

    def test_trader_manager_import(self):
        """Тест импорта менеджера трейдеров"""
        from core.traders.trader_manager import TraderManager

        assert TraderManager is not None

    def test_trader_context_import(self):
        """Тест импорта контекста трейдера"""
        from core.traders.trader_context import TraderContext

        assert TraderContext is not None


class TestSystemOrchestrator:
    """Тесты системного оркестратора"""

    def test_orchestrator_creation(self):
        """Тест создания оркестратора"""
        from core.system.orchestrator import SystemOrchestrator

        mock_config = Mock()
        orchestrator = SystemOrchestrator(config=mock_config)
        assert orchestrator is not None
        assert hasattr(orchestrator, "start_system")
        assert hasattr(orchestrator, "stop_system")


class TestExchangeComponents:
    """Тесты компонентов бирж"""

    def test_api_key_manager_import(self):
        """Тест импорта менеджера API ключей"""
        from exchanges.base.api_key_manager import APIKeyManager

        assert APIKeyManager is not None

    def test_enhanced_rate_limiter_import(self):
        """Тест импорта расширенного ограничителя скорости"""
        from exchanges.base.enhanced_rate_limiter import EnhancedRateLimiter

        assert EnhancedRateLimiter is not None

    def test_health_monitor_import(self):
        """Тест импорта монитора здоровья биржи"""
        from exchanges.base.health_monitor import ExchangeHealthMonitor

        assert ExchangeHealthMonitor is not None


class TestMLComponents:
    """Тесты ML компонентов"""

    def test_ml_manager_creation(self):
        """Тест создания ML менеджера"""
        from ml.ml_manager import MLManager

        mock_config = Mock()
        ml_manager = MLManager(config=mock_config)
        assert ml_manager is not None
        assert hasattr(ml_manager, "get_prediction")

    def test_signal_scheduler_import(self):
        """Тест импорта планировщика сигналов"""
        from ml.signal_scheduler import SignalScheduler

        assert SignalScheduler is not None


class TestStrategyComponents:
    """Тесты компонентов стратегий"""

    def test_strategy_factory_import(self):
        """Тест импорта фабрики стратегий"""
        from strategies.factory import StrategyFactory

        assert StrategyFactory is not None

    def test_strategy_manager_import(self):
        """Тест импорта менеджера стратегий"""
        from strategies.manager import StrategyManager

        assert StrategyManager is not None

    def test_strategy_registry_import(self):
        """Тест импорта реестра стратегий"""
        from strategies.registry import StrategyRegistry

        assert StrategyRegistry is not None


class TestBaseStrategy:
    """Тесты базовой стратегии"""

    def test_base_strategy_import(self):
        """Тест импорта базовой стратегии"""
        from strategies.base.base_strategy import BaseStrategy

        assert BaseStrategy is not None

    def test_strategy_abc_import(self):
        """Тест импорта ABC стратегии"""
        from strategies.base.strategy_abc import StrategyABC

        assert StrategyABC is not None


class TestMLStrategy:
    """Тесты ML стратегии"""

    def test_ml_signal_strategy_import(self):
        """Тест импорта ML стратегии сигналов"""
        from strategies.ml_strategy.ml_signal_strategy import MLSignalStrategy

        assert MLSignalStrategy is not None


class TestNotifications:
    """Тесты системы уведомлений"""

    def test_telegram_service_import(self):
        """Тест импорта Telegram сервиса"""
        try:
            from notifications.telegram.telegram_service import TelegramService

            assert TelegramService is not None
        except ImportError:
            pytest.skip("Telegram service may not be available")


class TestMonitoring:
    """Тесты системы мониторинга"""

    def test_telegram_bot_import(self):
        """Тест импорта Telegram бота"""
        try:
            from monitoring.telegram.bot import TelegramBot

            assert TelegramBot is not None
        except ImportError:
            pytest.skip("Telegram bot may not be available")


@pytest.mark.asyncio
class TestAsyncSystemComponents:
    """Тесты асинхронных системных компонентов"""

    async def test_async_orchestrator_methods(self):
        """Тест асинхронных методов оркестратора"""
        from core.system.orchestrator import SystemOrchestrator

        mock_config = Mock()
        orchestrator = SystemOrchestrator(config=mock_config)

        # Проверяем что есть асинхронные методы
        assert hasattr(orchestrator, "start_system")

    async def test_async_health_monitoring(self):
        """Тест асинхронного мониторинга здоровья"""
        from core.system.health_monitor import HealthMonitor

        monitor = HealthMonitor()
        assert monitor is not None


class TestUnifiedLauncher:
    """Тесты главного запускателя"""

    def test_unified_launcher_import(self):
        """Тест импорта unified_launcher"""
        # Просто проверяем что файл существует и может быть импортирован
        import importlib.util
        import os

        launcher_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "unified_launcher.py"
        )

        assert os.path.exists(launcher_path)

        # Попытаемся загрузить модуль
        spec = importlib.util.spec_from_file_location("unified_launcher", launcher_path)
        assert spec is not None


class TestWebIntegration:
    """Тесты веб интеграции"""

    def test_web_integration_import(self):
        """Тест импорта веб интеграции"""
        from web.integration.web_integration import WebIntegration

        assert WebIntegration is not None

    def test_web_orchestrator_bridge_import(self):
        """Тест импорта моста веб-оркестратора"""
        from web.integration.web_orchestrator_bridge import WebOrchestratorBridge

        assert WebOrchestratorBridge is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
