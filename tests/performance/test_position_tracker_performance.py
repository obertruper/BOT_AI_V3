#!/usr/bin/env python3
"""
Performance тесты для Enhanced Position Tracker
Тестирует производительность и нагрузку системы отслеживания позиций
"""

import pytest

# Маркируем весь модуль как performance и position_tracker тесты
pytestmark = [pytest.mark.performance, pytest.mark.position_tracker]

import asyncio
import time
import pytest
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, AsyncMock

from trading.position_tracker import EnhancedPositionTracker


class TestPositionTrackerPerformance:
    """Performance тесты для Position Tracker"""

    @pytest.fixture
    async def performance_tracker(self):
        """Создает оптимизированный трекер для performance тестов"""
        mock_exchange_manager = AsyncMock()
        mock_exchange = AsyncMock()
        
        # Быстрые ответы от биржи
        mock_exchange.fetch_ticker.return_value = {"last": 50000.0}
        mock_exchange.fetch_positions.return_value = []
        mock_exchange_manager.get_exchange.return_value = mock_exchange
        
        with patch('trading.position_tracker.AsyncPGPool') as mock_pool:
            mock_pool.fetch.return_value = []
            mock_pool.execute.return_value = None
            
            tracker = EnhancedPositionTracker(
                exchange_manager=mock_exchange_manager,
                update_interval=0.01  # Очень быстрые обновления для тестов
            )
            return tracker

    @pytest.mark.asyncio
    async def test_single_position_tracking_speed(self, performance_tracker):
        """Тест скорости отслеживания одной позиции"""
        start_time = time.perf_counter()
        
        # Добавляем позицию
        position = await performance_tracker.track_position(
            position_id="perf_test_001",
            symbol="BTCUSDT",
            side="long",
            size=Decimal("0.001"),
            entry_price=Decimal("50000.0"),
            exchange="bybit"
        )
        
        end_time = time.perf_counter()
        tracking_time = end_time - start_time
        
        assert position is not None
        assert tracking_time < 0.1, f"Position tracking took {tracking_time:.3f}s, should be <0.1s"

    @pytest.mark.asyncio
    async def test_multiple_positions_tracking_speed(self, performance_tracker):
        """Тест скорости отслеживания множества позиций"""
        num_positions = 100
        start_time = time.perf_counter()
        
        # Добавляем много позиций
        tasks = []
        for i in range(num_positions):
            task = performance_tracker.track_position(
                position_id=f"perf_multi_{i:03d}",
                symbol="BTCUSDT",
                side="long" if i % 2 == 0 else "short",
                size=Decimal("0.001"),
                entry_price=Decimal(str(50000 + i)),
                exchange="bybit"
            )
            tasks.append(task)
        
        # Ждем все позиции
        positions = await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        avg_time_per_position = total_time / num_positions
        
        assert len(positions) == num_positions
        assert all(p is not None for p in positions)
        assert avg_time_per_position < 0.01, f"Average time per position: {avg_time_per_position:.4f}s"
        assert total_time < 2.0, f"Total time: {total_time:.3f}s should be <2.0s"

    @pytest.mark.asyncio
    async def test_position_metrics_calculation_performance(self, performance_tracker):
        """Тест производительности расчета метрик"""
        # Добавляем позиции
        num_positions = 50
        positions = []
        
        for i in range(num_positions):
            position = await performance_tracker.track_position(
                position_id=f"metrics_perf_{i:03d}",
                symbol="BTCUSDT",
                side="long",
                size=Decimal("0.001"),
                entry_price=Decimal(str(50000 + i * 10)),
                exchange="bybit"
            )
            position.current_price = Decimal(str(50000 + i * 15))  # Симулируем изменение цены
            positions.append(position)
        
        # Измеряем время расчета метрик
        start_time = time.perf_counter()
        
        for position in positions:
            await performance_tracker._calculate_position_metrics(position)
            await performance_tracker._check_position_health(position)
        
        end_time = time.perf_counter()
        calculation_time = end_time - start_time
        avg_time_per_calculation = calculation_time / num_positions
        
        assert avg_time_per_calculation < 0.005, f"Average calculation time: {avg_time_per_calculation:.4f}s"
        assert calculation_time < 0.5, f"Total calculation time: {calculation_time:.3f}s"

    @pytest.mark.asyncio 
    async def test_concurrent_position_updates(self, performance_tracker):
        """Тест параллельного обновления позиций"""
        num_positions = 20
        
        # Создаем позиции
        for i in range(num_positions):
            await performance_tracker.track_position(
                position_id=f"concurrent_{i:03d}",
                symbol="BTCUSDT",
                side="long",
                size=Decimal("0.001"),
                entry_price=Decimal("50000.0"),
                exchange="bybit"
            )
        
        # Измеряем время параллельного обновления
        start_time = time.perf_counter()
        
        update_tasks = [
            performance_tracker.update_position_metrics(f"concurrent_{i:03d}")
            for i in range(num_positions)
        ]
        
        results = await asyncio.gather(*update_tasks, return_exceptions=True)
        
        end_time = time.perf_counter()
        update_time = end_time - start_time
        
        # Проверяем что все обновления прошли успешно
        successful_updates = sum(1 for r in results if r is True)
        assert successful_updates == num_positions
        assert update_time < 1.0, f"Concurrent updates took {update_time:.3f}s"

    @pytest.mark.asyncio
    async def test_memory_usage_with_many_positions(self, performance_tracker):
        """Тест использования памяти с большим количеством позиций"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Создаем много позиций
        num_positions = 1000
        positions = []
        
        for i in range(num_positions):
            position = await performance_tracker.track_position(
                position_id=f"memory_test_{i:04d}",
                symbol=f"TEST{i % 10}USDT",  # Разные символы
                side="long" if i % 2 == 0 else "short",
                size=Decimal(str(0.001 + i * 0.0001)),
                entry_price=Decimal(str(50000 + i)),
                exchange="bybit"
            )
            positions.append(position)
        
        # Обновляем все метрики
        for position in positions:
            position.current_price = position.entry_price * Decimal("1.01")
            await performance_tracker._calculate_position_metrics(position)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        memory_per_position = memory_increase / num_positions
        
        assert len(performance_tracker.tracked_positions) == num_positions
        assert memory_per_position < 0.1, f"Memory per position: {memory_per_position:.3f}MB"
        assert memory_increase < 100, f"Total memory increase: {memory_increase:.1f}MB"

    @pytest.mark.asyncio
    async def test_monitoring_loop_performance(self, performance_tracker):
        """Тест производительности цикла мониторинга"""
        # Добавляем позиции
        num_positions = 25
        for i in range(num_positions):
            await performance_tracker.track_position(
                position_id=f"monitor_perf_{i:03d}",
                symbol="BTCUSDT",
                side="long",
                size=Decimal("0.001"),
                entry_price=Decimal("50000.0"),
                exchange="bybit"
            )
        
        # Запускаем мониторинг и измеряем время циклов
        await performance_tracker.start_tracking()
        
        # Ждем несколько циклов
        await asyncio.sleep(0.1)  # Минимум 10 циклов при interval=0.01
        
        await performance_tracker.stop_tracking()
        
        # Проверяем что обновления происходили
        assert performance_tracker.stats["updates_count"] >= 5
        
        # Все позиции должны быть обновлены
        for position_id, position in performance_tracker.tracked_positions.items():
            assert position.updated_at is not None

    @pytest.mark.asyncio
    async def test_database_operations_performance(self, performance_tracker):
        """Тест производительности операций с БД"""
        num_operations = 100
        
        # Тест сохранения позиций
        start_time = time.perf_counter()
        
        save_tasks = []
        for i in range(num_operations):
            position = await performance_tracker.track_position(
                position_id=f"db_perf_{i:03d}",
                symbol="BTCUSDT", 
                side="long",
                size=Decimal("0.001"),
                entry_price=Decimal("50000.0"),
                exchange="bybit"
            )
            # Операции БД мокнуты, но структура вызовов тестируется
            save_tasks.append(performance_tracker._save_position_to_db(position))
        
        await asyncio.gather(*save_tasks)
        
        save_time = time.perf_counter() - start_time
        avg_save_time = save_time / num_operations
        
        assert avg_save_time < 0.01, f"Average save time: {avg_save_time:.4f}s"

    @pytest.mark.asyncio
    async def test_stats_calculation_performance(self, performance_tracker):
        """Тест производительности расчета статистики"""
        # Создаем много позиций с разными статусами
        num_positions = 200
        
        for i in range(num_positions):
            position = await performance_tracker.track_position(
                position_id=f"stats_perf_{i:03d}",
                symbol="BTCUSDT",
                side="long" if i % 2 == 0 else "short",
                size=Decimal("0.001"),
                entry_price=Decimal(str(50000 + i * 10)),
                exchange="bybit"
            )
            
            # Симулируем разные состояния здоровья
            position.current_price = Decimal(str(50000 + i * (10 if i % 3 == 0 else -5)))
            await performance_tracker._calculate_position_metrics(position)
            await performance_tracker._check_position_health(position)
        
        # Измеряем время расчета статистики
        start_time = time.perf_counter()
        
        # Выполняем несколько расчетов статистики
        for _ in range(10):
            stats = await performance_tracker.get_tracker_stats()
            
        end_time = time.perf_counter()
        stats_time = (end_time - start_time) / 10  # Среднее время
        
        assert stats_time < 0.05, f"Stats calculation time: {stats_time:.4f}s"
        assert stats["active_positions"] == num_positions

    @pytest.mark.asyncio
    async def test_position_removal_performance(self, performance_tracker):
        """Тест производительности удаления позиций"""
        num_positions = 100
        
        # Создаем позиции
        position_ids = []
        for i in range(num_positions):
            position = await performance_tracker.track_position(
                position_id=f"remove_perf_{i:03d}",
                symbol="BTCUSDT",
                side="long",
                size=Decimal("0.001"),
                entry_price=Decimal("50000.0"),
                exchange="bybit"
            )
            position_ids.append(position.position_id)
        
        # Измеряем время удаления
        start_time = time.perf_counter()
        
        # Удаляем все позиции
        removal_tasks = [
            performance_tracker.remove_position(pos_id, "closed")
            for pos_id in position_ids
        ]
        
        await asyncio.gather(*removal_tasks)
        
        end_time = time.perf_counter()
        removal_time = end_time - start_time
        avg_removal_time = removal_time / num_positions
        
        assert len(performance_tracker.tracked_positions) == 0
        assert avg_removal_time < 0.005, f"Average removal time: {avg_removal_time:.4f}s"
        assert removal_time < 1.0, f"Total removal time: {removal_time:.3f}s"


class TestPositionTrackerStressTests:
    """Stress тесты для Position Tracker"""

    @pytest.fixture
    async def stress_tracker(self):
        """Создает трекер для stress тестов"""
        mock_exchange_manager = AsyncMock()
        mock_exchange = AsyncMock()
        mock_exchange.fetch_ticker.return_value = {"last": 50000.0}
        mock_exchange_manager.get_exchange.return_value = mock_exchange
        
        with patch('trading.position_tracker.AsyncPGPool') as mock_pool:
            mock_pool.fetch.return_value = []
            mock_pool.execute.return_value = None
            
            return EnhancedPositionTracker(mock_exchange_manager)

    @pytest.mark.asyncio
    async def test_high_frequency_updates(self, stress_tracker):
        """Stress тест высокочастотных обновлений"""
        # Создаем позицию
        await stress_tracker.track_position(
            position_id="stress_hf_001",
            symbol="BTCUSDT",
            side="long",
            size=Decimal("0.001"),
            entry_price=Decimal("50000.0"),
            exchange="bybit"
        )
        
        # Выполняем много обновлений
        num_updates = 1000
        start_time = time.perf_counter()
        
        update_tasks = [
            stress_tracker.update_position_metrics("stress_hf_001")
            for _ in range(num_updates)
        ]
        
        results = await asyncio.gather(*update_tasks, return_exceptions=True)
        
        end_time = time.perf_counter()
        update_time = end_time - start_time
        
        successful_updates = sum(1 for r in results if r is True)
        updates_per_second = successful_updates / update_time
        
        assert successful_updates >= num_updates * 0.95  # 95% успешности
        assert updates_per_second > 100, f"Updates/sec: {updates_per_second:.1f}"

    @pytest.mark.asyncio
    async def test_massive_position_count(self, stress_tracker):
        """Stress тест с очень большим количеством позиций"""
        num_positions = 2000
        batch_size = 100
        
        total_start_time = time.perf_counter()
        
        # Создаем позиции батчами
        for batch in range(0, num_positions, batch_size):
            batch_tasks = []
            for i in range(batch, min(batch + batch_size, num_positions)):
                task = stress_tracker.track_position(
                    position_id=f"massive_{i:04d}",
                    symbol=f"PAIR{i % 100}USDT",
                    side="long" if i % 2 == 0 else "short",
                    size=Decimal(str(0.001 + (i % 1000) * 0.0001)),
                    entry_price=Decimal(str(50000 + i % 10000)),
                    exchange="bybit"
                )
                batch_tasks.append(task)
            
            await asyncio.gather(*batch_tasks)
        
        total_time = time.perf_counter() - total_start_time
        positions_per_second = num_positions / total_time
        
        assert len(stress_tracker.tracked_positions) == num_positions
        assert positions_per_second > 200, f"Positions/sec: {positions_per_second:.1f}"
        assert total_time < 15.0, f"Total time: {total_time:.1f}s"

    @pytest.mark.asyncio
    async def test_continuous_monitoring_stress(self, stress_tracker):
        """Stress тест непрерывного мониторинга"""
        # Создаем позиции
        num_positions = 50
        for i in range(num_positions):
            await stress_tracker.track_position(
                position_id=f"monitor_stress_{i:03d}",
                symbol="BTCUSDT",
                side="long",
                size=Decimal("0.001"),
                entry_price=Decimal("50000.0"),
                exchange="bybit"
            )
        
        # Запускаем интенсивный мониторинг
        stress_tracker.update_interval = 0.001  # 1ms интервал
        
        await stress_tracker.start_tracking()
        await asyncio.sleep(1.0)  # 1 секунда интенсивного мониторинга
        await stress_tracker.stop_tracking()
        
        # Проверяем что система выдержала нагрузку
        assert stress_tracker.stats["updates_count"] > 100
        assert len(stress_tracker.tracked_positions) == num_positions
        
        # Все позиции должны быть обновлены
        for position in stress_tracker.tracked_positions.values():
            assert position.updated_at is not None
            assert position.metrics is not None


if __name__ == "__main__":
    # Запуск performance тестов
    pytest.main([__file__, "-v", "--tb=short", "-s"])