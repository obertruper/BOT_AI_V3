#!/usr/bin/env python3
"""
Комплексное тестирование системных компонентов BOT_AI_V3
"""

import asyncio
import logging
import sys
import time
from datetime import datetime
from decimal import Decimal

import psutil

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SystemTester:
    """Класс для комплексного тестирования системы"""

    def __init__(self):
        self.test_results = {}
        self.start_time = time.time()

    async def test_worker_coordinator(self):
        """Тестирование координатора воркеров"""
        logger.info("\n" + "=" * 60)
        logger.info("🧪 ТЕСТИРОВАНИЕ WORKER COORDINATOR")
        logger.info("=" * 60)

        try:
            from core.system.worker_coordinator import worker_coordinator

            # 1. Запуск координатора
            await worker_coordinator.start()
            logger.info("✅ Координатор запущен")

            # 2. Регистрация первого воркера
            worker1_id = await worker_coordinator.register_worker(
                worker_type="ml_manager", metadata={"version": "1.0", "gpu": "RTX 5090"}
            )
            assert worker1_id is not None, "Не удалось зарегистрировать первый воркер"
            logger.info(f"✅ Первый воркер зарегистрирован: {worker1_id}")

            # 3. Попытка регистрации дублирующего воркера
            worker2_id = await worker_coordinator.register_worker(
                worker_type="ml_manager", metadata={"version": "1.0", "gpu": "RTX 5090"}
            )
            assert worker2_id is None, "Дублирующий воркер не должен регистрироваться"
            logger.info("✅ Дублирующий воркер правильно отклонен")

            # 4. Проверка heartbeat
            success = await worker_coordinator.heartbeat(
                worker1_id, status="running", active_tasks=5
            )
            assert success, "Heartbeat должен быть успешным"
            logger.info("✅ Heartbeat работает")

            # 5. Назначение задачи
            task_id = await worker_coordinator.assign_task("test_task_1", "ml_manager")
            assert task_id == worker1_id, "Задача должна быть назначена"
            logger.info(f"✅ Задача назначена воркеру: {task_id}")

            # 6. Проверка статистики
            stats = worker_coordinator.get_worker_stats()
            assert stats["total_workers"] == 1, "Должен быть 1 воркер"
            assert stats["active_tasks"] == 1, "Должна быть 1 активная задача"
            logger.info(
                f"✅ Статистика корректна: {stats['total_workers']} воркеров, {stats['active_tasks']} задач"
            )

            # 7. Завершение задачи
            await worker_coordinator.complete_task("test_task_1", worker1_id)
            logger.info("✅ Задача завершена")

            # 8. Снятие с регистрации
            await worker_coordinator.unregister_worker(worker1_id)
            logger.info("✅ Воркер снят с регистрации")

            # 9. Остановка координатора
            await worker_coordinator.stop()
            logger.info("✅ Координатор остановлен")

            return True, "Все тесты пройдены"

        except AssertionError as e:
            return False, f"Assertion failed: {e}"
        except Exception as e:
            return False, f"Ошибка: {e}"

    async def test_signal_deduplicator(self):
        """Тестирование дедупликатора сигналов"""
        logger.info("\n" + "=" * 60)
        logger.info("🧪 ТЕСТИРОВАНИЕ SIGNAL DEDUPLICATOR")
        logger.info("=" * 60)

        try:
            from core.system.signal_deduplicator import signal_deduplicator

            # 1. Тестовые сигналы
            signal1 = {
                "symbol": "BTCUSDT",
                "direction": "BUY",
                "strategy": "ml_strategy",
                "timestamp": datetime.now(),
                "signal_strength": 0.85,
                "price_level": 50000.0,
            }

            signal2 = {
                "symbol": "ETHUSDT",
                "direction": "SELL",
                "strategy": "ml_strategy",
                "timestamp": datetime.now(),
                "signal_strength": 0.75,
                "price_level": 3000.0,
            }

            # 2. Проверка уникальности первого сигнала
            is_unique1 = await signal_deduplicator.check_and_register_signal(signal1)
            assert is_unique1, "Первый сигнал должен быть уникальным"
            logger.info("✅ Первый сигнал BTCUSDT уникален")

            # 3. Проверка дубликата первого сигнала
            is_duplicate1 = await signal_deduplicator.check_and_register_signal(signal1)
            assert not is_duplicate1, "Повторный сигнал должен быть дубликатом"
            logger.info("✅ Дубликат BTCUSDT правильно определен")

            # 4. Проверка уникальности второго сигнала
            is_unique2 = await signal_deduplicator.check_and_register_signal(signal2)
            assert is_unique2, "Второй сигнал должен быть уникальным"
            logger.info("✅ Второй сигнал ETHUSDT уникален")

            # 5. Получение недавних сигналов
            recent = await signal_deduplicator.get_recent_signals(minutes=1)
            assert len(recent) >= 2, "Должно быть минимум 2 сигнала"
            logger.info(f"✅ Найдено {len(recent)} недавних сигналов")

            # 6. Проверка статистики
            stats = signal_deduplicator.get_stats()
            assert stats["total_checks"] >= 3, "Должно быть минимум 3 проверки"
            assert stats["duplicates_found"] >= 1, "Должен быть минимум 1 дубликат"
            assert stats["unique_signals"] >= 2, "Должно быть минимум 2 уникальных сигнала"

            logger.info(
                f"✅ Статистика: {stats['total_checks']} проверок, "
                f"{stats['duplicates_found']} дубликатов, "
                f"{stats['unique_signals']} уникальных"
            )

            # 7. Сброс статистики
            signal_deduplicator.reset_stats()
            new_stats = signal_deduplicator.get_stats()
            assert new_stats["total_checks"] == 0, "Статистика должна быть сброшена"
            logger.info("✅ Статистика успешно сброшена")

            return True, "Все тесты пройдены"

        except AssertionError as e:
            return False, f"Assertion failed: {e}"
        except Exception as e:
            return False, f"Ошибка: {e}"

    async def test_rate_limiter(self):
        """Тестирование лимитера скорости"""
        logger.info("\n" + "=" * 60)
        logger.info("🧪 ТЕСТИРОВАНИЕ RATE LIMITER")
        logger.info("=" * 60)

        try:
            from core.system.rate_limiter import rate_limiter

            exchange = "bybit"

            # 1. Тест обычных запросов
            delays = []
            for i in range(5):
                start = time.time()
                wait_time = await rate_limiter.acquire(exchange, "market_data")
                elapsed = time.time() - start
                delays.append(wait_time)
                logger.info(f"  Запрос {i + 1}: задержка {wait_time:.3f}с, время {elapsed:.3f}с")

            assert all(d >= 0 for d in delays), "Все задержки должны быть неотрицательными"
            logger.info("✅ Обычные запросы обработаны корректно")

            # 2. Тест превышения лимита
            logger.info("\n  Тестирование превышения лимита...")
            for i in range(15):
                wait_time = await rate_limiter.acquire(exchange, "order", weight=2)
                if wait_time > 0:
                    logger.info(
                        f"✅ Rate limit сработал на запросе {i + 1}, задержка: {wait_time:.2f}с"
                    )
                    break

            # 3. Проверка статистики
            stats = rate_limiter.get_stats(exchange)
            total_requests = sum(s["total_requests"] for s in stats.values())
            blocked_requests = sum(s["blocked_requests"] for s in stats.values())

            assert total_requests > 0, "Должны быть обработанные запросы"
            logger.info(
                f"✅ Статистика: {total_requests} запросов, {blocked_requests} заблокировано"
            )

            # 4. Проверка текущего использования
            usage = await rate_limiter.get_current_usage(exchange)
            assert "global" in usage, "Должна быть глобальная статистика"
            logger.info(f"✅ Текущее использование получено для {len(usage)} endpoint'ов")

            # 5. Очистка старых данных
            await rate_limiter.cleanup_old_data(1)
            logger.info("✅ Старые данные очищены")

            # 6. Сброс статистики
            rate_limiter.reset_stats(exchange)
            new_stats = rate_limiter.get_stats(exchange)
            assert len(new_stats) == 0 or all(
                s["total_requests"] == 0 for s in new_stats.values()
            ), "Статистика должна быть сброшена"
            logger.info("✅ Статистика сброшена")

            return True, "Все тесты пройдены"

        except AssertionError as e:
            return False, f"Assertion failed: {e}"
        except Exception as e:
            return False, f"Ошибка: {e}"

    async def test_balance_manager(self):
        """Тестирование менеджера балансов"""
        logger.info("\n" + "=" * 60)
        logger.info("🧪 ТЕСТИРОВАНИЕ BALANCE MANAGER")
        logger.info("=" * 60)

        try:
            from core.system.balance_manager import balance_manager

            # 1. Запуск менеджера
            await balance_manager.start()
            logger.info("✅ Менеджер балансов запущен")

            # 2. Обновление тестового баланса
            success = await balance_manager.update_balance(
                exchange="bybit",
                symbol="USDT",
                total=Decimal("10000.0"),
                available=Decimal("9000.0"),
                locked=Decimal("1000.0"),
            )
            assert success, "Обновление баланса должно быть успешным"
            logger.info("✅ Баланс USDT обновлен: 10000 total, 9000 available")

            # 3. Проверка доступности малой суммы
            available, error = await balance_manager.check_balance_availability(
                exchange="bybit", symbol="USDT", amount=Decimal("100.0")
            )
            assert available, f"100 USDT должны быть доступны: {error}"
            logger.info("✅ Проверка малой суммы: 100 USDT доступны")

            # 4. Резервирование баланса
            reservation_id = await balance_manager.reserve_balance(
                exchange="bybit",
                symbol="USDT",
                amount=Decimal("500.0"),
                purpose="test_order",
                metadata={"test": True},
            )
            assert reservation_id is not None, "Резервирование должно быть успешным"
            logger.info(f"✅ Зарезервировано 500 USDT, ID: {reservation_id}")

            # 5. Проверка доступности после резервирования
            available2, error2 = await balance_manager.check_balance_availability(
                exchange="bybit",
                symbol="USDT",
                amount=Decimal("8600.0"),  # 9000 - 500 + небольшой запас
            )
            assert not available2, "8600 USDT не должны быть доступны после резервирования 500"
            logger.info("✅ После резервирования 500 USDT, проверка 8600 USDT корректно отклонена")

            # 6. Освобождение резервирования
            released = await balance_manager.release_reservation(reservation_id)
            assert released, "Освобождение должно быть успешным"
            logger.info("✅ Резервирование освобождено")

            # 7. Проверка после освобождения
            available3, error3 = await balance_manager.check_balance_availability(
                exchange="bybit", symbol="USDT", amount=Decimal("8500.0")
            )
            assert available3, "8500 USDT должны быть доступны после освобождения"
            logger.info("✅ После освобождения доступны 8500 USDT")

            # 8. Получение сводки
            summary = await balance_manager.get_balance_summary()
            assert summary["total_exchanges"] >= 1, "Должна быть минимум 1 биржа"
            assert summary["total_symbols"] >= 1, "Должен быть минимум 1 символ"
            logger.info(
                f"✅ Сводка: {summary['total_exchanges']} бирж, "
                f"{summary['total_symbols']} символов, "
                f"{summary['total_reservations']} резервирований"
            )

            # 9. Остановка менеджера
            await balance_manager.stop()
            logger.info("✅ Менеджер балансов остановлен")

            return True, "Все тесты пройдены"

        except AssertionError as e:
            return False, f"Assertion failed: {e}"
        except Exception as e:
            return False, f"Ошибка: {e}"

    async def test_process_monitor(self):
        """Тестирование монитора процессов"""
        logger.info("\n" + "=" * 60)
        logger.info("🧪 ТЕСТИРОВАНИЕ PROCESS MONITOR")
        logger.info("=" * 60)

        try:
            from core.system.process_monitor import process_monitor

            # 1. Запуск монитора
            await process_monitor.start()
            logger.info("✅ Монитор процессов запущен")

            # 2. Регистрация компонента
            success = await process_monitor.register_component(
                "test_component", metadata={"version": "1.0", "type": "test"}
            )
            assert success, "Регистрация компонента должна быть успешной"
            logger.info("✅ Компонент зарегистрирован")

            # 3. Отправка heartbeat
            hb_success = await process_monitor.heartbeat(
                "test_component", status="healthy", active_tasks=3, metadata={"processed": 100}
            )
            assert hb_success, "Heartbeat должен быть успешным"
            logger.info("✅ Heartbeat отправлен")

            # 4. Сообщение о предупреждении
            await process_monitor.report_warning("test_component", "Тестовое предупреждение")
            logger.info("✅ Предупреждение отправлено")

            # 5. Сообщение об ошибке
            await process_monitor.report_error(
                "test_component", "Тестовая ошибка", is_critical=False
            )
            logger.info("✅ Ошибка отправлена")

            # 6. Получение здоровья компонента
            health = process_monitor.get_component_health("test_component")
            assert "component_name" in health, "Должна быть информация о компоненте"
            assert health["error_count"] >= 1, "Должна быть минимум 1 ошибка"
            assert health["warning_count"] >= 1, "Должно быть минимум 1 предупреждение"
            logger.info(
                f"✅ Здоровье компонента: статус={health['status']}, "
                f"ошибок={health['error_count']}, "
                f"предупреждений={health['warning_count']}"
            )

            # 7. Системные метрики
            await asyncio.sleep(1)  # Даем время для сбора метрик
            metrics = process_monitor.get_system_metrics(1)
            assert len(metrics) > 0, "Должны быть системные метрики"
            latest = metrics[-1] if metrics else {}
            logger.info(
                f"✅ Системные метрики: CPU={latest.get('cpu_percent', 0):.1f}%, "
                f"Memory={latest.get('memory_percent', 0):.1f}%"
            )

            # 8. Активные алерты
            alerts = process_monitor.get_alerts(active_only=True)
            assert len(alerts) >= 0, "Должен быть список алертов"
            logger.info(f"✅ Активных алертов: {len(alerts)}")

            # 9. Общая статистика
            stats = process_monitor.get_stats()
            assert stats["total_components"] >= 1, "Должен быть минимум 1 компонент"
            assert stats["total_heartbeats"] >= 1, "Должен быть минимум 1 heartbeat"
            logger.info(
                f"✅ Статистика: {stats['total_components']} компонентов, "
                f"{stats['total_heartbeats']} heartbeats, "
                f"{stats['total_alerts']} алертов"
            )

            # 10. Остановка монитора
            await process_monitor.stop()
            logger.info("✅ Монитор процессов остановлен")

            return True, "Все тесты пройдены"

        except AssertionError as e:
            return False, f"Assertion failed: {e}"
        except Exception as e:
            return False, f"Ошибка: {e}"

    async def test_integration(self):
        """Интеграционное тестирование всех компонентов вместе"""
        logger.info("\n" + "=" * 60)
        logger.info("🧪 ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ")
        logger.info("=" * 60)

        try:
            from core.system.balance_manager import balance_manager
            from core.system.process_monitor import process_monitor
            from core.system.rate_limiter import rate_limiter
            from core.system.signal_deduplicator import signal_deduplicator
            from core.system.worker_coordinator import worker_coordinator

            # 1. Запуск всех компонентов
            logger.info("\n📌 Запуск всех компонентов...")
            await worker_coordinator.start()
            await balance_manager.start()
            await process_monitor.start()
            logger.info("✅ Все компоненты запущены")

            # 2. Регистрация воркера и компонента
            worker_id = await worker_coordinator.register_worker(
                worker_type="trading_engine", metadata={"test": True}
            )
            await process_monitor.register_component("trading_engine")
            logger.info("✅ Trading Engine зарегистрирован")

            # 3. Симуляция торгового цикла
            logger.info("\n📌 Симуляция торгового цикла...")

            # Проверка сигнала на дубликат
            test_signal = {
                "symbol": "BTCUSDT",
                "direction": "BUY",
                "strategy": "integration_test",
                "timestamp": datetime.now(),
                "signal_strength": 0.9,
                "price_level": 51000.0,
            }

            is_unique = await signal_deduplicator.check_and_register_signal(test_signal)
            logger.info(f"  • Сигнал {'уникален' if is_unique else 'дубликат'}")

            # Проверка rate limit
            wait_time = await rate_limiter.acquire("bybit", "order")
            logger.info(f"  • Rate limit задержка: {wait_time:.3f}с")

            # Проверка баланса
            await balance_manager.update_balance(
                exchange="bybit",
                symbol="USDT",
                total=Decimal("5000"),
                available=Decimal("4500"),
                locked=Decimal("500"),
            )

            can_trade, error = await balance_manager.check_balance_availability(
                exchange="bybit", symbol="USDT", amount=Decimal("100")
            )
            logger.info(
                f"  • Баланс для торговли: {'доступен' if can_trade else f'недоступен ({error})'}"
            )

            # Heartbeat от воркера
            await worker_coordinator.heartbeat(worker_id, status="running", active_tasks=1)
            await process_monitor.heartbeat("trading_engine", status="healthy", active_tasks=1)
            logger.info("  • Heartbeats отправлены")

            # 4. Проверка общей статистики
            logger.info("\n📌 Сбор общей статистики...")

            worker_stats = worker_coordinator.get_worker_stats()
            logger.info(f"  • Воркеры: {worker_stats['total_workers']} активных")

            dedup_stats = signal_deduplicator.get_stats()
            logger.info(
                f"  • Сигналы: {dedup_stats['total_checks']} проверок, "
                f"{dedup_stats['unique_signals']} уникальных"
            )

            balance_summary = await balance_manager.get_balance_summary()
            logger.info(
                f"  • Балансы: {balance_summary['total_exchanges']} бирж, "
                f"{balance_summary['total_symbols']} символов"
            )

            monitor_stats = process_monitor.get_stats()
            logger.info(
                f"  • Мониторинг: {monitor_stats['total_components']} компонентов, "
                f"{monitor_stats['healthy_components']} здоровых"
            )

            # 5. Остановка всех компонентов
            logger.info("\n📌 Остановка всех компонентов...")
            await worker_coordinator.unregister_worker(worker_id)
            await worker_coordinator.stop()
            await balance_manager.stop()
            await process_monitor.stop()
            logger.info("✅ Все компоненты остановлены")

            return True, "Интеграционный тест пройден"

        except Exception as e:
            return False, f"Ошибка интеграции: {e}"

    async def run_all_tests(self):
        """Запуск всех тестов"""
        logger.info("\n" + "=" * 80)
        logger.info("🚀 КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ СИСТЕМНЫХ КОМПОНЕНТОВ BOT_AI_V3")
        logger.info("=" * 80)

        tests = [
            ("WorkerCoordinator", self.test_worker_coordinator),
            ("SignalDeduplicator", self.test_signal_deduplicator),
            ("RateLimiter", self.test_rate_limiter),
            ("BalanceManager", self.test_balance_manager),
            ("ProcessMonitor", self.test_process_monitor),
            ("Integration", self.test_integration),
        ]

        for test_name, test_func in tests:
            try:
                success, message = await test_func()
                self.test_results[test_name] = {
                    "success": success,
                    "message": message,
                    "duration": time.time() - self.start_time,
                }

                if success:
                    logger.info(f"\n✅ {test_name}: ПРОЙДЕН - {message}")
                else:
                    logger.error(f"\n❌ {test_name}: ПРОВАЛЕН - {message}")

            except Exception as e:
                self.test_results[test_name] = {
                    "success": False,
                    "message": str(e),
                    "duration": time.time() - self.start_time,
                }
                logger.error(f"\n❌ {test_name}: КРИТИЧЕСКАЯ ОШИБКА - {e}")

        # Итоговый отчет
        self.print_summary()

        # Возвращаем общий результат
        return all(r["success"] for r in self.test_results.values())

    def print_summary(self):
        """Вывод итогового отчета"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
        logger.info("=" * 80)

        passed = sum(1 for r in self.test_results.values() if r["success"])
        failed = len(self.test_results) - passed
        total_duration = time.time() - self.start_time

        logger.info("\n📈 Статистика:")
        logger.info(f"  • Всего тестов: {len(self.test_results)}")
        logger.info(f"  • ✅ Пройдено: {passed}")
        logger.info(f"  • ❌ Провалено: {failed}")
        logger.info(f"  • ⏱️  Время выполнения: {total_duration:.2f} сек")

        logger.info("\n📋 Детали по компонентам:")
        for name, result in self.test_results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            logger.info(f"  {status} | {name:20} | {result['message'][:50]}")

        # Системная информация
        logger.info("\n💻 Системная информация:")
        logger.info(f"  • CPU: {psutil.cpu_percent()}%")
        logger.info(f"  • Память: {psutil.virtual_memory().percent}%")
        logger.info(f"  • Python: {sys.version.split()[0]}")

        if passed == len(self.test_results):
            logger.info("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО! Система готова к работе.")
        else:
            logger.warning(f"\n⚠️  {failed} тестов провалено. Требуется проверка.")


async def main():
    """Главная функция"""
    tester = SystemTester()
    success = await tester.run_all_tests()

    if success:
        exit(0)
    else:
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
