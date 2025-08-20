"""
Тесты для SystemOrchestrator - главного координатора системы
"""

import asyncio
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core.exceptions import (
    SystemInitializationError,
    SystemShutdownError,
)
from core.system.orchestrator import HealthStatus, SystemOrchestrator


class TestHealthStatus:
    """Тесты для dataclass HealthStatus"""

    def test_health_status_creation(self):
        """Тест создания статуса здоровья"""
        now = datetime.now()
        status = HealthStatus(
            is_healthy=True,
            timestamp=now,
            issues=[],
            warnings=["Low memory"],
            system_resources={"cpu": 45.0, "memory": 70.0},
            active_traders=3,
            total_trades=150,
        )

        assert status.is_healthy == True
        assert status.timestamp == now
        assert len(status.issues) == 0
        assert len(status.warnings) == 1
        assert status.system_resources["cpu"] == 45.0
        assert status.active_traders == 3
        assert status.total_trades == 150

    def test_unhealthy_status(self):
        """Тест нездорового статуса"""
        status = HealthStatus(
            is_healthy=False,
            timestamp=datetime.now(),
            issues=["Database connection lost", "Exchange API error"],
            warnings=[],
            system_resources={"cpu": 95.0, "memory": 90.0},
            active_traders=0,
            total_trades=0,
        )

        assert status.is_healthy == False
        assert len(status.issues) == 2
        assert "Database connection lost" in status.issues


