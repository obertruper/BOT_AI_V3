#!/usr/bin/env python3
"""
Мониторинг состояния компонентов торговой системы

Этот скрипт:
1. Проверяет инициализацию всех компонентов торговой системы
2. Тестирует связи между компонентами
3. Диагностирует проблемы в unified_launcher и orchestrator
4. Проверяет состояние процессов и подключений
5. Мониторит очереди обработки сигналов и ордеров
"""

import asyncio
import logging
import sys
from datetime import datetime

# Добавляем путь к проекту
sys.path.insert(0, "/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3")

from database.connections import get_async_db


class TradingSystemMonitor:
    """Мониторинг торговой системы"""

    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        self.component_status = {}
        self.system_health = {
            "database": False,
            "unified_launcher": False,
            "orchestrator": False,
            "trading_engine": False,
            "signal_processor": False,
            "order_manager": False,
            "execution_engine": False,
        }

    async def run_system_monitoring(self):
        """Запуск полного мониторинга системы"""
        self.logger.info("🔍 МОНИТОРИНГ ТОРГОВОЙ СИСТЕМЫ BOT_AI_V3")
        self.logger.info("=" * 60)

        try:
            # 1. Проверка базовых компонентов
            await self._check_database_health()
            await self._check_system_imports()

            # 2. Анализ конфигурации
            await self._analyze_system_config()

            # 3. Проверка unified_launcher
            await self._check_unified_launcher()

            # 4. Диагностика торгового движка
            await self._diagnose_trading_engine()

            # 5. Проверка обработки сигналов
            await self._check_signal_processing_flow()

            # 6. Анализ API и веб-интерфейса
            await self._check_api_status()

            # 7. Итоговый отчет
            await self._generate_system_report()

        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка мониторинга: {e}")

    async def _check_database_health(self):
        """Проверка состояния базы данных"""
        self.logger.info("📊 Проверка состояния PostgreSQL...")

        try:
            async with get_async_db() as db:
                # Проверка подключения
                result = await db.execute("SELECT NOW() as current_time")
                current_time = result.scalar()
                self.system_health["database"] = True

                # Проверка таблиц и индексов
                tables_result = await db.execute(
                    """
                    SELECT table_name,
                           (SELECT COUNT(*) FROM information_schema.columns
                            WHERE table_name = t.table_name) as column_count
                    FROM information_schema.tables t
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """
                )
                tables = tables_result.fetchall()

                # Статистика данных
                stats = {}
                for table in tables:
                    count_result = await db.execute(f"SELECT COUNT(*) FROM {table.table_name}")
                    stats[table.table_name] = count_result.scalar()

                self.logger.info(f"✅ БД подключена: {current_time}")
                self.logger.info("📈 Статистика таблиц:")

                for table_name, count in stats.items():
                    self.logger.info(f"   🔸 {table_name}: {count:,} записей")

                # Критическая проверка: сигналы vs ордера
                if stats.get("signals", 0) > 100 and stats.get("orders", 0) < 10:
                    self.logger.error("❌ КРИТИЧЕСКАЯ ПРОБЛЕМА: Много сигналов, мало ордеров!")

        except Exception as e:
            self.logger.error(f"❌ Ошибка БД: {e}")
            self.system_health["database"] = False

    async def _check_system_imports(self):
        """Проверка импортов основных компонентов"""
        self.logger.info("📦 Проверка импортов компонентов...")

        imports_to_check = [
            ("unified_launcher", "unified_launcher"),
            ("SystemOrchestrator", "core.system.orchestrator"),
            ("TradingEngine", "trading.engine"),
            ("SignalProcessor", "trading.signals.signal_processor"),
            ("OrderManager", "trading.orders.order_manager"),
            ("ExecutionEngine", "trading.execution.executor"),
            ("ExchangeRegistry", "exchanges.registry"),
            ("RiskManager", "risk_management.manager"),
            ("StrategyManager", "strategies.manager"),
        ]

        for component_name, module_path in imports_to_check:
            try:
                __import__(module_path)
                self.logger.info(f"   ✅ {component_name}")
                self.component_status[component_name] = "available"
            except ImportError as e:
                self.logger.error(f"   ❌ {component_name}: {e}")
                self.component_status[component_name] = f"import_error: {e}"
            except Exception as e:
                self.logger.warning(f"   ⚠️  {component_name}: {e}")
                self.component_status[component_name] = f"error: {e}"

    async def _analyze_system_config(self):
        """Анализ конфигурации системы"""
        self.logger.info("⚙️  Анализ конфигурации системы...")

        config_files = [
            "config/system.yaml",
            "config/ml/ml_config.yaml",
            ".env",
            "requirements.txt",
        ]

        for config_file in config_files:
            try:
                import os

                if os.path.exists(config_file):
                    size = os.path.getsize(config_file)
                    modified = datetime.fromtimestamp(os.path.getmtime(config_file))
                    self.logger.info(f"   ✅ {config_file}: {size} байт (изменен: {modified})")
                else:
                    self.logger.warning(f"   ⚠️  {config_file}: файл не найден")
            except Exception as e:
                self.logger.error(f"   ❌ {config_file}: ошибка проверки - {e}")

    async def _check_unified_launcher(self):
        """Проверка unified_launcher"""
        self.logger.info("🚀 Диагностика unified_launcher...")

        try:
            # Проверяем наличие процессов
            import subprocess

            # Ищем процессы Python с unified_launcher
            result = subprocess.run(
                ["pgrep", "-f", "unified_launcher"], capture_output=True, text=True
            )

            if result.returncode == 0:
                pids = result.stdout.strip().split("\n")
                self.logger.info(f"   ✅ Найдены процессы: {pids}")
                self.system_health["unified_launcher"] = True
            else:
                self.logger.warning("   ⚠️  Процессы unified_launcher не найдены")
                self.system_health["unified_launcher"] = False

            # Проверяем порты
            port_checks = [
                ("API", 8080),
                ("Frontend", 5173),
            ]

            for name, port in port_checks:
                port_result = subprocess.run(["lsof", f"-i:{port}"], capture_output=True, text=True)

                if port_result.returncode == 0:
                    self.logger.info(f"   ✅ {name} порт {port} активен")
                else:
                    self.logger.warning(f"   ⚠️  {name} порт {port} не используется")

        except Exception as e:
            self.logger.error(f"   ❌ Ошибка проверки процессов: {e}")

    async def _diagnose_trading_engine(self):
        """Диагностика торгового движка"""
        self.logger.info("🏗️  Диагностика торгового движка...")

        try:
            # Пытаемся импортировать и создать экземпляр
            from trading.engine import TradingEngine, TradingState

            self.logger.info("   ✅ TradingEngine импортирован")

            # Проверяем состояния
            states = [state.value for state in TradingState]
            self.logger.info(f"   🔸 Доступные состояния: {states}")

            # Пытаемся создать мок-конфигурацию
            mock_config = {
                "signal_processing": {},
                "position_management": {},
                "order_management": {},
                "execution": {},
                "risk_management": {},
                "strategies": {},
                "exchanges": {},
            }

            # Проверяем создание экземпляра (без инициализации)
            try:
                # Нужен мок orchestrator
                class MockOrchestrator:
                    def get_database_manager(self):
                        return None

                engine = TradingEngine(MockOrchestrator(), mock_config)
                self.logger.info("   ✅ TradingEngine может быть создан")
                self.logger.info(f"   🔸 Начальное состояние: {engine.state.value}")
                self.system_health["trading_engine"] = True

            except Exception as e:
                self.logger.error(f"   ❌ Ошибка создания TradingEngine: {e}")
                self.system_health["trading_engine"] = False

        except ImportError as e:
            self.logger.error(f"   ❌ Ошибка импорта TradingEngine: {e}")
            self.system_health["trading_engine"] = False

    async def _check_signal_processing_flow(self):
        """Проверка потока обработки сигналов"""
        self.logger.info("📡 Диагностика обработки сигналов...")

        try:
            # Анализ существующих сигналов и их обработки
            async with get_async_db() as db:
                # Сигналы по времени
                signals_by_hour = await db.execute(
                    """
                    SELECT DATE_TRUNC('hour', created_at) as hour,
                           COUNT(*) as count,
                           signal_type
                    FROM signals
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                    GROUP BY hour, signal_type
                    ORDER BY hour DESC
                    LIMIT 10
                """
                )

                recent_signals = signals_by_hour.fetchall()

                if recent_signals:
                    self.logger.info("   📊 Сигналы за последние часы:")
                    for row in recent_signals:
                        self.logger.info(f"      {row.hour}: {row.count} {row.signal_type}")
                else:
                    self.logger.warning("   ⚠️  Нет недавних сигналов")

                # Проверка обработки - есть ли связанные ордера
                signals_with_orders = await db.execute(
                    """
                    SELECT s.id, s.symbol, s.signal_type, s.created_at,
                           COUNT(o.id) as order_count
                    FROM signals s
                    LEFT JOIN orders o ON o.extra_data::text LIKE '%signal_id": ' || s.id || '%'
                    WHERE s.created_at > NOW() - INTERVAL '1 hour'
                    GROUP BY s.id, s.symbol, s.signal_type, s.created_at
                    ORDER BY s.created_at DESC
                    LIMIT 5
                """
                )

                signal_order_links = signals_with_orders.fetchall()

                if signal_order_links:
                    self.logger.info("   🔗 Связь сигналов с ордерами:")
                    for row in signal_order_links:
                        status = "✅" if row.order_count > 0 else "❌"
                        self.logger.info(
                            f"      {status} Сигнал {row.id} ({row.signal_type}): {row.order_count} ордеров"
                        )

                # Проверяем, есть ли orphaned сигналы (без ордеров)
                orphaned_count_result = await db.execute(
                    """
                    SELECT COUNT(*) FROM signals s
                    WHERE s.created_at > NOW() - INTERVAL '6 hours'
                    AND NOT EXISTS (
                        SELECT 1 FROM orders o
                        WHERE o.extra_data::text LIKE '%signal_id": ' || s.id || '%'
                    )
                """
                )
                orphaned_count = orphaned_count_result.scalar()

                if orphaned_count > 10:
                    self.logger.error(f"   ❌ ПРОБЛЕМА: {orphaned_count} сигналов без ордеров!")
                elif orphaned_count > 0:
                    self.logger.warning(f"   ⚠️  {orphaned_count} сигналов без ордеров")
                else:
                    self.logger.info("   ✅ Все недавние сигналы имеют связанные ордера")

        except Exception as e:
            self.logger.error(f"   ❌ Ошибка анализа сигналов: {e}")

    async def _check_api_status(self):
        """Проверка состояния API"""
        self.logger.info("🌐 Проверка API и веб-интерфейса...")

        try:
            import asyncio

            import aiohttp

            # Тестируем API endpoints
            api_endpoints = [
                ("http://localhost:8080/health", "Health Check"),
                ("http://localhost:8080/api/status", "API Status"),
                ("http://localhost:8080/api/trading/status", "Trading Status"),
            ]

            timeout = aiohttp.ClientTimeout(total=5)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                for url, name in api_endpoints:
                    try:
                        async with session.get(url) as response:
                            if response.status == 200:
                                data = await response.json()
                                self.logger.info(f"   ✅ {name}: OK")
                            else:
                                self.logger.warning(f"   ⚠️  {name}: HTTP {response.status}")
                    except TimeoutError:
                        self.logger.warning(f"   ⚠️  {name}: Timeout")
                    except aiohttp.ClientConnectorError:
                        self.logger.warning(f"   ⚠️  {name}: Connection refused")
                    except Exception as e:
                        self.logger.warning(f"   ⚠️  {name}: {e}")

        except ImportError:
            self.logger.warning("   ⚠️  aiohttp не доступен для тестирования API")
        except Exception as e:
            self.logger.error(f"   ❌ Ошибка проверки API: {e}")

    async def _generate_system_report(self):
        """Генерация итогового отчета"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("📊 ИТОГОВЫЙ ОТЧЕТ СИСТЕМЫ")
        self.logger.info("=" * 60)

        # Общее состояние
        healthy_components = sum(1 for status in self.system_health.values() if status)
        total_components = len(self.system_health)
        health_percentage = (healthy_components / total_components) * 100

        self.logger.info(
            f"🏥 СОСТОЯНИЕ СИСТЕМЫ: {health_percentage:.1f}% ({healthy_components}/{total_components})"
        )

        # Детализация по компонентам
        self.logger.info("\n🔧 КОМПОНЕНТЫ:")
        for component, status in self.system_health.items():
            status_icon = "✅" if status else "❌"
            self.logger.info(f"   {status_icon} {component}")

        # Рекомендации
        self.logger.info("\n💡 РЕКОМЕНДАЦИИ:")

        if not self.system_health["database"]:
            self.logger.info("   🔸 КРИТИЧНО: Проверьте PostgreSQL на порту 5555")

        if not self.system_health["unified_launcher"]:
            self.logger.info("   🔸 Запустите: python3 unified_launcher.py")

        if not self.system_health["trading_engine"]:
            self.logger.info("   🔸 Проверьте импорты и зависимости торгового движка")

        if health_percentage < 70:
            self.logger.info("   🔸 ВНИМАНИЕ: Система требует вмешательства")
        elif health_percentage < 90:
            self.logger.info("   🔸 Система в основном работает, есть минорные проблемы")
        else:
            self.logger.info("   🔸 Система работает нормально")

        self.logger.info(f"\n⏰ Отчет сгенерирован: {datetime.now()}")
        self.logger.info("=" * 60)


class LiveSystemMonitor:
    """Мониторинг системы в реальном времени"""

    def __init__(self, interval: int = 30):
        self.interval = interval
        self.logger = logging.getLogger(f"{__name__}.live")
        self.running = False

    async def start_monitoring(self):
        """Запуск мониторинга в реальном времени"""
        self.running = True
        self.logger.info(f"🔄 Запуск live мониторинга (интервал: {self.interval}s)")

        while self.running:
            try:
                await self._check_system_pulse()
                await asyncio.sleep(self.interval)
            except KeyboardInterrupt:
                self.logger.info("⏹️  Остановка мониторинга...")
                break
            except Exception as e:
                self.logger.error(f"❌ Ошибка мониторинга: {e}")
                await asyncio.sleep(5)

    async def _check_system_pulse(self):
        """Проверка пульса системы"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        try:
            # Быстрая проверка БД
            async with get_async_db() as db:
                result = await db.execute(
                    "SELECT COUNT(*) FROM signals WHERE created_at > NOW() - INTERVAL '1 minute'"
                )
                new_signals = result.scalar()

                result = await db.execute(
                    "SELECT COUNT(*) FROM orders WHERE created_at > NOW() - INTERVAL '1 minute'"
                )
                new_orders = result.scalar()

                if new_signals > 0 or new_orders > 0:
                    self.logger.info(
                        f"[{timestamp}] 📈 Активность: +{new_signals} сигналов, +{new_orders} ордеров"
                    )
                else:
                    self.logger.info(f"[{timestamp}] 💤 Нет активности")

        except Exception as e:
            self.logger.error(f"[{timestamp}] ❌ Ошибка пульса: {e}")


async def main():
    """Главная функция"""
    import argparse

    parser = argparse.ArgumentParser(description="Мониторинг торговой системы BOT_AI_V3")
    parser.add_argument("--live", action="store_true", help="Live мониторинг")
    parser.add_argument("--interval", type=int, default=30, help="Интервал для live мониторинга")

    args = parser.parse_args()

    if args.live:
        monitor = LiveSystemMonitor(args.interval)
        await monitor.start_monitoring()
    else:
        monitor = TradingSystemMonitor()
        await monitor.run_system_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
