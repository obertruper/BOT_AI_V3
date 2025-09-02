#!/usr/bin/env python3
"""
Performance тесты для Dynamic SL/TP
Измерение производительности и оптимизация
"""

import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import pytest

from trading.orders.dynamic_sltp_calculator import DynamicSLTPCalculator


@pytest.mark.performance
@pytest.mark.sltp
class TestDynamicSLTPPerformance:
    """Performance тесты для Dynamic SL/TP Calculator"""

    @pytest.fixture
    def large_dataset(self):
        """Большой датасет для тестирования производительности"""
        dates = pd.date_range(start="2024-01-01", periods=10000, freq="1min")

        # Генерируем реалистичные данные
        prices = []
        base_price = 50000
        current_price = base_price

        for i in range(10000):
            # Реалистичное изменение цены
            change = np.random.normal(0, 0.002)
            current_price *= 1 + change

            prices.append(
                {
                    "timestamp": dates[i],
                    "open": current_price,
                    "high": current_price * (1 + abs(np.random.normal(0, 0.001))),
                    "low": current_price * (1 - abs(np.random.normal(0, 0.001))),
                    "close": current_price * (1 + np.random.normal(0, 0.0005)),
                    "volume": np.random.uniform(100, 1000),
                }
            )

        return pd.DataFrame(prices)

    @pytest.mark.asyncio
    async def test_single_calculation_speed(self, large_dataset):
        """Тест скорости одного расчета на большом датасете"""
        calculator = DynamicSLTPCalculator()

        # Берем последние 1000 свечей
        candles = large_dataset.tail(1000)
        current_price = 50000

        # Измеряем время выполнения
        start_time = time.perf_counter()

        result = calculator.calculate_dynamic_levels(
            current_price=current_price, candles=candles, confidence=0.75, signal_type="BUY"
        )

        end_time = time.perf_counter()
        execution_time = end_time - start_time

        # Проверки производительности
        assert result is not None
        assert execution_time < 0.1, f"Расчет занял {execution_time:.4f}s, должен быть < 0.1s"

        print(f"\n📊 Single calculation time: {execution_time * 1000:.2f}ms")

    @pytest.mark.asyncio
    async def test_batch_calculations(self, large_dataset):
        """Тест пакетной обработки множества символов"""
        calculator = DynamicSLTPCalculator()

        # Симулируем 50 различных символов
        symbols = [f"SYMBOL{i}USDT" for i in range(50)]
        candles = large_dataset.tail(100)  # Последние 100 свечей для каждого

        results = []

        # Измеряем время пакетной обработки
        start_time = time.perf_counter()

        for symbol in symbols:
            # Немного изменяем цену для каждого символа
            current_price = 50000 * (1 + np.random.uniform(-0.1, 0.1))

            result = calculator.calculate_dynamic_levels(
                current_price=current_price,
                candles=candles,
                confidence=np.random.uniform(0.5, 0.95),
                signal_type=np.random.choice(["BUY", "SELL"]),
            )
            results.append(result)

        end_time = time.perf_counter()
        total_time = end_time - start_time
        avg_time = total_time / len(symbols)

        # Проверки
        assert len(results) == 50
        assert total_time < 2.0, f"Batch processing took {total_time:.2f}s, should be < 2s"
        assert avg_time < 0.04, f"Average time per symbol: {avg_time:.4f}s, should be < 0.04s"

        print("\n📊 Batch processing stats:")
        print(f"   Total symbols: {len(symbols)}")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Average per symbol: {avg_time * 1000:.2f}ms")
        print(f"   Throughput: {len(symbols) / total_time:.1f} symbols/sec")

    @pytest.mark.asyncio
    async def test_parallel_processing(self, large_dataset):
        """Тест параллельной обработки"""
        calculator = DynamicSLTPCalculator()
        candles = large_dataset.tail(100)

        # Функция для параллельного выполнения
        def calculate_for_symbol(symbol_data):
            symbol, price, confidence, signal_type = symbol_data
            return calculator.calculate_dynamic_levels(
                current_price=price, candles=candles, confidence=confidence, signal_type=signal_type
            )

        # Подготовка данных для 100 символов
        symbols_data = [
            (
                f"SYMBOL{i}USDT",
                50000 * (1 + np.random.uniform(-0.1, 0.1)),
                np.random.uniform(0.5, 0.95),
                np.random.choice(["BUY", "SELL"]),
            )
            for i in range(100)
        ]

        # Последовательное выполнение
        start_seq = time.perf_counter()
        seq_results = [calculate_for_symbol(data) for data in symbols_data]
        seq_time = time.perf_counter() - start_seq

        # Параллельное выполнение с ThreadPoolExecutor
        start_parallel = time.perf_counter()
        with ThreadPoolExecutor(max_workers=4) as executor:
            parallel_results = list(executor.map(calculate_for_symbol, symbols_data))
        parallel_time = time.perf_counter() - start_parallel

        # Расчет ускорения
        speedup = seq_time / parallel_time

        # Проверки
        assert len(parallel_results) == 100
        assert speedup > 1.5, f"Parallel speedup: {speedup:.2f}x, expected > 1.5x"

        print("\n⚡ Parallel processing performance:")
        print(f"   Sequential time: {seq_time:.2f}s")
        print(f"   Parallel time: {parallel_time:.2f}s")
        print(f"   Speedup: {speedup:.2f}x")
        print(f"   Efficiency: {(speedup / 4) * 100:.1f}%")

    @pytest.mark.asyncio
    async def test_memory_usage(self, large_dataset):
        """Тест потребления памяти"""
        calculator = DynamicSLTPCalculator()

        # Запускаем трейсинг памяти
        tracemalloc.start()

        # Начальный снимок
        snapshot_start = tracemalloc.take_snapshot()

        # Выполняем 100 расчетов
        results = []
        for i in range(100):
            candles = large_dataset.iloc[i * 100 : (i + 1) * 100]  # Разные окна данных
            result = calculator.calculate_dynamic_levels(
                current_price=50000, candles=candles, confidence=0.75, signal_type="BUY"
            )
            results.append(result)

        # Конечный снимок
        snapshot_end = tracemalloc.take_snapshot()

        # Анализ разницы
        top_stats = snapshot_end.compare_to(snapshot_start, "lineno")

        # Подсчет общего потребления
        total_memory = sum(stat.size_diff for stat in top_stats) / 1024 / 1024  # MB

        tracemalloc.stop()

        # Проверки
        assert total_memory < 50, f"Memory usage: {total_memory:.2f}MB, should be < 50MB"

        print("\n💾 Memory usage stats:")
        print(f"   Total allocated: {total_memory:.2f}MB")
        print(f"   Per calculation: {total_memory / 100:.3f}MB")

    @pytest.mark.asyncio
    async def test_cache_effectiveness(self):
        """Тест эффективности кэширования"""
        calculator = DynamicSLTPCalculator()

        # Создаем одинаковые данные
        dates = pd.date_range(start="2024-01-01", periods=100, freq="1min")
        candles = pd.DataFrame(
            {
                "timestamp": dates,
                "open": [50000] * 100,
                "high": [50100] * 100,
                "low": [49900] * 100,
                "close": [50050] * 100,
                "volume": [100] * 100,
            }
        )

        # Первый расчет (холодный кэш)
        start_cold = time.perf_counter()
        result1 = calculator.calculate_dynamic_levels(
            current_price=50000, candles=candles, confidence=0.75, signal_type="BUY"
        )
        cold_time = time.perf_counter() - start_cold

        # Повторный расчет с теми же данными (теплый кэш)
        start_warm = time.perf_counter()
        result2 = calculator.calculate_dynamic_levels(
            current_price=50000, candles=candles, confidence=0.75, signal_type="BUY"
        )
        warm_time = time.perf_counter() - start_warm

        # Кэш должен ускорять повторные расчеты
        cache_speedup = cold_time / warm_time if warm_time > 0 else 1

        print("\n🚀 Cache effectiveness:")
        print(f"   Cold cache: {cold_time * 1000:.2f}ms")
        print(f"   Warm cache: {warm_time * 1000:.2f}ms")
        print(f"   Speedup: {cache_speedup:.2f}x")

        # Результаты должны быть идентичными
        assert result1["stop_loss_pct"] == result2["stop_loss_pct"]
        assert result1["take_profit_pct"] == result2["take_profit_pct"]

    @pytest.mark.asyncio
    async def test_stress_continuous_calculation(self, large_dataset):
        """Стресс-тест: непрерывные расчеты в течение времени"""
        calculator = DynamicSLTPCalculator()
        candles = large_dataset.tail(100)

        duration = 5  # секунд
        calculations = 0
        errors = 0

        start_time = time.time()
        end_time = start_time + duration

        while time.time() < end_time:
            try:
                # Случайные параметры для каждого расчета
                result = calculator.calculate_dynamic_levels(
                    current_price=50000 * (1 + np.random.uniform(-0.05, 0.05)),
                    candles=candles,
                    confidence=np.random.uniform(0.4, 0.95),
                    signal_type=np.random.choice(["BUY", "SELL"]),
                )
                calculations += 1
            except Exception as e:
                errors += 1
                print(f"Error during stress test: {e}")

        actual_duration = time.time() - start_time
        rate = calculations / actual_duration

        # Проверки
        assert errors == 0, f"Had {errors} errors during stress test"
        assert rate > 50, f"Calculation rate: {rate:.1f}/sec, expected > 50/sec"

        print("\n🔥 Stress test results:")
        print(f"   Duration: {actual_duration:.1f}s")
        print(f"   Total calculations: {calculations}")
        print(f"   Rate: {rate:.1f} calc/sec")
        print(f"   Errors: {errors}")

    @pytest.mark.asyncio
    async def test_compare_with_fixed_sltp(self):
        """Сравнение производительности с фиксированными SL/TP"""
        calculator = DynamicSLTPCalculator()

        # Подготовка данных
        dates = pd.date_range(start="2024-01-01", periods=100, freq="1min")
        candles = pd.DataFrame(
            {
                "timestamp": dates,
                "open": np.random.uniform(49000, 51000, 100),
                "high": np.random.uniform(49500, 51500, 100),
                "low": np.random.uniform(48500, 50500, 100),
                "close": np.random.uniform(49000, 51000, 100),
                "volume": np.random.uniform(100, 1000, 100),
            }
        )

        # Фиксированные SL/TP (простой расчет)
        def calculate_fixed_sltp(current_price, signal_type):
            sl_pct = 1.5
            tp_pct = 4.5

            if signal_type == "BUY":
                sl_price = current_price * (1 - sl_pct / 100)
                tp_price = current_price * (1 + tp_pct / 100)
            else:
                sl_price = current_price * (1 + sl_pct / 100)
                tp_price = current_price * (1 - tp_pct / 100)

            return {
                "stop_loss_pct": sl_pct,
                "take_profit_pct": tp_pct,
                "stop_loss_price": sl_price,
                "take_profit_price": tp_price,
            }

        iterations = 1000

        # Измерение фиксированных SL/TP
        start_fixed = time.perf_counter()
        for _ in range(iterations):
            fixed_result = calculate_fixed_sltp(50000, "BUY")
        fixed_time = time.perf_counter() - start_fixed

        # Измерение динамических SL/TP
        start_dynamic = time.perf_counter()
        for _ in range(iterations):
            dynamic_result = calculator.calculate_dynamic_levels(
                current_price=50000, candles=candles, confidence=0.75, signal_type="BUY"
            )
        dynamic_time = time.perf_counter() - start_dynamic

        # Расчет overhead
        overhead = (dynamic_time / fixed_time) - 1

        print("\n📊 Performance comparison:")
        print(f"   Fixed SL/TP: {fixed_time:.3f}s for {iterations} iterations")
        print(f"   Dynamic SL/TP: {dynamic_time:.3f}s for {iterations} iterations")
        print(f"   Overhead: {overhead * 100:.1f}%")
        print(f"   Dynamic is {dynamic_time / fixed_time:.1f}x slower")

        # Dynamic должен быть не более чем в 10 раз медленнее
        assert dynamic_time / fixed_time < 10, "Dynamic SL/TP too slow compared to fixed"
