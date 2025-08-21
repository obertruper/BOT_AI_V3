#!/usr/bin/env python3
"""
Integration тесты для Enhanced Position Tracker
Тестирует интеграцию с базой данных, API и другими компонентами
"""

import pytest

# Маркируем весь модуль как integration и position_tracker тесты
pytestmark = [pytest.mark.integration, pytest.mark.position_tracker]

import asyncio
import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import patch, AsyncMock

from trading.position_tracker import EnhancedPositionTracker, get_position_tracker
from database.connections.postgres import AsyncPGPool
from exchanges.exchange_manager import ExchangeManager


class TestPositionTrackerDatabaseIntegration:
    """Тесты интеграции с базой данных"""

    @pytest.fixture
    async def db_tracker(self):
        """Создает трекер с реальной БД (мокнутой)"""
        mock_exchange_manager = AsyncMock()
        
        with patch('trading.position_tracker.AsyncPGPool') as mock_pool:
            # Моки для методов AsyncPGPool
            mock_pool.fetch.return_value = [
                {
                    "position_id": "existing_pos_001",
                    "symbol": "BTCUSDT", 
                    "side": "long",
                    "size": 0.001,
                    "entry_price": 50000.0,
                    "stop_loss": 49000.0,
                    "take_profit": 52000.0,
                    "exchange": "bybit",
                    "created_at": datetime.now()
                }
            ]
            mock_pool.execute.return_value = None
            
            tracker = EnhancedPositionTracker(mock_exchange_manager)
            return tracker

    async def test_load_active_positions(self, db_tracker):
        """Тест загрузки активных позиций из БД"""
        await db_tracker._load_active_positions()
        
        # Проверяем что позиция загрузилась
        assert len(db_tracker.tracked_positions) == 1
        assert "existing_pos_001" in db_tracker.tracked_positions
        
        position = db_tracker.tracked_positions["existing_pos_001"]
        assert position.symbol == "BTCUSDT"
        assert position.side == "long"
        assert position.size == Decimal("0.001")

    async def test_save_position_to_db(self, db_tracker):
        """Тест сохранения позиции в БД"""
        from trading.position_tracker import TrackedPosition
        
        position = TrackedPosition(
            position_id="test_save_001",
            symbol="ETHUSDT",
            side="short",
            size=Decimal("0.1"),
            entry_price=Decimal("3000.0"),
            exchange="bybit"
        )
        
        # Сохраняем в БД
        await db_tracker._save_position_to_db(position)
        
        # Проверяем что AsyncPGPool.execute был вызван
        with patch('trading.position_tracker.AsyncPGPool.execute') as mock_execute:
            await db_tracker._save_position_to_db(position)
            mock_execute.assert_called_once()

    async def test_update_position_in_db(self, db_tracker):
        """Тест обновления позиции в БД"""
        # Добавляем позицию
        position = await db_tracker.track_position(
            position_id="test_update_001",
            symbol="BTCUSDT",
            side="long",
            size=Decimal("0.001"),
            entry_price=Decimal("50000.0"),
            exchange="bybit"
        )
        
        # Обновляем метрики
        position.current_price = Decimal("51000.0")
        await db_tracker._calculate_position_metrics(position)
        
        # Обновляем в БД
        with patch('trading.position_tracker.AsyncPGPool.execute') as mock_execute:
            await db_tracker._update_position_in_db(position)
            mock_execute.assert_called_once()


