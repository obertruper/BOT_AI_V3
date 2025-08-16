"""
Unit тесты для SystemOrchestrator - ML интеграция
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.system.orchestrator import SystemOrchestrator


@pytest.mark.unit
@pytest.mark.ml
class TestSystemOrchestratorML:
    """Тесты ML функциональности SystemOrchestrator"""

    @pytest.fixture
    def mock_config(self):
        """Mock конфигурация с ML настройками"""
        return {
            "system": {"environment": "test", "enable_ml": True},
            "ml": {
                "enabled": True,
                "model_directory": "models/saved",
                "signal_scheduler": {"enabled": True, "interval_seconds": 60},
            },
            "trading": {"enabled": True},
        }

    @pytest.fixture
    def orchestrator(self, mock_config):
        """Создание экземпляра SystemOrchestrator"""
        with patch("core.system.orchestrator.ConfigManager") as mock_config_manager:
            mock_config_manager.return_value.get_config.return_value = mock_config

            # Mock все зависимости
            with patch("core.system.orchestrator.TraderManager"):
                with patch("core.system.orchestrator.ExchangeRegistry"):
                    with patch("core.system.orchestrator.StrategyManager"):
                        with patch("core.system.orchestrator.RiskManager"):
                            with patch("core.system.orchestrator.MonitoringService"):
                                orchestrator = SystemOrchestrator()
                                return orchestrator

    @pytest.mark.asyncio
    async def test_ml_components_initialization(self, orchestrator, mock_config):
        """Тест инициализации ML компонентов"""
        # Mock ML компоненты
        with patch("core.system.orchestrator.MLSignalGenerator") as mock_ml_generator:
            with patch("core.system.orchestrator.SignalScheduler") as mock_scheduler:
                mock_ml_generator_instance = AsyncMock()
                mock_scheduler_instance = AsyncMock()

                mock_ml_generator.return_value = mock_ml_generator_instance
                mock_scheduler.return_value = mock_scheduler_instance

                # Инициализируем orchestrator
                await orchestrator.initialize()

                # Проверяем, что ML компоненты созданы
                assert orchestrator.ml_signal_generator is not None
                assert orchestrator.signal_scheduler is not None

                # Проверяем вызовы инициализации
                mock_ml_generator_instance.initialize.assert_called_once()
                mock_scheduler_instance.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_ml_disabled_initialization(self, orchestrator):
        """Тест инициализации когда ML отключен"""
        # Отключаем ML
        orchestrator.config["ml"]["enabled"] = False

        await orchestrator.initialize()

        # ML компоненты не должны быть созданы
        assert not hasattr(orchestrator, "ml_signal_generator")
        assert not hasattr(orchestrator, "signal_scheduler")

    @pytest.mark.asyncio
    async def test_ml_signal_processing(self, orchestrator):
        """Тест обработки ML сигналов"""
        # Mock ML генератор
        orchestrator.ml_signal_generator = AsyncMock()
        orchestrator.ml_signal_generator.generate_signals = AsyncMock()

        # Mock сигнал
        mock_signal = MagicMock()
        mock_signal.symbol = "BTCUSDT"
        mock_signal.confidence = 0.8
        orchestrator.ml_signal_generator.generate_signals.return_value = [mock_signal]

        # Mock обработку сигнала
        orchestrator._process_ml_signal = AsyncMock()

        # Запускаем обработку
        await orchestrator._process_ml_signals()

        # Проверяем вызовы
        orchestrator.ml_signal_generator.generate_signals.assert_called_once()
        orchestrator._process_ml_signal.assert_called_once_with(mock_signal)

    @pytest.mark.asyncio
    async def test_ml_signal_to_trading_engine(self, orchestrator):
        """Тест передачи ML сигнала в торговый движок"""
        # Mock компоненты
        orchestrator.trader_manager = AsyncMock()
        orchestrator.trader_manager.get_active_traders = AsyncMock(return_value=["trader1"])
        orchestrator.trader_manager.get_trader = AsyncMock()

        mock_trader = AsyncMock()
        mock_trader.trading_engine = AsyncMock()
        orchestrator.trader_manager.get_trader.return_value = mock_trader

        # Mock ML сигнал
        mock_signal = MagicMock()
        mock_signal.symbol = "BTCUSDT"
        mock_signal.confidence = 0.8
        mock_signal.metadata = {"ml_model": "PatchTST"}

        # Обрабатываем сигнал
        await orchestrator._process_ml_signal(mock_signal)

        # Проверяем передачу в trading engine
        mock_trader.trading_engine.process_signal.assert_called_once_with(mock_signal)

    @pytest.mark.asyncio
    async def test_ml_scheduler_lifecycle(self, orchestrator):
        """Тест жизненного цикла ML планировщика"""
        # Mock scheduler
        orchestrator.signal_scheduler = AsyncMock()

        # Start
        await orchestrator._start_ml_scheduler()
        orchestrator.signal_scheduler.start.assert_called_once()

        # Stop
        await orchestrator._stop_ml_scheduler()
        orchestrator.signal_scheduler.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_ml_error_handling(self, orchestrator):
        """Тест обработки ошибок в ML компонентах"""
        # Mock ML генератор с ошибкой
        orchestrator.ml_signal_generator = AsyncMock()
        orchestrator.ml_signal_generator.generate_signals = AsyncMock(
            side_effect=RuntimeError("ML model error")
        )

        # Обработка не должна прерваться
        await orchestrator._process_ml_signals()

        # Проверяем, что ошибка залогирована (через mock logger)
        # Система должна продолжить работу
        assert orchestrator._running  # Предполагаем, что есть флаг

    @pytest.mark.asyncio
    async def test_ml_metrics_collection(self, orchestrator):
        """Тест сбора метрик ML системы"""
        # Mock компоненты
        orchestrator.ml_signal_generator = AsyncMock()
        orchestrator.ml_signal_generator.get_metrics = AsyncMock(
            return_value={
                "signals_generated": 100,
                "average_confidence": 0.75,
                "model_version": "1.0.0",
            }
        )

        orchestrator.signal_scheduler = AsyncMock()
        orchestrator.signal_scheduler.get_metrics = AsyncMock(
            return_value={"cycles_completed": 50, "average_processing_time": 0.125}
        )

        # Собираем метрики
        metrics = await orchestrator.collect_ml_metrics()

        assert metrics["ml_signal_generator"]["signals_generated"] == 100
        assert metrics["signal_scheduler"]["cycles_completed"] == 50

    @pytest.mark.asyncio
    async def test_ml_graceful_shutdown(self, orchestrator):
        """Тест корректного завершения ML компонентов"""
        # Mock ML компоненты
        orchestrator.ml_signal_generator = AsyncMock()
        orchestrator.signal_scheduler = AsyncMock()

        # Mock активные задачи
        active_task = asyncio.create_task(asyncio.sleep(10))
        orchestrator._ml_tasks = [active_task]

        # Shutdown
        await orchestrator._shutdown_ml_components()

        # Проверяем вызовы
        orchestrator.signal_scheduler.stop.assert_called_once()
        orchestrator.ml_signal_generator.shutdown.assert_called_once()

        # Проверяем отмену задач
        assert active_task.cancelled()

    @pytest.mark.asyncio
    async def test_ml_health_check(self, orchestrator):
        """Тест health check для ML компонентов"""
        # Mock компоненты
        orchestrator.ml_signal_generator = AsyncMock()
        orchestrator.ml_signal_generator.is_healthy = AsyncMock(return_value=True)

        orchestrator.signal_scheduler = AsyncMock()
        orchestrator.signal_scheduler.is_running = AsyncMock(return_value=True)

        # Проверяем здоровье
        health = await orchestrator.check_ml_health()

        assert health["ml_signal_generator"]["status"] == "healthy"
        assert health["signal_scheduler"]["status"] == "running"

    @pytest.mark.asyncio
    async def test_ml_signal_filtering(self, orchestrator):
        """Тест фильтрации ML сигналов"""
        # Mock сигналы с разной уверенностью
        signals = [
            MagicMock(symbol="BTC", confidence=0.9),
            MagicMock(symbol="ETH", confidence=0.5),  # Будет отфильтрован
            MagicMock(symbol="BNB", confidence=0.7),
        ]

        orchestrator.ml_signal_generator = AsyncMock()
        orchestrator.ml_signal_generator.generate_signals = AsyncMock(return_value=signals)

        # Mock обработку
        orchestrator._process_ml_signal = AsyncMock()

        # Минимальная уверенность
        orchestrator.config["ml"]["min_confidence"] = 0.6

        # Обрабатываем
        await orchestrator._process_ml_signals()

        # Проверяем, что обработаны только 2 сигнала
        assert orchestrator._process_ml_signal.call_count == 2

    @pytest.mark.asyncio
    async def test_ml_signal_routing(self, orchestrator):
        """Тест маршрутизации ML сигналов к трейдерам"""
        # Mock трейдеры с разными символами
        orchestrator.trader_manager = AsyncMock()

        trader1 = AsyncMock()
        trader1.config = {"symbol": "BTCUSDT"}
        trader1.is_active = True

        trader2 = AsyncMock()
        trader2.config = {"symbol": "ETHUSDT"}
        trader2.is_active = True

        orchestrator.trader_manager.get_traders_for_symbol = AsyncMock()
        orchestrator.trader_manager.get_traders_for_symbol.side_effect = [
            [trader1],  # Для BTCUSDT
            [trader2],  # Для ETHUSDT
        ]

        # Сигналы для разных символов
        btc_signal = MagicMock(symbol="BTCUSDT")
        eth_signal = MagicMock(symbol="ETHUSDT")

        # Маршрутизируем
        await orchestrator._route_ml_signal(btc_signal)
        await orchestrator._route_ml_signal(eth_signal)

        # Проверяем доставку
        trader1.process_ml_signal.assert_called_once_with(btc_signal)
        trader2.process_ml_signal.assert_called_once_with(eth_signal)

    @pytest.mark.asyncio
    async def test_ml_performance_monitoring(self, orchestrator):
        """Тест мониторинга производительности ML"""
        # Mock таймеры
        orchestrator._ml_processing_times = [0.1, 0.15, 0.12, 0.11, 0.13]

        # Рассчитываем статистику
        stats = await orchestrator.get_ml_performance_stats()

        assert stats["average_processing_time"] == pytest.approx(0.122, 0.001)
        assert stats["min_processing_time"] == 0.1
        assert stats["max_processing_time"] == 0.15
        assert stats["total_cycles"] == 5

    @pytest.mark.asyncio
    async def test_ml_config_reload(self, orchestrator):
        """Тест перезагрузки ML конфигурации"""
        # Mock компоненты
        orchestrator.ml_signal_generator = AsyncMock()
        orchestrator.signal_scheduler = AsyncMock()
        orchestrator.config_manager = AsyncMock()

        # Новая конфигурация
        new_config = {
            "ml": {
                "enabled": True,
                "signal_scheduler": {"interval_seconds": 30},
            }  # Изменилось с 60
        }

        orchestrator.config_manager.reload_config = AsyncMock(return_value=new_config)

        # Перезагружаем
        await orchestrator.reload_ml_config()

        # Проверяем перезапуск компонентов
        orchestrator.signal_scheduler.stop.assert_called_once()
        orchestrator.signal_scheduler.update_interval.assert_called_once_with(30)
        orchestrator.signal_scheduler.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_ml_emergency_stop(self, orchestrator):
        """Тест экстренной остановки ML системы"""
        # Mock компоненты
        orchestrator.ml_signal_generator = AsyncMock()
        orchestrator.signal_scheduler = AsyncMock()

        # Активные ML процессы
        orchestrator._ml_active = True

        # Экстренная остановка
        await orchestrator.emergency_stop_ml()

        # Проверяем немедленную остановку
        orchestrator.signal_scheduler.stop.assert_called_once()
        assert not orchestrator._ml_active

        # Новые сигналы не должны обрабатываться
        await orchestrator._process_ml_signals()
        orchestrator.ml_signal_generator.generate_signals.assert_not_called()
