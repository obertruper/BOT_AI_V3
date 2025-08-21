#!/usr/bin/env python3
"""
Unit тесты для Enhanced Position Tracker
Тестирует основную функциональность отслеживания позиций
"""

import pytest

# Маркируем весь модуль как position_tracker тесты
pytestmark = [pytest.mark.unit, pytest.mark.position_tracker]

import asyncio
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from trading.position_tracker import (
    EnhancedPositionTracker,
    TrackedPosition,
    PositionStatus,
    PositionHealth,
    PositionMetrics,
    get_position_tracker
)


class TestEnhancedPositionTracker:
    """Тестовый класс для EnhancedPositionTracker"""

    @pytest.fixture
    async def mock_exchange_manager(self):
        """Создает mock ExchangeManager"""
        mock_manager = AsyncMock()
        mock_exchange = AsyncMock()
        
        # Mock данные для тикера
        mock_exchange.fetch_ticker.return_value = {"last": 50000.0}
        
        # Mock данные для позиций
        mock_exchange.fetch_positions.return_value = [{
            "symbol": "BTCUSDT",
            "side": "long",
            "contracts": 0.001,
            "markPrice": 50500.0,
            "size": 0.001
        }]
        
        mock_manager.get_exchange.return_value = mock_exchange
        return mock_manager

    @pytest.fixture
    async def tracker(self, mock_exchange_manager):
        """Создает экземпляр трекера для тестов"""
        with patch('trading.position_tracker.AsyncPGPool') as mock_pool:
            # Mock методы AsyncPGPool
            mock_pool.fetch.return_value = []
            mock_pool.execute.return_value = None
            
            tracker = EnhancedPositionTracker(
                exchange_manager=mock_exchange_manager,
                db_pool=None,
                update_interval=1
            )
            return tracker

    @pytest.fixture
    def sample_position_data(self):
        """Образец данных позиции для тестов"""
        return {
            "position_id": "test_pos_001",
            "symbol": "BTCUSDT",
            "side": "long",
            "size": Decimal("0.001"),
            "entry_price": Decimal("50000.0"),
            "stop_loss": Decimal("49000.0"),
            "take_profit": Decimal("52000.0"),
            "exchange": "bybit"
        }

    async def test_tracker_initialization(self, mock_exchange_manager):
        """Тест инициализации трекера"""
        with patch('trading.position_tracker.AsyncPGPool'):
            tracker = EnhancedPositionTracker(mock_exchange_manager)
            
            assert tracker.exchange_manager == mock_exchange_manager
            assert tracker.update_interval == 30
            assert tracker.tracked_positions == {}
            assert not tracker.is_running
            assert tracker.stats["total_tracked"] == 0
            assert tracker.stats["active_positions"] == 0

    async def test_track_position(self, tracker, sample_position_data):
        """Тест добавления позиции в отслеживание"""
        position = await tracker.track_position(**sample_position_data)
        
        assert position.position_id == "test_pos_001"
        assert position.symbol == "BTCUSDT"
        assert position.side == "long"
        assert position.size == Decimal("0.001")
        assert position.entry_price == Decimal("50000.0")
        assert position.status == PositionStatus.ACTIVE
        
        # Проверяем что позиция добавлена в tracking
        assert "test_pos_001" in tracker.tracked_positions
        assert tracker.stats["total_tracked"] == 1
        assert tracker.stats["active_positions"] == 1

    async def test_remove_position(self, tracker, sample_position_data):
        """Тест удаления позиции из отслеживания"""
        # Добавляем позицию
        await tracker.track_position(**sample_position_data)
        
        # Удаляем позицию
        await tracker.remove_position("test_pos_001", "closed")
        
        # Проверяем что позиция удалена
        assert "test_pos_001" not in tracker.tracked_positions
        assert tracker.stats["active_positions"] == 0

    async def test_calculate_unrealized_pnl(self, tracker, sample_position_data):
        """Тест расчета нереализованного PnL"""
        # Добавляем позицию
        position = await tracker.track_position(**sample_position_data)
        
        # Устанавливаем текущую цену
        position.current_price = Decimal("51000.0")
        
        # Рассчитываем PnL
        pnl = await tracker.calculate_unrealized_pnl("test_pos_001")
        
        # Для long позиции: (current_price - entry_price) * size
        # (51000 - 50000) * 0.001 = 1.0
        expected_pnl = Decimal("1.0")
        assert pnl == expected_pnl

    async def test_calculate_unrealized_pnl_short(self, tracker, sample_position_data):
        """Тест расчета PnL для короткой позиции"""
        # Модифицируем данные для short позиции
        sample_position_data["side"] = "short"
        sample_position_data["position_id"] = "test_pos_002"
        
        # Добавляем позицию
        position = await tracker.track_position(**sample_position_data)
        position.current_price = Decimal("49000.0")
        
        # Рассчитываем PnL
        pnl = await tracker.calculate_unrealized_pnl("test_pos_002")
        
        # Для short позиции: (entry_price - current_price) * size
        # (50000 - 49000) * 0.001 = 1.0
        expected_pnl = Decimal("1.0")
        assert pnl == expected_pnl

    async def test_position_health_check(self, tracker, sample_position_data):
        """Тест проверки здоровья позиции"""
        position = await tracker.track_position(**sample_position_data)
        
        # Устанавливаем цену для убыточной позиции (-6%)
        position.current_price = Decimal("47000.0")
        await tracker._calculate_position_metrics(position)
        await tracker._check_position_health(position)
        
        # Должна быть CRITICAL позиция
        assert position.health == PositionHealth.CRITICAL
        assert position.metrics.health_score == 0.1

    async def test_position_health_warning(self, tracker, sample_position_data):
        """Тест предупреждения о здоровье позиции"""
        position = await tracker.track_position(**sample_position_data)
        
        # Устанавливаем цену для позиции с предупреждением (-4%)
        position.current_price = Decimal("48000.0")
        await tracker._calculate_position_metrics(position)
        await tracker._check_position_health(position)
        
        # Должна быть WARNING позиция
        assert position.health == PositionHealth.WARNING
        assert position.metrics.health_score == 0.5

    async def test_position_health_healthy(self, tracker, sample_position_data):
        """Тест здоровой позиции"""
        position = await tracker.track_position(**sample_position_data)
        
        # Устанавливаем прибыльную цену
        position.current_price = Decimal("51000.0")
        await tracker._calculate_position_metrics(position)
        await tracker._check_position_health(position)
        
        # Должна быть HEALTHY позиция
        assert position.health == PositionHealth.HEALTHY
        assert position.metrics.health_score == 1.0

    async def test_get_active_positions(self, tracker, sample_position_data):
        """Тест получения активных позиций"""
        # Добавляем несколько позиций
        await tracker.track_position(**sample_position_data)
        
        sample_position_data["position_id"] = "test_pos_002"
        sample_position_data["symbol"] = "ETHUSDT"
        await tracker.track_position(**sample_position_data)
        
        # Получаем активные позиции
        active_positions = await tracker.get_active_positions()
        
        assert len(active_positions) == 2
        assert all(pos.status == PositionStatus.ACTIVE for pos in active_positions)

    async def test_get_positions_by_symbol(self, tracker, sample_position_data):
        """Тест получения позиций по символу"""
        # Добавляем позиции разных символов
        await tracker.track_position(**sample_position_data)
        
        sample_position_data["position_id"] = "test_pos_002"
        sample_position_data["symbol"] = "ETHUSDT"
        await tracker.track_position(**sample_position_data)
        
        # Получаем позиции для BTCUSDT
        btc_positions = await tracker.get_positions_by_symbol("BTCUSDT")
        assert len(btc_positions) == 1
        assert btc_positions[0].symbol == "BTCUSDT"
        
        # Получаем позиции для ETHUSDT
        eth_positions = await tracker.get_positions_by_symbol("ETHUSDT")
        assert len(eth_positions) == 1
        assert eth_positions[0].symbol == "ETHUSDT"

    async def test_tracker_stats(self, tracker, sample_position_data):
        """Тест получения статистики трекера"""
        # Добавляем позицию
        position = await tracker.track_position(**sample_position_data)
        
        # Устанавливаем метрики
        position.current_price = Decimal("47000.0")  # Критическое состояние
        await tracker._calculate_position_metrics(position)
        await tracker._check_position_health(position)
        
        # Получаем статистику
        stats = await tracker.get_tracker_stats()
        
        assert stats["total_tracked"] == 1
        assert stats["active_positions"] == 1
        assert stats["health_distribution"]["critical"] == 1
        assert stats["health_distribution"]["healthy"] == 0
        assert stats["health_distribution"]["warning"] == 0
        assert stats["is_running"] == False

    async def test_position_metrics_calculation(self, tracker, sample_position_data):
        """Тест расчета метрик позиции"""
        position = await tracker.track_position(**sample_position_data)
        
        # Устанавливаем цену и рассчитываем метрики
        position.current_price = Decimal("51000.0")
        await tracker._calculate_position_metrics(position)
        
        metrics = position.metrics
        
        # Проверяем расчеты
        assert metrics.unrealized_pnl == Decimal("1.0")  # (51000-50000)*0.001
        assert metrics.current_price == Decimal("51000.0")
        assert metrics.roi_percent == Decimal("2.0")  # 2% прибыль
        assert metrics.hold_time_minutes >= 0
        assert metrics.max_profit == Decimal("1.0")

    @patch('trading.position_tracker.AsyncPGPool')
    async def test_sync_with_exchange(self, mock_pool, tracker, sample_position_data):
        """Тест синхронизации с биржей"""
        position = await tracker.track_position(**sample_position_data)
        
        # Выполняем синхронизацию
        result = await tracker.sync_with_exchange("test_pos_001")
        
        # Проверяем что синхронизация прошла успешно
        assert result == True
        
        # Проверяем что цена обновилась (mock возвращает 50500)
        assert position.current_price == Decimal("50500.0")

    async def test_start_stop_tracking(self, tracker):
        """Тест запуска и остановки мониторинга"""
        # Запуск
        await tracker.start_tracking()
        assert tracker.is_running == True
        assert tracker.monitoring_task is not None
        
        # Остановка
        await tracker.stop_tracking()
        assert tracker.is_running == False


