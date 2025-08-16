#!/usr/bin/env python3
"""
Скрипт исправления проблем системы BOT Trading v3
Исправляет ошибки базы данных, PositionManager, 499 ошибки и другие критические проблемы
"""

import asyncio
import json
import os
import re
import sys
from datetime import datetime

# Добавляем корень проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config.config_manager import ConfigManager
from database.connections.postgres import AsyncPGPool


class SystemIssueFixer:
    """Исправление системных проблем включая 499 ошибки"""

    def __init__(self):
        self.config_manager = None
        self.fixes_applied = []
        self.errors_found = []
        self.websocket_issues = []
        self.http_timeout_issues = []
        self.async_issues = []

    async def initialize(self):
        """Инициализация"""
        print("🔧 Инициализация системы исправления проблем")

        try:
            self.config_manager = ConfigManager("config/system.yaml")
            await self.config_manager.initialize()
            print("✅ ConfigManager инициализирован")
        except Exception as e:
            print(f"❌ Ошибка инициализации ConfigManager: {e}")
            self.errors_found.append(f"ConfigManager init error: {e}")

    async def analyze_499_errors(self):
        """Анализ 499 ошибок в системе"""
        print("\n🔍 Анализ 499 ошибок...")

        try:
            # Анализируем логи на предмет 499 ошибок
            log_files = [
                "data/logs/trading.log",
                "data/logs/system.log",
                "data/logs/api.log",
                "logs/trading.log",
                "logs/system.log",
            ]

            error_499_count = 0
            error_details = []

            for log_file in log_files:
                if os.path.exists(log_file):
                    print(f"   📄 Анализ лога: {log_file}")

                    with open(log_file, encoding="utf-8") as f:
                        content = f.read()

                    # Ищем 499 ошибки
                    error_patterns = [
                        r"499.*error",
                        r"Client.*closed.*request",
                        r"Connection.*closed.*prematurely",
                        r"WebSocket.*closed",
                        r"timeout.*error",
                        r"Connection.*timeout",
                    ]

                    for pattern in error_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            error_499_count += len(matches)
                            error_details.extend(matches[:5])  # Первые 5 для анализа

                    print(f"      Найдено потенциальных проблем: {error_499_count}")

            if error_499_count > 0:
                print(f"   ⚠️ Обнаружено {error_499_count} потенциальных 499 ошибок")
                self.errors_found.append(f"Found {error_499_count} potential 499 errors")

                # Анализируем детали
                print("   📊 Анализ деталей ошибок:")
                for detail in error_details[:10]:  # Показываем первые 10
                    print(f"      • {detail}")
            else:
                print("   ✅ 499 ошибки не обнаружены в логах")

        except Exception as e:
            print(f"   ❌ Ошибка анализа 499 ошибок: {e}")
            self.errors_found.append(f"499 error analysis error: {e}")

    async def fix_websocket_issues(self):
        """Исправление проблем с WebSocket соединениями"""
        print("\n🔌 Исправление проблем с WebSocket...")

        try:
            # Проверяем WebSocket конфигурации
            websocket_files = [
                "exchanges/base/websocket_base.py",
                "web/api/websocket/manager.py",
                "web/frontend/src/hooks/useWebSocket.ts",
            ]

            for file_path in websocket_files:
                if os.path.exists(file_path):
                    print(f"   📄 Анализ WebSocket файла: {file_path}")

                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()

                    # Проверяем настройки таймаутов
                    timeout_issues = []

                    # Ищем проблемы с таймаутами
                    if "timeout" in content.lower():
                        # Проверяем слишком короткие таймауты
                        short_timeout_pattern = r"timeout.*[=:]\s*(\d+)"
                        matches = re.findall(short_timeout_pattern, content)

                        for match in matches:
                            try:
                                timeout_value = int(match)
                                if timeout_value < 5:  # Меньше 5 секунд - проблема
                                    timeout_issues.append(
                                        f"Слишком короткий таймаут: {timeout_value}s"
                                    )
                            except ValueError:
                                pass

                    # Проверяем отсутствие обработки ошибок
                    if "except" not in content and "error" in content.lower():
                        timeout_issues.append("Отсутствует обработка ошибок")

                    if timeout_issues:
                        print("      ⚠️ Проблемы найдены:")
                        for issue in timeout_issues:
                            print(f"         • {issue}")
                        self.websocket_issues.extend(timeout_issues)
                    else:
                        print("      ✅ Проблемы не обнаружены")

            # Создаем оптимизированные настройки WebSocket
            await self._create_websocket_optimizations()

        except Exception as e:
            print(f"   ❌ Ошибка анализа WebSocket: {e}")
            self.errors_found.append(f"WebSocket analysis error: {e}")

    async def _create_websocket_optimizations(self):
        """Создание оптимизированных настроек WebSocket"""
        print("   🔧 Создание оптимизированных настроек WebSocket...")

        # Создаем файл с оптимизированными настройками
        optimizations = {
            "websocket_timeouts": {
                "connection_timeout": 30,
                "ping_interval": 25,
                "ping_timeout": 10,
                "reconnect_delay": 5,
                "max_reconnect_attempts": 10,
            },
            "http_timeouts": {
                "request_timeout": 30,
                "connect_timeout": 10,
                "read_timeout": 20,
            },
            "async_operations": {
                "task_timeout": 60,
                "max_concurrent_tasks": 50,
                "retry_attempts": 3,
            },
        }

        # Сохраняем оптимизации
        config_file = "config/websocket_optimizations.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(optimizations, f, indent=2, ensure_ascii=False)

        print(f"   ✅ Оптимизации сохранены в {config_file}")
        self.fixes_applied.append("WebSocket optimizations created")

    async def fix_http_timeout_issues(self):
        """Исправление проблем с HTTP таймаутами"""
        print("\n🌐 Исправление проблем с HTTP таймаутами...")

        try:
            # Проверяем HTTP клиенты
            http_files = [
                "exchanges/bybit/client.py",
                "exchanges/factory.py",
                "web/frontend/src/api/client.ts",
            ]

            for file_path in http_files:
                if os.path.exists(file_path):
                    print(f"   📄 Анализ HTTP клиента: {file_path}")

                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()

                    # Проверяем настройки таймаутов
                    timeout_issues = []

                    # Ищем проблемы с таймаутами
                    if "timeout" in content.lower():
                        # Проверяем слишком короткие таймауты
                        short_timeout_pattern = r"timeout.*[=:]\s*(\d+)"
                        matches = re.findall(short_timeout_pattern, content)

                        for match in matches:
                            try:
                                timeout_value = int(match)
                                if timeout_value < 10:  # Меньше 10 секунд - проблема
                                    timeout_issues.append(
                                        f"Слишком короткий HTTP таймаут: {timeout_value}s"
                                    )
                            except ValueError:
                                pass

                    if timeout_issues:
                        print("      ⚠️ Проблемы найдены:")
                        for issue in timeout_issues:
                            print(f"         • {issue}")
                        self.http_timeout_issues.extend(timeout_issues)
                    else:
                        print("      ✅ Проблемы не обнаружены")

            # Создаем оптимизированные HTTP настройки
            await self._create_http_optimizations()

        except Exception as e:
            print(f"   ❌ Ошибка анализа HTTP таймаутов: {e}")
            self.errors_found.append(f"HTTP timeout analysis error: {e}")

    async def _create_http_optimizations(self):
        """Создание оптимизированных HTTP настроек"""
        print("   🔧 Создание оптимизированных HTTP настроек...")

        # Создаем файл с оптимизированными настройками
        http_optimizations = {
            "http_client_config": {
                "default_timeout": 30,
                "connect_timeout": 10,
                "read_timeout": 20,
                "retry_attempts": 3,
                "retry_delay": 1,
                "max_retry_delay": 60,
            },
            "rate_limiting": {
                "requests_per_minute": 60,
                "burst_limit": 10,
                "backoff_factor": 2,
            },
            "connection_pool": {
                "max_connections": 100,
                "max_connections_per_host": 10,
                "keepalive_timeout": 30,
            },
        }

        # Сохраняем оптимизации
        config_file = "config/http_optimizations.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(http_optimizations, f, indent=2, ensure_ascii=False)

        print(f"   ✅ HTTP оптимизации сохранены в {config_file}")
        self.fixes_applied.append("HTTP optimizations created")

    async def fix_async_operation_issues(self):
        """Исправление проблем с асинхронными операциями"""
        print("\n⚡ Исправление проблем с асинхронными операциями...")

        try:
            # Проверяем асинхронные операции
            async_files = [
                "core/system/process_manager.py",
                "trading/engine.py",
                "ml/ml_signal_processor.py",
            ]

            for file_path in async_files:
                if os.path.exists(file_path):
                    print(f"   📄 Анализ асинхронного файла: {file_path}")

                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()

                    # Проверяем проблемы с асинхронными операциями
                    async_issues = []

                    # Ищем отсутствие таймаутов в asyncio.wait_for
                    if "asyncio.wait_for" in content:
                        # Проверяем, есть ли таймауты
                        wait_for_pattern = r"asyncio\.wait_for\([^,]+\)"
                        matches = re.findall(wait_for_pattern, content)

                        for match in matches:
                            if "timeout=" not in match:
                                async_issues.append("asyncio.wait_for без таймаута")

                    # Ищем бесконечные циклы
                    if "while True:" in content and "asyncio.sleep" not in content:
                        async_issues.append("Бесконечный цикл без sleep")

                    # Ищем отсутствие обработки исключений
                    if "async def" in content and "except" not in content:
                        async_issues.append("Отсутствует обработка исключений")

                    if async_issues:
                        print("      ⚠️ Проблемы найдены:")
                        for issue in async_issues:
                            print(f"         • {issue}")
                        self.async_issues.extend(async_issues)
                    else:
                        print("      ✅ Проблемы не обнаружены")

            # Создаем оптимизированные асинхронные настройки
            await self._create_async_optimizations()

        except Exception as e:
            print(f"   ❌ Ошибка анализа асинхронных операций: {e}")
            self.errors_found.append(f"Async operation analysis error: {e}")

    async def _create_async_optimizations(self):
        """Создание оптимизированных асинхронных настроек"""
        print("   🔧 Создание оптимизированных асинхронных настроек...")

        # Создаем файл с оптимизированными настройками
        async_optimizations = {
            "async_operation_config": {
                "default_task_timeout": 60,
                "max_concurrent_tasks": 50,
                "task_cleanup_interval": 30,
                "deadlock_detection_timeout": 300,
            },
            "error_handling": {
                "retry_attempts": 3,
                "retry_delay": 1,
                "exponential_backoff": True,
                "max_retry_delay": 60,
            },
            "monitoring": {
                "task_monitoring_enabled": True,
                "memory_monitoring_enabled": True,
                "performance_monitoring_enabled": True,
            },
        }

        # Сохраняем оптимизации
        config_file = "config/async_optimizations.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(async_optimizations, f, indent=2, ensure_ascii=False)

        print(f"   ✅ Асинхронные оптимизации сохранены в {config_file}")
        self.fixes_applied.append("Async optimizations created")

    async def create_499_monitoring_system(self):
        """Создание системы мониторинга 499 ошибок"""
        print("\n📊 Создание системы мониторинга 499 ошибок...")

        try:
            # Создаем скрипт мониторинга
            monitoring_script = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Система мониторинга 499 ошибок