class TestPositionTrackerExchangeIntegration:
    """Тесты интеграции с биржами"""

    @pytest.fixture
    async def exchange_tracker(self):
        """Создает трекер с мокнутым ExchangeManager"""
        mock_exchange_manager = AsyncMock()
        mock_exchange = AsyncMock()
        
        # Mock для fetch_ticker
        mock_exchange.fetch_ticker.return_value = {
            "last": 50500.0,
            "bid": 50495.0,
            "ask": 50505.0
        }
        
        # Mock для fetch_positions
        mock_exchange.fetch_positions.return_value = [
            {
                "symbol": "BTCUSDT",
                "side": "long", 
                "contracts": 0.001,
                "size": 0.001,
                "markPrice": 50500.0,
                "unrealizedPnl": 0.5
            }
        ]
        
        mock_exchange_manager.get_exchange.return_value = mock_exchange
        
        with patch('trading.position_tracker.AsyncPGPool'):
            tracker = EnhancedPositionTracker(mock_exchange_manager)
            return tracker

    async def test_get_current_price(self, exchange_tracker):
        """Тест получения текущей цены с биржи"""
        price = await exchange_tracker._get_current_price("BTCUSDT", "bybit")
        
        assert price == Decimal("50500.0")
        
        # Проверяем что метод биржи был вызван
        exchange_tracker.exchange_manager.get_exchange.assert_called_with("bybit")

    async def test_fetch_position_from_exchange(self, exchange_tracker):
        """Тест получения данных позиции с биржи"""
        from trading.position_tracker import TrackedPosition
        
        position = TrackedPosition(
            position_id="test_fetch_001",
            symbol="BTCUSDT",
            side="long",
            size=Decimal("0.001"),
            entry_price=Decimal("50000.0"),
            exchange="bybit"
        )
        
        exchange_data = await exchange_tracker._fetch_position_from_exchange(position)
        
        assert exchange_data is not None
        assert exchange_data["symbol"] == "BTCUSDT"
        assert exchange_data["side"] == "long"
        assert float(exchange_data["contracts"]) == 0.001

    async def test_sync_with_exchange_success(self, exchange_tracker):
        """Тест успешной синхронизации с биржей"""
        # Добавляем позицию
        position = await exchange_tracker.track_position(
            position_id="sync_test_001",
            symbol="BTCUSDT",
            side="long",
            size=Decimal("0.001"),
            entry_price=Decimal("50000.0"),
            exchange="bybit"
        )
        
        # Синхронизируем
        result = await exchange_tracker.sync_with_exchange("sync_test_001")
        
        assert result == True
        assert position.current_price == Decimal("50500.0")
        assert position.size == Decimal("0.001")

    async def test_sync_with_exchange_position_closed(self, exchange_tracker):
        """Тест синхронизации когда позиция закрыта на бирже"""
        # Настраиваем мок чтобы возвращал закрытую позицию
        mock_exchange = AsyncMock()
        mock_exchange.fetch_positions.return_value = [
            {
                "symbol": "BTCUSDT",
                "side": "long",
                "contracts": 0.001,
                "size": 0,  # Размер 0 = закрытая позиция
                "markPrice": 50500.0
            }
        ]
        exchange_tracker.exchange_manager.get_exchange.return_value = mock_exchange
        
        # Добавляем позицию
        await exchange_tracker.track_position(
            position_id="closed_test_001",
            symbol="BTCUSDT",
            side="long", 
            size=Decimal("0.001"),
            entry_price=Decimal("50000.0"),
            exchange="bybit"
        )
        
        # Синхронизируем
        result = await exchange_tracker.sync_with_exchange("closed_test_001")
        
        assert result == True
        # Позиция должна быть удалена из отслеживания
        assert "closed_test_001" not in exchange_tracker.tracked_positions