class TestPositionTrackerFactory:
    """Тесты фабричной функции get_position_tracker"""

    @patch('trading.position_tracker.ExchangeManager')
    @patch('trading.position_tracker.get_global_config_manager')
    async def test_get_position_tracker_success(self, mock_config_manager, mock_exchange_manager):
        """Тест успешного создания трекера через фабрику"""
        # Настраиваем моки
        mock_config = {"exchanges": {"bybit": {"enabled": True}}}
        mock_config_manager.return_value.get_config.return_value = mock_config
        
        # Получаем трекер
        tracker = await get_position_tracker()
        
        assert isinstance(tracker, EnhancedPositionTracker)
        assert tracker.exchange_manager is not None

    @patch('trading.position_tracker.ExchangeManager')
    @patch('trading.position_tracker.get_global_config_manager')
    async def test_get_position_tracker_fallback_config(self, mock_config_manager, mock_exchange_manager):
        """Тест создания трекера с fallback конфигурацией"""
        # Имитируем ошибку получения конфига
        mock_config_manager.side_effect = Exception("Config error")
        
        # Получаем трекер
        tracker = await get_position_tracker()
        
        assert isinstance(tracker, EnhancedPositionTracker)
        # Проверяем что используется базовая конфигурация
        mock_exchange_manager.assert_called_once()


