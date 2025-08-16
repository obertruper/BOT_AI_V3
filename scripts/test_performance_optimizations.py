#!/usr/bin/env python3
"""
Тестирование оптимизаций производительности BOT_AI_V3
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Any

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.logger import setup_logger
from core.system.performance_cache import (
    get_cache_health,
    performance_cache,
    warm_up_cache,
)
from core.system.process_manager import ProcessManager

logger = setup_logger(__name__)


class PerformanceTestSuite:
    """Тестирование оптимизаций производительности"""

    def __init__(self):
        self.results = {}
        self.process_manager = ProcessManager()

    async def run_all_tests(self) -> dict[str, Any]:
        """Запуск всех тестов"""
        logger.info("🧪 Начинаем тестирование оптимизаций производительности")
        logger.info("=" * 60)

        # Запускаем фоновые задачи кеша
        performance_cache.start_cleanup_task()

        # Тесты кеширования
        await self.test_cache_performance()
        await self.test_cache_memory_management()
        await self.test_batch_operations()

        # Тесты логирования
        await self.test_logging_performance()

        # Тесты ProcessManager
        await self.test_process_management()

        # Сводка результатов
        await self.print_summary()

        return self.results

    async def test_cache_performance(self):
        """Тест производительности кеширования"""
        logger.info("📊 Тестирование производительности кеша...")

        test_data = {}
        start_time = time.time()

        # Тест записи
        write_start = time.time()
        for i in range(1000):
            await performance_cache.set(f"test_key_{i}", f"test_value_{i}")
        write_time = time.time() - write_start

        # Тест чтения
        read_start = time.time()
        for i in range(1000):
            value = await performance_cache.get(f"test_key_{i}")
            assert value == f"test_value_{i}", f"Неверное значение для ключа test_key_{i}"
        read_time = time.time() - read_start

        # Тест batch операций
        batch_data = {f"batch_key_{i}": f"batch_value_{i}" for i in range(100)}
        batch_start = time.time()
        await performance_cache.set_many(batch_data)
        batch_time = time.time() - batch_start

        total_time = time.time() - start_time

        test_data = {
            "total_time": round(total_time, 3),
            "write_time": round(write_time, 3),
            "read_time": round(read_time, 3),
            "batch_time": round(batch_time, 3),
            "write_ops_per_sec": round(1000 / write_time, 1),
            "read_ops_per_sec": round(1000 / read_time, 1),
            "batch_ops_per_sec": round(100 / batch_time, 1),
        }

        self.results["cache_performance"] = test_data

        logger.info(f"  ✅ Запись: {test_data['write_ops_per_sec']} ops/sec")
        logger.info(f"  ✅ Чтение: {test_data['read_ops_per_sec']} ops/sec")
        logger.info(f"  ✅ Batch: {test_data['batch_ops_per_sec']} ops/sec")

    async def test_cache_memory_management(self):
        """Тест управления памятью кеша"""
        logger.info("🧠 Тестирование управления памятью...")

        # Получаем начальные статистики
        initial_stats = performance_cache.get_stats()

        # Заполняем кеш до лимита
        for i in range(performance_cache.max_size + 100):
            await performance_cache.set(f"memory_test_{i}", f"large_value_{'x' * 100}_{i}")

        # Проверяем, что размер не превышает лимит
        final_stats = performance_cache.get_stats()

        test_data = {
            "initial_size": initial_stats["size"],
            "final_size": final_stats["size"],
            "max_size": performance_cache.max_size,
            "evictions": final_stats["evictions"],
            "within_limit": final_stats["size"] <= performance_cache.max_size,
        }

        self.results["cache_memory"] = test_data

        logger.info(f"  ✅ Размер кеша: {test_data['final_size']}/{test_data['max_size']}")
        logger.info(f"  ✅ Evictions: {test_data['evictions']}")
        logger.info(f"  ✅ В пределах лимита: {test_data['within_limit']}")

    async def test_batch_operations(self):
        """Тест batch операций"""
        logger.info("📦 Тестирование batch операций...")

        # Подготавливаем операции
        operations = []
        for i in range(100):
            operations.extend(
                [
                    {"type": "set", "key": f"batch_op_{i}", "value": f"value_{i}"},
                    {"type": "get", "key": f"batch_op_{i}"},
                ]
            )

        # Выполняем batch операции
        start_time = time.time()
        results = await performance_cache.batch_update(operations)
        execution_time = time.time() - start_time

        # Проверяем результаты
        successful_ops = sum(1 for result in results if result is not None)

        test_data = {
            "total_operations": len(operations),
            "successful_operations": successful_ops,
            "execution_time": round(execution_time, 3),
            "ops_per_sec": round(len(operations) / execution_time, 1),
            "success_rate": round(successful_ops / len(operations) * 100, 1),
        }

        self.results["batch_operations"] = test_data

        logger.info(f"  ✅ Операций: {test_data['total_operations']}")
        logger.info(f"  ✅ Успешных: {test_data['successful_operations']}")
        logger.info(f"  ✅ Скорость: {test_data['ops_per_sec']} ops/sec")

    async def test_logging_performance(self):
        """Тест производительности логирования"""
        logger.info("📝 Тестирование производительности логирования...")

        test_logger = setup_logger("performance_test")

        # Тестируем различные уровни логирования
        start_time = time.time()

        for i in range(1000):
            test_logger.debug(f"Debug message {i}")
            test_logger.info(f"Info message {i}")
            if i % 10 == 0:
                test_logger.warning(f"Warning message {i}")
            if i % 100 == 0:
                test_logger.error(f"Error message {i}")

        execution_time = time.time() - start_time

        test_data = {
            "total_logs": 4000,  # 1000 debug + 1000 info + 100 warning + 10 error
            "execution_time": round(execution_time, 3),
            "logs_per_sec": round(4000 / execution_time, 1),
        }

        self.results["logging_performance"] = test_data

        logger.info(f"  ✅ Логов: {test_data['total_logs']}")
        logger.info(f"  ✅ Время: {test_data['execution_time']}с")
        logger.info(f"  ✅ Скорость: {test_data['logs_per_sec']} logs/sec")

    async def test_process_management(self):
        """Тест управления процессами"""
        logger.info("⚙️ Тестирование управления процессами...")

        await self.process_manager.initialize()

        # Тестируем запуск и остановку процесса
        start_time = time.time()

        try:
            # Запускаем простой процесс
            pid = await self.process_manager.start_component(
                name="test_process", command="sleep 5", auto_restart=False
            )

            # Ждем немного
            await asyncio.sleep(1)

            # Получаем информацию о процессе
            proc_info = self.process_manager.get_process_info("test_process")

            # Останавливаем процесс
            await self.process_manager.stop_component("test_process")

            execution_time = time.time() - start_time

            test_data = {
                "process_started": pid is not None,
                "process_info_available": proc_info is not None,
                "execution_time": round(execution_time, 3),
                "process_pid": pid,
            }

        except Exception as e:
            test_data = {
                "process_started": False,
                "process_info_available": False,
                "execution_time": round(time.time() - start_time, 3),
                "error": str(e),
            }

        self.results["process_management"] = test_data

        logger.info(f"  ✅ Процесс запущен: {test_data['process_started']}")
        logger.info(f"  ✅ Информация доступна: {test_data['process_info_available']}")
        logger.info(f"  ✅ Время выполнения: {test_data['execution_time']}с")

    async def print_summary(self):
        """Вывод сводки результатов"""
        logger.info("\n" + "=" * 60)
        logger.info("📋 СВОДКА РЕЗУЛЬТАТОВ ТЕСТИРОВАНИЯ")
        logger.info("=" * 60)

        # Оценка производительности кеша
        cache_perf = self.results.get("cache_performance", {})
        if cache_perf.get("read_ops_per_sec", 0) > 10000:
            cache_rating = "ОТЛИЧНО"
        elif cache_perf.get("read_ops_per_sec", 0) > 5000:
            cache_rating = "ХОРОШО"
        else:
            cache_rating = "ТРЕБУЕТ УЛУЧШЕНИЯ"

        logger.info(f"\n🏆 Производительность кеша: {cache_rating}")

        # Здоровье кеша
        cache_health = await get_cache_health()
        logger.info(f"💚 Здоровье кеша: {cache_health['status'].upper()}")

        # Общая оценка
        total_tests = len(self.results)
        successful_tests = sum(1 for test in self.results.values() if not test.get("error"))

        logger.info("\n📊 Общая статистика:")
        logger.info(f"  Тестов выполнено: {total_tests}")
        logger.info(f"  Успешных: {successful_tests}")
        logger.info(f"  Процент успеха: {round(successful_tests / total_tests * 100, 1)}%")

        # Рекомендации
        recommendations = cache_health.get("recommendations", [])
        if recommendations:
            logger.info("\n💡 Рекомендации:")
            for rec in recommendations:
                logger.info(f"  - {rec}")

        logger.info("\n" + "=" * 60)


async def main():
    """Главная функция"""
    logger.info("🚀 Запуск тестирования оптимизаций производительности BOT_AI_V3")

    # Прогреваем кеш
    await warm_up_cache()

    # Запускаем тесты
    test_suite = PerformanceTestSuite()
    results = await test_suite.run_all_tests()

    # Останавливаем кеш
    await performance_cache.stop()

    logger.info("✅ Тестирование завершено")

    return results


if __name__ == "__main__":
    asyncio.run(main())