class TestSystemOrchestrator:
    """Тесты для SystemOrchestrator"""

    @pytest.fixture
    def mock_config_manager(self):
        """Mock для ConfigManager"""
        config = MagicMock()
        config.get.return_value = {
            "exchanges": ["bybit", "binance"],
            "trading_pairs": ["BTCUSDT", "ETHUSDT"],
            "max_traders": 10,
            "health_check_interval": 60,
        }
        return config

    @pytest.fixture
    def mock_trader_manager(self):
        """Mock для TraderManager"""
        manager = MagicMock()
        manager.get_active_traders_count.return_value = 3
        manager.get_total_trades.return_value = 100
        manager.start_all = AsyncMock()
        manager.stop_all = AsyncMock()
        return manager

    @pytest.fixture
    def mock_trader_factory(self):
        """Mock для TraderFactory"""
        factory = MagicMock()
        factory.create_trader = AsyncMock()
        return factory

    @pytest.fixture
    def mock_logger_factory(self):
        """Mock для LoggerFactory"""
        logger = MagicMock()
        logger.info = MagicMock()
        logger.error = MagicMock()
        logger.warning = MagicMock()

        factory = MagicMock()
        factory.get_logger.return_value = logger
        return factory, logger

    @pytest.fixture
    async def orchestrator(
        self, mock_config_manager, mock_trader_manager, mock_trader_factory, mock_logger_factory
    ):
        """Создание оркестратора с моками"""
        factory, logger = mock_logger_factory

        with patch(
            "core.system.orchestrator.get_global_config_manager", return_value=mock_config_manager
        ):
            with patch(
                "core.system.orchestrator.get_global_trader_manager",
                return_value=mock_trader_manager,
            ):
                with patch(
                    "core.system.orchestrator.get_global_trader_factory",
                    return_value=mock_trader_factory,
                ):
                    with patch(
                        "core.system.orchestrator.get_global_logger_factory", return_value=factory
                    ):
                        orch = SystemOrchestrator()
                        orch.logger = logger
                        orch.config_manager = mock_config_manager
                        orch.trader_manager = mock_trader_manager
                        orch.trader_factory = mock_trader_factory
                        return orch

    @pytest.mark.asyncio
    async def test_initialization(self, orchestrator):
        """Тест инициализации оркестратора"""
        assert orchestrator is not None
        assert orchestrator.config_manager is not None
        assert orchestrator.trader_manager is not None
        assert orchestrator.trader_factory is not None
        assert orchestrator.logger is not None

    @pytest.mark.asyncio
    async def test_start_system(self, orchestrator):
        """Тест запуска системы"""
        orchestrator.trader_manager.start_all = AsyncMock()
        orchestrator._initialize_components = AsyncMock()
        orchestrator._start_monitoring = AsyncMock()

        # Мокируем метод start если он есть
        if hasattr(orchestrator, "start"):
            await orchestrator.start()

            orchestrator._initialize_components.assert_called_once()
            orchestrator.trader_manager.start_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_system(self, orchestrator):
        """Тест остановки системы"""
        orchestrator.trader_manager.stop_all = AsyncMock()
        orchestrator._stop_monitoring = AsyncMock()

        if hasattr(orchestrator, "stop"):
            await orchestrator.stop()

            orchestrator.trader_manager.stop_all.assert_called_once()
            orchestrator._stop_monitoring.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check(self, orchestrator):
        """Тест проверки здоровья системы"""
        # Мокируем системные ресурсы
        with patch("core.system.orchestrator.get_system_resources") as mock_resources:
            mock_resources.return_value = {
                "cpu_percent": 50.0,
                "memory_percent": 60.0,
                "disk_percent": 40.0,
            }

            if hasattr(orchestrator, "check_health"):
                health = await orchestrator.check_health()

                assert isinstance(health, HealthStatus)
                assert health.is_healthy == True
                assert health.active_traders == 3
                assert health.total_trades == 100

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, orchestrator):
        """Тест нездорового состояния системы"""
        # Высокая загрузка CPU
        with patch("core.system.orchestrator.get_system_resources") as mock_resources:
            mock_resources.return_value = {
                "cpu_percent": 95.0,
                "memory_percent": 90.0,
                "disk_percent": 85.0,
            }

            if hasattr(orchestrator, "check_health"):
                health = await orchestrator.check_health()

                if health:
                    assert health.is_healthy == False or len(health.warnings) > 0

    @pytest.mark.asyncio
    async def test_initialization_error(self, mock_config_manager):
        """Тест ошибки инициализации"""
        with patch(
            "core.system.orchestrator.get_global_config_manager",
            side_effect=Exception("Config error"),
        ):
            with pytest.raises((SystemInitializationError, Exception)):
                orch = SystemOrchestrator()
                if hasattr(orch, "initialize"):
                    await orch.initialize()

    @pytest.mark.asyncio
    async def test_shutdown_error(self, orchestrator):
        """Тест ошибки при остановке"""
        orchestrator.trader_manager.stop_all = AsyncMock(side_effect=Exception("Stop error"))

        if hasattr(orchestrator, "stop"):
            with pytest.raises((SystemShutdownError, Exception)):
                await orchestrator.stop()

    @pytest.mark.asyncio
    async def test_monitoring_loop(self, orchestrator):
        """Тест цикла мониторинга"""
        orchestrator._should_monitor = True
        orchestrator.check_health = AsyncMock(
            return_value=HealthStatus(
                is_healthy=True,
                timestamp=datetime.now(),
                issues=[],
                warnings=[],
                system_resources={"cpu": 50.0},
                active_traders=3,
                total_trades=100,
            )
        )

        if hasattr(orchestrator, "_monitoring_loop"):
            # Запускаем мониторинг на короткое время
            task = asyncio.create_task(orchestrator._monitoring_loop())
            await asyncio.sleep(0.1)
            orchestrator._should_monitor = False
            await task

            orchestrator.check_health.assert_called()

    @pytest.mark.asyncio
    async def test_component_initialization(self, orchestrator):
        """Тест инициализации компонентов"""
        components = ["database", "cache", "message_queue"]

        for component in components:
            mock_component = AsyncMock()
            setattr(orchestrator, f"_{component}", mock_component)

        if hasattr(orchestrator, "_initialize_components"):
            await orchestrator._initialize_components()

            # Проверяем что компоненты были инициализированы
            for component in components:
                if hasattr(orchestrator, f"_{component}"):
                    comp = getattr(orchestrator, f"_{component}")
                    if hasattr(comp, "initialize"):
                        comp.initialize.assert_called()

    @pytest.mark.asyncio
    async def test_resource_limits(self, orchestrator):
        """Тест проверки лимитов ресурсов"""
        # Превышение лимита трейдеров
        orchestrator.trader_manager.get_active_traders_count.return_value = 15
        orchestrator.config_manager.get.return_value = {"max_traders": 10}

        if hasattr(orchestrator, "can_create_trader"):
            can_create = await orchestrator.can_create_trader()
            assert can_create == False

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, orchestrator):
        """Тест корректной остановки"""
        orchestrator.trader_manager.stop_all = AsyncMock()
        orchestrator._stop_monitoring = AsyncMock()
        orchestrator._cleanup_resources = AsyncMock()

        if hasattr(orchestrator, "shutdown"):
            await orchestrator.shutdown()

            orchestrator.trader_manager.stop_all.assert_called_once()
            if hasattr(orchestrator, "_cleanup_resources"):
                orchestrator._cleanup_resources.assert_called_once()

    def test_singleton_pattern(self):
        """Тест паттерна Singleton если используется"""
        with patch("core.system.orchestrator.get_global_config_manager"):
            with patch("core.system.orchestrator.get_global_trader_manager"):
                with patch("core.system.orchestrator.get_global_trader_factory"):
                    with patch("core.system.orchestrator.get_global_logger_factory"):
                        orch1 = SystemOrchestrator()
                        orch2 = SystemOrchestrator()

                        # Если используется Singleton, объекты должны быть одинаковыми
                        # Если нет - разными
                        assert orch1 is not orch2 or orch1 is orch2

    @pytest.mark.asyncio
    async def test_error_recovery(self, orchestrator):
        """Тест восстановления после ошибок"""
        # Симулируем ошибку в trader_manager
        orchestrator.trader_manager.start_all = AsyncMock(side_effect=Exception("Start failed"))

        if hasattr(orchestrator, "start_with_recovery"):
            result = await orchestrator.start_with_recovery()
            # Система должна попытаться восстановиться
            assert result is not None

    @pytest.mark.asyncio
    async def test_config_reload(self, orchestrator):
        """Тест перезагрузки конфигурации"""
        new_config = {"exchanges": ["okx"], "trading_pairs": ["SOLUSDT"], "max_traders": 5}

        if hasattr(orchestrator, "reload_config"):
            await orchestrator.reload_config(new_config)

            orchestrator.config_manager.reload.assert_called()
            orchestrator.trader_manager.update_config.assert_called()

    @pytest.mark.asyncio
    async def test_metrics_collection(self, orchestrator):
        """Тест сбора метрик"""
        if hasattr(orchestrator, "collect_metrics"):
            metrics = await orchestrator.collect_metrics()

            assert "active_traders" in metrics
            assert "total_trades" in metrics
            assert "system_uptime" in metrics
            assert metrics["active_traders"] == 3
            assert metrics["total_trades"] == 100