class TestPositionTrackerAPIIntegration:
    """Тесты интеграции с API"""

    @pytest.fixture
    def client(self):
        """Создает тестовый клиент FastAPI"""
        from fastapi.testclient import TestClient
        from web.api.main import app
        
        return TestClient(app)

    async def test_position_tracker_status_endpoint(self, client):
        """Тест эндпоинта статуса трекера"""
        response = client.get("/api/testing/position-tracker-status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert "tracker_stats" in data
        assert "is_running" in data["tracker_stats"]

    async def test_create_test_position_endpoint(self, client):
        """Тест эндпоинта создания тестовой позиции"""
        position_data = {
            "symbol": "BTCUSDT",
            "side": "long",
            "size": 0.001,
            "entry_price": 50000.0,
            "stop_loss": 49000.0,
            "take_profit": 52000.0
        }
        
        response = client.post("/api/testing/create-test-position", json=position_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert "position" in data
        assert data["position"]["symbol"] == "BTCUSDT"
        assert data["position"]["side"] == "long"

    async def test_cleanup_test_positions_endpoint(self, client):
        """Тест эндпоинта очистки тестовых позиций"""
        # Сначала создаем тестовую позицию
        position_data = {
            "symbol": "BTCUSDT",
            "side": "long", 
            "size": 0.001,
            "entry_price": 50000.0
        }
        client.post("/api/testing/create-test-position", json=position_data)
        
        # Затем очищаем
        response = client.delete("/api/testing/cleanup-test-positions")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert "deleted_count" in data


class TestPositionTrackerSystemIntegration:
    """Системные интеграционные тесты"""

    @patch('trading.position_tracker.get_global_config_manager')
    @patch('trading.position_tracker.ExchangeManager')
    async def test_get_position_tracker_integration(self, mock_exchange_manager, mock_config_manager):
        """Тест интеграции фабричной функции"""
        # Настраиваем конфигурацию
        mock_config = {
            "exchanges": {
                "bybit": {
                    "enabled": True,
                    "api_key": "test_key",
                    "api_secret": "test_secret",
                    "testnet": True
                }
            }
        }
        mock_config_manager.return_value.get_config.return_value = mock_config
        
        # Получаем трекер
        tracker = await get_position_tracker()
        
        assert isinstance(tracker, EnhancedPositionTracker)
        mock_exchange_manager.assert_called_once_with(mock_config)

    async def test_position_lifecycle_integration(self):
        """Тест полного жизненного цикла позиции"""
        with patch('trading.position_tracker.ExchangeManager') as mock_em:
            with patch('trading.position_tracker.AsyncPGPool'):
                # Настраиваем моки
                mock_exchange = AsyncMock()
                mock_exchange.fetch_ticker.return_value = {"last": 50000.0}
                mock_em.return_value.get_exchange.return_value = mock_exchange
                
                tracker = EnhancedPositionTracker(mock_em.return_value)
                
                # 1. Создание позиции
                position = await tracker.track_position(
                    position_id="lifecycle_test",
                    symbol="BTCUSDT",
                    side="long",
                    size=Decimal("0.001"),
                    entry_price=Decimal("50000.0"),
                    exchange="bybit"
                )
                
                assert position.position_id == "lifecycle_test"
                assert tracker.stats["total_tracked"] == 1
                
                # 2. Обновление метрик
                success = await tracker.update_position_metrics("lifecycle_test")
                assert success == True
                
                # 3. Получение статистики
                stats = await tracker.get_tracker_stats()
                assert stats["active_positions"] == 1
                
                # 4. Удаление позиции
                await tracker.remove_position("lifecycle_test", "closed")
                assert "lifecycle_test" not in tracker.tracked_positions

    async def test_monitoring_loop_integration(self):
        """Тест интеграции цикла мониторинга"""
        with patch('trading.position_tracker.ExchangeManager') as mock_em:
            with patch('trading.position_tracker.AsyncPGPool'):
                mock_exchange = AsyncMock()
                mock_exchange.fetch_ticker.return_value = {"last": 51000.0}
                mock_em.return_value.get_exchange.return_value = mock_exchange
                
                tracker = EnhancedPositionTracker(mock_em.return_value, update_interval=0.1)
                
                # Добавляем позицию
                await tracker.track_position(
                    position_id="monitor_test",
                    symbol="BTCUSDT",
                    side="long",
                    size=Decimal("0.001"),
                    entry_price=Decimal("50000.0"),
                    exchange="bybit"
                )
                
                # Запускаем мониторинг на короткое время
                await tracker.start_tracking()
                await asyncio.sleep(0.2)  # Даем время на один цикл
                await tracker.stop_tracking()
                
                # Проверяем что обновления произошли
                assert tracker.stats["updates_count"] > 0
                
                position = tracker.tracked_positions["monitor_test"]
                assert position.current_price == Decimal("51000.0")


class TestPositionTrackerErrorHandling:
    """Тесты обработки ошибок"""

    async def test_database_error_handling(self):
        """Тест обработки ошибок базы данных"""
        with patch('trading.position_tracker.ExchangeManager') as mock_em:
            with patch('trading.position_tracker.AsyncPGPool') as mock_pool:
                # Имитируем ошибку БД
                mock_pool.execute.side_effect = Exception("Database error")
                
                tracker = EnhancedPositionTracker(mock_em.return_value)
                
                # Попытка сохранения должна обрабатывать ошибку
                from trading.position_tracker import TrackedPosition
                position = TrackedPosition(
                    position_id="error_test",
                    symbol="BTCUSDT",
                    side="long",
                    size=Decimal("0.001"),
                    entry_price=Decimal("50000.0")
                )
                
                # Не должно выбрасывать исключение
                await tracker._save_position_to_db(position)

    async def test_exchange_error_handling(self):
        """Тест обработки ошибок биржи"""
        with patch('trading.position_tracker.ExchangeManager') as mock_em:
            with patch('trading.position_tracker.AsyncPGPool'):
                # Имитируем ошибку биржи
                mock_exchange = AsyncMock()
                mock_exchange.fetch_ticker.side_effect = Exception("Exchange error")
                mock_em.return_value.get_exchange.return_value = mock_exchange
                
                tracker = EnhancedPositionTracker(mock_em.return_value)
                
                # Получение цены должно вернуть 0 при ошибке
                price = await tracker._get_current_price("BTCUSDT", "bybit")
                assert price == Decimal("0")

    async def test_update_position_error_handling(self):
        """Тест обработки ошибок обновления позиции"""
        with patch('trading.position_tracker.ExchangeManager') as mock_em:
            with patch('trading.position_tracker.AsyncPGPool'):
                mock_exchange = AsyncMock()
                mock_exchange.fetch_ticker.side_effect = Exception("Update error")
                mock_em.return_value.get_exchange.return_value = mock_exchange
                
                tracker = EnhancedPositionTracker(mock_em.return_value)
                
                # Добавляем позицию
                await tracker.track_position(
                    position_id="update_error_test",
                    symbol="BTCUSDT",
                    side="long",
                    size=Decimal("0.001"),
                    entry_price=Decimal("50000.0"),
                    exchange="bybit"
                )
                
                # Обновление должно вернуть False при ошибке
                result = await tracker.update_position_metrics("update_error_test")
                assert result == False


if __name__ == "__main__":
    # Запуск интеграционных тестов
    pytest.main([__file__, "-v", "--tb=short"])