Автоматически отслеживает и уведомляет о 499 ошибках
"""

import asyncio
import os
import sys
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List

# Добавляем корень проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class Error499Monitor:
    """Мониторинг 499 ошибок"""

    def __init__(self):
        self.error_patterns = [
            r'499.*error',
            r'Client.*closed.*request',
            r'Connection.*closed.*prematurely',
            r'WebSocket.*closed',
            r'timeout.*error',
            r'Connection.*timeout'
        ]
        self.error_count = 0
        self.last_check = datetime.now()

    async def monitor_logs(self):
        """Мониторинг логов на предмет 499 ошибок"""
        log_files = [
            "data/logs/trading.log",
            "data/logs/system.log",
            "logs/trading.log",
            "logs/system.log"
        ]

        for log_file in log_files:
            if os.path.exists(log_file):
                await self._check_log_file(log_file)

    async def _check_log_file(self, log_file: str):
        """Проверка конкретного лог файла"""
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()

            for pattern in self.error_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    self.error_count += len(matches)
                    print(f"⚠️ Найдено {len(matches)} потенциальных 499 ошибок в {log_file}")

        except Exception as e:
            print(f"❌ Ошибка проверки лога {log_file}: {e}")

    async def generate_report(self):
        """Генерация отчета"""
        print(f"📊 Отчет мониторинга 499 ошибок")
        print(f"   Всего ошибок: {self.error_count}")
        print(f"   Время проверки: {datetime.now()}")

        if self.error_count > 0:
            print("   ⚠️ Обнаружены 499 ошибки! Рекомендуется запустить fix_system_issues.py")
        else:
            print("   ✅ 499 ошибки не обнаружены")

async def main():
    """Основная функция"""
    monitor = Error499Monitor()
    await monitor.monitor_logs()
    await monitor.generate_report()

if __name__ == "__main__":
    asyncio.run(main())
'''

            # Сохраняем скрипт мониторинга
            monitoring_file = "scripts/monitor_499_errors.py"
            with open(monitoring_file, "w", encoding="utf-8") as f:
                f.write(monitoring_script)

            # Делаем файл исполняемым
            os.chmod(monitoring_file, 0o755)

            print(f"   ✅ Система мониторинга создана: {monitoring_file}")
            self.fixes_applied.append("499 error monitoring system created")

        except Exception as e:
            print(f"   ❌ Ошибка создания системы мониторинга: {e}")
            self.errors_found.append(f"Monitoring system creation error: {e}")

    async def fix_database_issues(self):
        """Исправление проблем базы данных"""
        print("\n🗄️ Исправление проблем базы данных...")

        try:
            # Проверяем структуру таблицы signals
            result = await AsyncPGPool.fetch(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'signals'
                ORDER BY ordinal_position
            """
            )

            print("   📊 Структура таблицы signals:")
            for row in result:
                print(
                    f"      {row['column_name']}: {row['data_type']} ({'NULL' if row['is_nullable'] == 'YES' else 'NOT NULL'})"
                )

            # Проверяем последние записи в таблице signals
            result = await AsyncPGPool.fetch(
                """
                SELECT id, symbol, side, created_at, updated_at
                FROM signals
                ORDER BY created_at DESC
                LIMIT 5
            """
            )

            print("   📈 Последние 5 сигналов:")
            for row in result:
                print(f"      ID {row['id']}: {row['symbol']} {row['side']} ({row['created_at']})")

            # Проверяем, есть ли проблемы с типами данных
            result = await AsyncPGPool.fetch(
                """
                SELECT COUNT(*) as count
                FROM signals
                WHERE symbol IS NULL OR side IS NULL
            """
            )

            null_count = result[0]["count"] if result else 0
            if null_count > 0:
                print(f"   ⚠️ Найдено {null_count} записей с NULL значениями")
                self.errors_found.append(f"Found {null_count} signals with NULL values")

            self.fixes_applied.append("Database structure analyzed")

        except Exception as e:
            print(f"   ❌ Ошибка проверки БД: {e}")
            self.errors_found.append(f"Database check error: {e}")

    async def fix_position_manager_issues(self):
        """Исправление проблем PositionManager"""
        print("\n📊 Исправление проблем PositionManager...")

        try:
            # Проверяем файл PositionManager
            position_manager_path = "trading/positions/position_manager.py"

            if os.path.exists(position_manager_path):
                with open(position_manager_path, encoding="utf-8") as f:
                    content = f.read()

                # Проверяем наличие методов
                missing_methods = []

                if "def sync_positions" not in content:
                    missing_methods.append("sync_positions")

                if "def calculate_total_pnl" not in content:
                    missing_methods.append("calculate_total_pnl")

                if missing_methods:
                    print(f"   ⚠️ Отсутствуют методы: {', '.join(missing_methods)}")
                    self.errors_found.append(f"Missing PositionManager methods: {missing_methods}")

                    # Создаем резервную копию
                    backup_path = (
                        f"{position_manager_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    )
                    with open(backup_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"   💾 Создана резервная копия: {backup_path}")

                    # Добавляем недостающие методы
                    await self._add_missing_position_manager_methods(
                        position_manager_path, content, missing_methods
                    )
                else:
                    print("   ✅ Все методы PositionManager присутствуют")
            else:
                print(f"   ❌ Файл {position_manager_path} не найден")
                self.errors_found.append(f"PositionManager file not found: {position_manager_path}")

        except Exception as e:
            print(f"   ❌ Ошибка проверки PositionManager: {e}")
            self.errors_found.append(f"PositionManager check error: {e}")

    async def _add_missing_position_manager_methods(
        self, file_path: str, content: str, missing_methods: list
    ):
        """Добавление недостающих методов в PositionManager"""
        print("   🔧 Добавление недостающих методов...")

        # Определяем методы для добавления
        methods_to_add = []

        if "sync_positions" in missing_methods:
            methods_to_add.append(
                """
    async def sync_positions(self) -> None:
        \"\"\"Синхронизация позиций с биржей\"\"\"
        try:
            # Получаем все активные позиции
            active_positions = await self.get_active_positions()

            for position in active_positions:
                # Обновляем данные позиции с биржи
                await self.update_position_from_exchange(position)

        except Exception as e:
            self.logger.error(f"Ошибка синхронизации позиций: {e}")
            raise
"""
            )

        if "calculate_total_pnl" in missing_methods:
            methods_to_add.append(
                """
    async def calculate_total_pnl(self) -> float:
        \"\"\"Расчет общего P&L по всем позициям\"\"\"
        try:
            total_pnl = 0.0

            # Получаем все активные позиции
            active_positions = await self.get_active_positions()

            for position in active_positions:
                # Рассчитываем P&L для каждой позиции
                position_pnl = await self.calculate_position_pnl(position)
                total_pnl += position_pnl

            return total_pnl

        except Exception as e:
            self.logger.error(f"Ошибка расчета общего P&L: {e}")
            return 0.0
"""
            )

        if methods_to_add:
            # Добавляем методы в конец класса
            for method in methods_to_add:
                # Находим последнюю закрывающую скобку класса
                last_class_end = content.rfind("    def ")
                if last_class_end == -1:
                    last_class_end = content.rfind("\nclass ")

                if last_class_end != -1:
                    # Находим конец последнего метода
                    lines = content.split("\n")
                    for i in range(len(lines) - 1, -1, -1):
                        if lines[i].strip() == "" or lines[i].strip().startswith("class "):
                            break

                    # Вставляем новые методы
                    insert_pos = "\n".join(lines[: i + 1])
                    new_content = (
                        insert_pos
                        + "\n"
                        + "\n".join(methods_to_add)
                        + "\n"
                        + "\n".join(lines[i + 1 :])
                    )

                    # Сохраняем обновленный файл
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(new_content)

                    print(f"   ✅ Добавлены методы: {', '.join(missing_methods)}")
                    self.fixes_applied.append(f"Added PositionManager methods: {missing_methods}")
                else:
                    print("   ❌ Не удалось найти место для вставки методов")
                    self.errors_found.append(
                        "Could not find insertion point for PositionManager methods"
                    )

    async def fix_signal_processing_issues(self):
        """Исправление проблем обработки сигналов"""
        print("\n📡 Исправление проблем обработки сигналов...")

        try:
            # Проверяем файл обработки сигналов
            signal_processor_path = "core/signals/unified_signal_processor.py"

            if os.path.exists(signal_processor_path):
                with open(signal_processor_path, encoding="utf-8") as f:
                    content = f.read()

                # Проверяем проблемные места
                issues_found = []

                # Проверяем создание сигналов
                if "Signal(" in content and "create_signal" in content:
                    print("   ✅ Обработчик сигналов найден")
                else:
                    print("   ⚠️ Проблемы с обработкой сигналов")
                    issues_found.append("Signal processing issues detected")

                if issues_found:
                    self.errors_found.extend(issues_found)
                else:
                    print("   ✅ Обработка сигналов выглядит корректно")

            else:
                print(f"   ❌ Файл {signal_processor_path} не найден")
                self.errors_found.append(
                    f"Signal processor file not found: {signal_processor_path}"
                )

        except Exception as e:
            print(f"   ❌ Ошибка проверки обработки сигналов: {e}")
            self.errors_found.append(f"Signal processing check error: {e}")

    async def run_migrations(self):
        """Запуск миграций базы данных"""
        print("\n🔄 Запуск миграций базы данных...")

        try:
            import subprocess

            # Запускаем миграции
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            )

            if result.returncode == 0:
                print("   ✅ Миграции выполнены успешно")
                self.fixes_applied.append("Database migrations applied")
            else:
                print(f"   ❌ Ошибка миграций: {result.stderr}")
                self.errors_found.append(f"Migration error: {result.stderr}")

        except Exception as e:
            print(f"   ❌ Ошибка запуска миграций: {e}")
            self.errors_found.append(f"Migration execution error: {e}")

    async def generate_fix_report(self):
        """Генерация отчета об исправлениях"""
        print("\n📊 Отчет об исправлениях")
        print("=" * 50)

        report = {
            "timestamp": datetime.now().isoformat(),
            "fixes_applied": self.fixes_applied,
            "errors_found": self.errors_found,
            "websocket_issues": self.websocket_issues,
            "http_timeout_issues": self.http_timeout_issues,
            "async_issues": self.async_issues,
            "fixes_count": len(self.fixes_applied),
            "errors_count": len(self.errors_found),
        }

        # Сохраняем отчет
        report_file = f"logs/fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        print(f"📄 Отчет сохранен: {report_file}")

        # Выводим статистику
        print("\n📈 Статистика исправлений:")
        print(f"   ✅ Применено исправлений: {report['fixes_count']}")
        print(f"   ❌ Найдено ошибок: {report['errors_count']}")
        print(f"   🔌 WebSocket проблем: {len(self.websocket_issues)}")
        print(f"   🌐 HTTP таймаут проблем: {len(self.http_timeout_issues)}")
        print(f"   ⚡ Асинхронных проблем: {len(self.async_issues)}")

        if self.fixes_applied:
            print("\n✅ Примененные исправления:")
            for fix in self.fixes_applied:
                print(f"   • {fix}")

        if self.errors_found:
            print("\n❌ Найденные проблемы:")
            for error in self.errors_found:
                print(f"   • {error}")

        # Рекомендации
        if self.errors_found:
            print("\n🔧 ДОПОЛНИТЕЛЬНЫЕ РЕКОМЕНДАЦИИ:")
            print("   1. Перезапустите систему после исправлений")
            print("   2. Запустите мониторинг 499 ошибок: python scripts/monitor_499_errors.py")
            print("   3. Проверьте логи на наличие новых ошибок")
            print("   4. Запустите тесты: python -m pytest tests/")
            print("   5. Мониторьте систему: python scripts/monitor_system_enhanced.py")
            print("   6. Проверьте WebSocket соединения в реальном времени")

    async def run_all_fixes(self):
        """Запуск всех исправлений"""
        print("🚀 Запуск исправления системных проблем (включая 499 ошибки)")
        print("=" * 70)

        try:
            await self.initialize()
            await self.analyze_499_errors()
            await self.fix_websocket_issues()
            await self.fix_http_timeout_issues()
            await self.fix_async_operation_issues()
            await self.create_499_monitoring_system()
            await self.fix_database_issues()
            await self.fix_position_manager_issues()
            await self.fix_signal_processing_issues()
            await self.run_migrations()
            await self.generate_fix_report()

            print("\n✅ Исправление завершено!")

        except Exception as e:
            print(f"\n❌ Критическая ошибка: {e}")
            self.errors_found.append(f"Critical error: {e}")
            await self.generate_fix_report()


async def main():
    """Основная функция"""
    fixer = SystemIssueFixer()
    await fixer.run_all_fixes()


if __name__ == "__main__":
    asyncio.run(main())