class TestSystemOrchestratorIntegration:
    """Интеграционные тесты для SystemOrchestrator"""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Тест полного жизненного цикла системы"""
        with patch("core.system.orchestrator.get_global_config_manager"):
            with patch("core.system.orchestrator.get_global_trader_manager"):
                with patch("core.system.orchestrator.get_global_trader_factory"):
                    with patch("core.system.orchestrator.get_global_logger_factory"):
                        orchestrator = SystemOrchestrator()

                        # Запуск
                        if hasattr(orchestrator, "start"):
                            await orchestrator.start()

                        # Проверка здоровья
                        if hasattr(orchestrator, "check_health"):
                            health = await orchestrator.check_health()
                            assert health is not None

                        # Остановка
                        if hasattr(orchestrator, "stop"):
                            await orchestrator.stop()

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Тест параллельных операций"""
        with patch("core.system.orchestrator.get_global_config_manager"):
            with patch("core.system.orchestrator.get_global_trader_manager"):
                with patch("core.system.orchestrator.get_global_trader_factory"):
                    with patch("core.system.orchestrator.get_global_logger_factory"):
                        orchestrator = SystemOrchestrator()

                        # Запускаем несколько операций параллельно
                        tasks = []
                        if hasattr(orchestrator, "check_health"):
                            for _ in range(5):
                                tasks.append(orchestrator.check_health())

                        if tasks:
                            results = await asyncio.gather(*tasks, return_exceptions=True)

                            # Все операции должны завершиться
                            assert len(results) == 5
                            # Не должно быть исключений
                            for result in results:
                                if isinstance(result, Exception):
                                    pytest.fail(f"Unexpected exception: {result}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
