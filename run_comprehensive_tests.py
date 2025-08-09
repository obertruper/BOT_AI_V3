#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главный скрипт для запуска комплексного тестирования торговой системы

Запускает все диагностические тесты в правильном порядке и генерирует сводный отчет.
"""

import asyncio
import logging
import sys
import time
from datetime import datetime

# Добавляем путь к проекту
sys.path.insert(0, "/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3")


class MasterTestRunner:
    """Главный запускатель всех тестов"""

    def __init__(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%H:%M:%S",
        )
        self.logger = logging.getLogger(__name__)

        self.test_results = {
            "system_monitoring": {"status": "pending", "errors": [], "duration": 0},
            "comprehensive_diagnostics": {
                "status": "pending",
                "errors": [],
                "duration": 0,
            },
            "forced_signal_tests": {"status": "pending", "errors": [], "duration": 0},
        }

    async def run_all_tests(self):
        """Запуск всех тестов в оптимальном порядке"""
        self.logger.info("🚀 КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ BOT_AI_V3")
        self.logger.info("=" * 80)
        self.logger.info(f"⏰ Начало тестирования: {datetime.now()}")
        self.logger.info("=" * 80)

        start_time = time.time()

        try:
            # 1. Мониторинг системы (быстрая диагностика)
            await self._run_system_monitoring()

            # 2. Комплексная диагностика (основные тесты)
            await self._run_comprehensive_diagnostics()

            # 3. Форсированные тесты с балансом (глубокие тесты)
            await self._run_forced_signal_tests()

            # 4. Генерация сводного отчета
            await self._generate_master_report()

        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка в главном тесте: {e}")

        finally:
            total_duration = time.time() - start_time
            self.logger.info(f"⏱️  Общее время тестирования: {total_duration:.2f}s")

    async def _run_system_monitoring(self):
        """Запуск системного мониторинга"""
        self.logger.info("🔍 ЭТАП 1: Системный мониторинг")
        self.logger.info("-" * 60)

        start_time = time.time()

        try:
            from tests.trading_system_monitor import TradingSystemMonitor

            monitor = TradingSystemMonitor()
            await monitor.run_system_monitoring()

            self.test_results["system_monitoring"]["status"] = "completed"
            self.logger.info("✅ Системный мониторинг завершен")

        except Exception as e:
            self.logger.error(f"❌ Ошибка системного мониторинга: {e}")
            self.test_results["system_monitoring"]["status"] = "failed"
            self.test_results["system_monitoring"]["errors"].append(str(e))

        finally:
            self.test_results["system_monitoring"]["duration"] = (
                time.time() - start_time
            )

    async def _run_comprehensive_diagnostics(self):
        """Запуск комплексной диагностики"""
        self.logger.info("\n🔬 ЭТАП 2: Комплексная диагностика")
        self.logger.info("-" * 60)

        start_time = time.time()

        try:
            from tests.comprehensive_signal_order_tests import (
                ComprehensiveTradingDiagnostics,
            )

            diagnostics = ComprehensiveTradingDiagnostics()
            await diagnostics.run_comprehensive_tests()

            # Проверяем результаты
            if len(diagnostics.test_stats["errors"]) == 0:
                self.test_results["comprehensive_diagnostics"]["status"] = "completed"
                self.logger.info("✅ Комплексная диагностика завершена успешно")
            else:
                self.test_results["comprehensive_diagnostics"]["status"] = (
                    "completed_with_errors"
                )
                self.test_results["comprehensive_diagnostics"]["errors"] = (
                    diagnostics.test_stats["errors"]
                )
                self.logger.warning(
                    f"⚠️  Диагностика завершена с {len(diagnostics.test_stats['errors'])} ошибками"
                )

        except Exception as e:
            self.logger.error(f"❌ Ошибка комплексной диагностики: {e}")
            self.test_results["comprehensive_diagnostics"]["status"] = "failed"
            self.test_results["comprehensive_diagnostics"]["errors"].append(str(e))

        finally:
            self.test_results["comprehensive_diagnostics"]["duration"] = (
                time.time() - start_time
            )

    async def _run_forced_signal_tests(self):
        """Запуск форсированных тестов с балансом"""
        self.logger.info("\n⚡ ЭТАП 3: Форсированные тесты с балансом $150")
        self.logger.info("-" * 60)

        start_time = time.time()

        try:
            from tests.forced_signal_order_creation import ForcedSignalOrderTester

            tester = ForcedSignalOrderTester()
            await tester.run_forced_tests()

            self.test_results["forced_signal_tests"]["status"] = "completed"
            self.logger.info("✅ Форсированные тесты завершены")

        except Exception as e:
            self.logger.error(f"❌ Ошибка форсированных тестов: {e}")
            self.test_results["forced_signal_tests"]["status"] = "failed"
            self.test_results["forced_signal_tests"]["errors"].append(str(e))

        finally:
            self.test_results["forced_signal_tests"]["duration"] = (
                time.time() - start_time
            )

    async def _generate_master_report(self):
        """Генерация сводного отчета"""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("📊 СВОДНЫЙ ОТЧЕТ КОМПЛЕКСНОГО ТЕСТИРОВАНИЯ")
        self.logger.info("=" * 80)

        # Подсчет статистики
        total_tests = len(self.test_results)
        completed_tests = sum(
            1
            for result in self.test_results.values()
            if result["status"] in ["completed", "completed_with_errors"]
        )
        failed_tests = sum(
            1 for result in self.test_results.values() if result["status"] == "failed"
        )

        total_duration = sum(
            result["duration"] for result in self.test_results.values()
        )
        total_errors = sum(
            len(result["errors"]) for result in self.test_results.values()
        )

        self.logger.info("📈 ОБЩАЯ СТАТИСТИКА:")
        self.logger.info(f"   🔸 Всего тестов: {total_tests}")
        self.logger.info(f"   🔸 Завершено: {completed_tests}")
        self.logger.info(f"   🔸 Неудачных: {failed_tests}")
        self.logger.info(f"   🔸 Общее время: {total_duration:.2f}s")
        self.logger.info(f"   🔸 Общее количество ошибок: {total_errors}")

        # Детализация по тестам
        self.logger.info("\n🔍 ДЕТАЛИЗАЦИЯ:")
        for test_name, result in self.test_results.items():
            status_icon = {
                "completed": "✅",
                "completed_with_errors": "⚠️",
                "failed": "❌",
                "pending": "⏳",
            }.get(result["status"], "❓")

            self.logger.info(
                f"   {status_icon} {test_name}: {result['status']} ({result['duration']:.2f}s)"
            )

            if result["errors"]:
                self.logger.info(f"      Ошибки ({len(result['errors'])}):")
                for error in result["errors"]:
                    self.logger.info(f"        - {error}")

        # Проверка базы данных для финального анализа
        await self._final_database_analysis()

        # Рекомендации
        self.logger.info("\n💡 РЕКОМЕНДАЦИИ:")

        if failed_tests > 0:
            self.logger.info(
                "   🔸 КРИТИЧНО: Есть неудачные тесты - система требует вмешательства"
            )

        if total_errors > 10:
            self.logger.info(
                "   🔸 ВНИМАНИЕ: Много ошибок - проверьте конфигурацию системы"
            )

        if completed_tests == total_tests and total_errors == 0:
            self.logger.info("   🔸 ОТЛИЧНО: Все тесты пройдены без ошибок!")

        self.logger.info(
            "   🔸 Для live мониторинга: python3 tests/trading_system_monitor.py --live"
        )
        self.logger.info(
            "   🔸 Для повторной диагностики: python3 run_comprehensive_tests.py"
        )

        self.logger.info(f"\n⏰ Отчет сгенерирован: {datetime.now()}")
        self.logger.info("=" * 80)

    async def _final_database_analysis(self):
        """Финальный анализ базы данных"""
        try:
            from database.connections import get_async_db

            async with get_async_db() as db:
                # Проверяем результаты тестов
                test_signals_result = await db.execute(
                    "SELECT COUNT(*) FROM signals WHERE extra_data::text LIKE '%test%'"
                )
                test_signals_count = test_signals_result.scalar()

                test_orders_result = await db.execute(
                    "SELECT COUNT(*) FROM orders WHERE extra_data::text LIKE '%test%' OR extra_data::text LIKE '%forced%'"
                )
                test_orders_count = test_orders_result.scalar()

                # Общая статистика
                all_signals_result = await db.execute("SELECT COUNT(*) FROM signals")
                all_signals_count = all_signals_result.scalar()

                all_orders_result = await db.execute("SELECT COUNT(*) FROM orders")
                all_orders_count = all_orders_result.scalar()

                self.logger.info("\n📊 ФИНАЛЬНЫЙ АНАЛИЗ БД:")
                self.logger.info(f"   🔸 Тестовые сигналы: {test_signals_count}")
                self.logger.info(f"   🔸 Тестовые ордера: {test_orders_count}")
                self.logger.info(f"   🔸 Всего сигналов: {all_signals_count:,}")
                self.logger.info(f"   🔸 Всего ордеров: {all_orders_count:,}")

                if all_signals_count > 0:
                    conversion_rate = (all_orders_count / all_signals_count) * 100
                    self.logger.info(
                        f"   🔸 Конверсия сигнал→ордер: {conversion_rate:.2f}%"
                    )

                    if conversion_rate < 10:
                        self.logger.error(
                            "   ❌ КРИТИЧЕСКАЯ ПРОБЛЕМА: Низкая конверсия сигналов в ордера!"
                        )
                        self.logger.error("      Возможные причины:")
                        self.logger.error("      - TradingEngine не запущен")
                        self.logger.error(
                            "      - SignalProcessor не обрабатывает сигналы"
                        )
                        self.logger.error("      - OrderManager не создает ордера")
                        self.logger.error(
                            "      - Ошибки валидации или риск-менеджмента"
                        )
                    elif conversion_rate < 50:
                        self.logger.warning(
                            f"   ⚠️  Низкая конверсия ({conversion_rate:.1f}%) - возможны проблемы"
                        )
                    else:
                        self.logger.info(
                            f"   ✅ Хорошая конверсия ({conversion_rate:.1f}%)"
                        )

        except Exception as e:
            self.logger.error(f"❌ Ошибка финального анализа БД: {e}")


async def main():
    """Главная функция"""
    runner = MasterTestRunner()
    await runner.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