class TestTrackedPosition:
    """Тесты класса TrackedPosition"""

    def test_tracked_position_creation(self):
        """Тест создания TrackedPosition"""
        position = TrackedPosition(
            position_id="test_001",
            symbol="BTCUSDT",
            side="long",
            size=Decimal("0.001"),
            entry_price=Decimal("50000.0")
        )
        
        assert position.position_id == "test_001"
        assert position.symbol == "BTCUSDT"
        assert position.side == "long"
        assert position.size == Decimal("0.001")
        assert position.entry_price == Decimal("50000.0")
        assert position.status == PositionStatus.ACTIVE
        assert position.health == PositionHealth.UNKNOWN
        assert position.metrics is not None

    def test_position_post_init(self):
        """Тест автоматического создания метрик"""
        position = TrackedPosition(
            position_id="test_001",
            symbol="BTCUSDT",
            side="long",
            size=Decimal("0.001"),
            entry_price=Decimal("50000.0")
        )
        
        assert isinstance(position.metrics, PositionMetrics)
        assert position.metrics.position_id == "test_001"


class TestPositionMetrics:
    """Тесты класса PositionMetrics"""

    def test_position_metrics_defaults(self):
        """Тест значений по умолчанию для метрик"""
        metrics = PositionMetrics("test_001")
        
        assert metrics.position_id == "test_001"
        assert metrics.unrealized_pnl == Decimal("0")
        assert metrics.realized_pnl == Decimal("0")
        assert metrics.current_price == Decimal("0")
        assert metrics.roi_percent == Decimal("0")
        assert metrics.hold_time_minutes == 0
        assert metrics.max_profit == Decimal("0")
        assert metrics.max_drawdown == Decimal("0")
        assert metrics.health_score == 1.0
        assert isinstance(metrics.last_updated, datetime)


if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v"])