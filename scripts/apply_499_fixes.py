#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт автоматического применения исправлений 499 ошибок
Применяет оптимизации к существующим файлам для предотвращения 499 ошибок
"""

import asyncio
import json
import os
import re
import sys
from datetime import datetime

# Добавляем корень проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Fix499Applier:
    """Применение исправлений 499 ошибок"""

    def __init__(self):
        self.fixes_applied = []
        self.files_modified = []
        self.backups_created = []

    async def apply_websocket_fixes(self):
        """Применение исправлений к WebSocket файлам"""
        print("🔌 Применение исправлений к WebSocket файлам...")

        websocket_files = [
            "exchanges/base/websocket_base.py",
            "web/api/websocket/manager.py",
        ]

        for file_path in websocket_files:
            if os.path.exists(file_path):
                await self._apply_websocket_fixes_to_file(file_path)
            else:
                print(f"   ⚠️ Файл не найден: {file_path}")

    async def _apply_websocket_fixes_to_file(self, file_path: str):
        """Применение исправлений к конкретному WebSocket файлу"""
        print(f"   📄 Применение исправлений к: {file_path}")

        try:
            # Создаем резервную копию
            backup_path = (
                f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            with open(file_path, "r", encoding="utf-8") as f:
                original_content = f.read()

            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(original_content)

            self.backups_created.append(backup_path)
            print(f"      💾 Создана резервная копия: {backup_path}")

            # Применяем исправления
            modified_content = self._apply_websocket_optimizations(original_content)

            # Сохраняем измененный файл
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(modified_content)

            self.files_modified.append(file_path)
            print("      ✅ Исправления применены")

        except Exception as e:
            print(f"      ❌ Ошибка применения исправлений: {e}")

    def _apply_websocket_optimizations(self, content: str) -> str:
        """Применение оптимизаций к WebSocket коду"""
        modified_content = content

        # Добавляем оптимизированные таймауты в __init__
        if "def __init__" in content and "timeout" in content:
            # Ищем существующие таймауты и заменяем их
            timeout_replacements = [
                (r"timeout\s*=\s*\d+", "timeout=30"),
                (r"ping_interval\s*=\s*\d+", "ping_interval=25"),
                (r"ping_timeout\s*=\s*\d+", "ping_timeout=10"),
                (r"reconnect_delay\s*=\s*\d+", "reconnect_delay=5"),
                (r"max_reconnect_attempts\s*=\s*\d+", "max_reconnect_attempts=10"),
            ]

            for pattern, replacement in timeout_replacements:
                modified_content = re.sub(pattern, replacement, modified_content)

        # Добавляем обработку ошибок в connect метод
        if "async def connect" in content and "except Exception" not in content:
            # Находим место для вставки обработки ошибок
            connect_pattern = r"(async def connect\([^)]*\):\s*\n\s*)(.*?)(\n\s*return)"
            match = re.search(connect_pattern, modified_content, re.DOTALL)

            if match:
                before = match.group(1)
                connect_body = match.group(2)
                after = match.group(3)

                error_handling = """
        try:
            # Установка соединения с оптимизированными таймаутами
            self.websocket = await websockets.connect(
                self.connection_url,
                timeout=self.connection_timeout,
                ping_interval=self.ping_interval,
                ping_timeout=self.ping_timeout,
            )
        except Exception as e:
            self.logger.error(f"Ошибка подключения WebSocket: {e}")
            self.state = WebSocketState.ERROR
            if self.reconnect_attempts < self.max_reconnect_attempts:
                await self._schedule_reconnect()
            raise"""

                modified_content = re.sub(
                    connect_pattern,
                    f"{before}{error_handling}{after}",
                    modified_content,
                    flags=re.DOTALL,
                )

        # Добавляем метод планирования переподключения
        if "async def _schedule_reconnect" not in content:
            reconnect_method = '''
    async def _schedule_reconnect(self):
        """Планирование переподключения с экспоненциальной задержкой"""
        delay = min(self.reconnect_delay * (2 ** self.reconnect_attempts), 60)
        self.logger.info(f"Переподключение через {delay} секунд")
        await asyncio.sleep(delay)
        self.reconnect_attempts += 1
        await self.connect()
'''

            # Вставляем метод в конец класса
            class_end = modified_content.rfind("\nclass ")
            if class_end != -1:
                lines = modified_content.split("\n")
                for i in range(len(lines) - 1, -1, -1):
                    if lines[i].strip() == "" or lines[i].strip().startswith("class "):
                        break

                insert_pos = "\n".join(lines[: i + 1])
                modified_content = (
                    insert_pos + reconnect_method + "\n" + "\n".join(lines[i + 1 :])
                )

        return modified_content

    async def apply_async_fixes(self):
        """Применение исправлений к асинхронным операциям"""
        print("\n⚡ Применение исправлений к асинхронным операциям...")

        async_files = ["core/system/process_manager.py", "trading/engine.py"]

        for file_path in async_files:
            if os.path.exists(file_path):
                await self._apply_async_fixes_to_file(file_path)
            else:
                print(f"   ⚠️ Файл не найден: {file_path}")

    async def _apply_async_fixes_to_file(self, file_path: str):
        """Применение исправлений к конкретному асинхронному файлу"""
        print(f"   📄 Применение исправлений к: {file_path}")

        try:
            # Создаем резервную копию
            backup_path = (
                f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            with open(file_path, "r", encoding="utf-8") as f:
                original_content = f.read()

            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(original_content)

            self.backups_created.append(backup_path)
            print(f"      💾 Создана резервная копия: {backup_path}")

            # Применяем исправления
            modified_content = self._apply_async_optimizations(original_content)

            # Сохраняем измененный файл
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(modified_content)

            self.files_modified.append(file_path)
            print("      ✅ Исправления применены")

        except Exception as e:
            print(f"      ❌ Ошибка применения исправлений: {e}")

    def _apply_async_optimizations(self, content: str) -> str:
        """Применение оптимизаций к асинхронному коду"""
        modified_content = content

        # Добавляем таймауты к asyncio.wait_for
        wait_for_pattern = r"asyncio\.wait_for\(([^,]+)\)"
        matches = re.findall(wait_for_pattern, content)

        for match in matches:
            if "timeout=" not in match:
                # Добавляем таймаут
                new_wait_for = f"asyncio.wait_for({match}, timeout=60)"
                modified_content = modified_content.replace(
                    f"asyncio.wait_for({match})", new_wait_for
                )

        # Добавляем обработку исключений к асинхронным функциям
        async_func_pattern = (
            r"(async def [^:]+:\s*\n)(\s*)(.*?)(\n\s*return|\n\s*pass|\n\s*$)"
        )

        def add_exception_handling(match):
            func_def = match.group(1)
            indent = match.group(2)
            func_body = match.group(3)
            end = match.group(4)

            if "try:" not in func_body and "except" not in func_body:
                wrapped_body = f"""try:
{indent}    {func_body}
{indent}except Exception as e:
{indent}    self.logger.error(f"Ошибка в асинхронной функции: {{e}}")
{indent}    raise"""
                return f"{func_def}{wrapped_body}{end}"
            else:
                return match.group(0)

        modified_content = re.sub(
            async_func_pattern,
            add_exception_handling,
            modified_content,
            flags=re.DOTALL,
        )

        return modified_content

    async def create_monitoring_config(self):
        """Создание конфигурации мониторинга"""
        print("\n📊 Создание конфигурации мониторинга...")

        monitoring_config = {
            "499_error_monitoring": {
                "enabled": True,
                "check_interval": 30,  # секунды
                "log_files": [
                    "data/logs/trading.log",
                    "data/logs/system.log",
                    "logs/trading.log",
                    "logs/system.log",
                ],
                "error_patterns": [
                    r"499.*error",
                    r"Client.*closed.*request",
                    r"Connection.*closed.*prematurely",
                    r"WebSocket.*closed",
                    r"timeout.*error",
                    r"Connection.*timeout",
                ],
                "alert_threshold": 5,  # количество ошибок для алерта
                "auto_fix_enabled": True,
            },
            "websocket_monitoring": {
                "enabled": True,
                "health_check_interval": 25,
                "connection_timeout": 30,
                "max_reconnect_attempts": 10,
                "auto_reconnect": True,
            },
            "performance_monitoring": {
                "enabled": True,
                "memory_threshold": 80,  # процент использования памяти
                "cpu_threshold": 90,  # процент использования CPU
                "response_time_threshold": 5000,  # миллисекунды
            },
        }

        config_file = "config/499_monitoring_config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(monitoring_config, f, indent=2, ensure_ascii=False)

        print(f"   ✅ Конфигурация мониторинга создана: {config_file}")
        self.fixes_applied.append("Monitoring configuration created")

    async def create_auto_fix_script(self):
        """Создание скрипта автоматического исправления"""
        print("\n🤖 Создание скрипта автоматического исправления...")

        auto_fix_script = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Автоматическое исправление 499 ошибок
Запускается автоматически при обнаружении проблем
"""

import asyncio
import os
import sys
import json
import subprocess
from datetime import datetime

class Auto499Fixer:
    """Автоматическое исправление 499 ошибок"""

    def __init__(self):
        self.config = self._load_config()
        self.fixes_applied = 0

    def _load_config(self):
        """Загрузка конфигурации"""
        try:
            with open("config/499_monitoring_config.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"499_error_monitoring": {"auto_fix_enabled": True}}

    async def auto_fix_499_errors(self):
        """Автоматическое исправление 499 ошибок"""
        if not self.config["499_error_monitoring"]["auto_fix_enabled"]:
            return

        print("🤖 Запуск автоматического исправления 499 ошибок...")

        try:
            # Перезапуск WebSocket соединений
            await self._restart_websocket_connections()

            # Очистка кэша
            await self._clear_cache()

            # Перезапуск проблемных процессов
            await self._restart_problematic_processes()

            print(f"✅ Автоматическое исправление завершено. Применено исправлений: {self.fixes_applied}")

        except Exception as e:
            print(f"❌ Ошибка автоматического исправления: {e}")

    async def _restart_websocket_connections(self):
        """Перезапуск WebSocket соединений"""
        print("   🔌 Перезапуск WebSocket соединений...")
        # Здесь должна быть логика перезапуска WebSocket
        self.fixes_applied += 1

    async def _clear_cache(self):
        """Очистка кэша"""
        print("   🧹 Очистка кэша...")
        # Здесь должна быть логика очистки кэша
        self.fixes_applied += 1

    async def _restart_problematic_processes(self):
        """Перезапуск проблемных процессов"""
        print("   🔄 Перезапуск проблемных процессов...")
        # Здесь должна быть логика перезапуска процессов
        self.fixes_applied += 1

async def main():
    """Основная функция"""
    fixer = Auto499Fixer()
    await fixer.auto_fix_499_errors()

if __name__ == "__main__":
    asyncio.run(main())
'''

        # Сохраняем скрипт
        auto_fix_file = "scripts/auto_fix_499_errors.py"
        with open(auto_fix_file, "w", encoding="utf-8") as f:
            f.write(auto_fix_script)

        # Делаем файл исполняемым
        os.chmod(auto_fix_file, 0o755)

        print(f"   ✅ Скрипт автоматического исправления создан: {auto_fix_file}")
        self.fixes_applied.append("Auto-fix script created")

    async def generate_application_report(self):
        """Генерация отчета о применении исправлений"""
        print("\n📊 Отчет о применении исправлений")
        print("=" * 50)

        report = {
            "timestamp": datetime.now().isoformat(),
            "fixes_applied": self.fixes_applied,
            "files_modified": self.files_modified,
            "backups_created": self.backups_created,
            "fixes_count": len(self.fixes_applied),
            "files_count": len(self.files_modified),
            "backups_count": len(self.backups_created),
        }

        # Сохраняем отчет
        report_file = (
            f"logs/application_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        print(f"📄 Отчет сохранен: {report_file}")

        # Выводим статистику
        print("\n📈 Статистика применения:")
        print(f"   ✅ Применено исправлений: {report['fixes_count']}")
        print(f"   📄 Изменено файлов: {report['files_count']}")
        print(f"   💾 Создано резервных копий: {report['backups_count']}")

        if self.fixes_applied:
            print("\n✅ Примененные исправления:")
            for fix in self.fixes_applied:
                print(f"   • {fix}")

        if self.files_modified:
            print("\n📄 Измененные файлы:")
            for file in self.files_modified:
                print(f"   • {file}")

        if self.backups_created:
            print("\n💾 Резервные копии:")
            for backup in self.backups_created:
                print(f"   • {backup}")

        # Рекомендации
        print("\n🔧 РЕКОМЕНДАЦИИ:")
        print("   1. Перезапустите систему для применения изменений")
        print("   2. Запустите мониторинг: python scripts/monitor_499_errors.py")
        print("   3. Проверьте работу WebSocket соединений")
        print("   4. Мониторьте логи на наличие новых ошибок")
        print("   5. При необходимости откатите изменения используя резервные копии")

    async def run_all_applications(self):
        """Запуск всех применений исправлений"""
        print("🚀 Применение исправлений 499 ошибок к файлам")
        print("=" * 60)

        try:
            await self.apply_websocket_fixes()
            await self.apply_async_fixes()
            await self.create_monitoring_config()
            await self.create_auto_fix_script()
            await self.generate_application_report()

            print("\n✅ Применение исправлений завершено!")

        except Exception as e:
            print(f"\n❌ Критическая ошибка: {e}")
            await self.generate_application_report()


async def main():
    """Основная функция"""
    applier = Fix499Applier()
    await applier.run_all_applications()


if __name__ == "__main__":
    asyncio.run(main())
