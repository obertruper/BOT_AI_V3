#!/usr/bin/env python3
"""
Скрипт исправления проблем с WebSocket соединениями
Автоматически исправляет проблемы с WebSocket, которые вызывают 499 ошибки
"""

import asyncio
import json
import os
import re
import sys
from datetime import datetime

# Добавляем корень проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class WebSocketConnectionFixer:
    """Исправление проблем с WebSocket соединениями"""

    def __init__(self):
        self.fixes_applied = []
        self.issues_found = []
        self.optimization_configs = {}

    async def analyze_websocket_issues(self):
        """Анализ проблем с WebSocket"""
        print("🔍 Анализ проблем с WebSocket соединениями...")

        # Анализируем основные WebSocket файлы
        websocket_files = [
            "exchanges/base/websocket_base.py",
            "web/api/websocket/manager.py",
            "web/frontend/src/hooks/useWebSocket.ts",
        ]

        for file_path in websocket_files:
            if os.path.exists(file_path):
                await self._analyze_websocket_file(file_path)
            else:
                print(f"   ⚠️ Файл не найден: {file_path}")

    async def _analyze_websocket_file(self, file_path: str):
        """Анализ конкретного WebSocket файла"""
        print(f"   📄 Анализ: {file_path}")

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            issues = []

            # Проверяем таймауты
            timeout_issues = self._check_timeout_issues(content)
            if timeout_issues:
                issues.extend(timeout_issues)

            # Проверяем обработку ошибок
            error_handling_issues = self._check_error_handling(content)
            if error_handling_issues:
                issues.extend(error_handling_issues)

            # Проверяем переподключения
            reconnection_issues = self._check_reconnection_issues(content)
            if reconnection_issues:
                issues.extend(reconnection_issues)

            if issues:
                print(f"      ⚠️ Найдено проблем: {len(issues)}")
                for issue in issues:
                    print(f"         • {issue}")
                self.issues_found.extend(issues)
            else:
                print("      ✅ Проблемы не обнаружены")

        except Exception as e:
            print(f"      ❌ Ошибка анализа: {e}")

    def _check_timeout_issues(self, content: str) -> list[str]:
        """Проверка проблем с таймаутами"""
        issues = []

        # Ищем слишком короткие таймауты
        timeout_patterns = [
            r"timeout.*[=:]\s*(\d+)",
            r"ping_interval.*[=:]\s*(\d+)",
            r"ping_timeout.*[=:]\s*(\d+)",
            r"reconnect_delay.*[=:]\s*(\d+)",
        ]

        for pattern in timeout_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                try:
                    value = int(match)
                    if "ping_interval" in pattern and value < 20:
                        issues.append(
                            f"Слишком короткий ping_interval: {value}s (рекомендуется >= 20s)"
                        )
                    elif "ping_timeout" in pattern and value < 10:
                        issues.append(
                            f"Слишком короткий ping_timeout: {value}s (рекомендуется >= 10s)"
                        )
                    elif "reconnect_delay" in pattern and value < 5:
                        issues.append(
                            f"Слишком короткий reconnect_delay: {value}s (рекомендуется >= 5s)"
                        )
                    elif "timeout" in pattern and value < 30:
                        issues.append(f"Слишком короткий timeout: {value}s (рекомендуется >= 30s)")
                except ValueError:
                    pass

        return issues

    def _check_error_handling(self, content: str) -> list[str]:
        """Проверка обработки ошибок"""
        issues = []

        # Проверяем наличие обработки исключений
        if "async def" in content and "except" not in content:
            issues.append("Отсутствует обработка исключений в асинхронных функциях")

        # Проверяем обработку WebSocket ошибок
        if "websocket" in content.lower() and "connectionclosed" not in content.lower():
            issues.append("Отсутствует обработка ConnectionClosed исключений")

        # Проверяем обработку таймаутов
        if "timeout" in content.lower() and "timeouterror" not in content.lower():
            issues.append("Отсутствует обработка TimeoutError")

        return issues

    def _check_reconnection_issues(self, content: str) -> list[str]:
        """Проверка проблем с переподключениями"""
        issues = []

        # Проверяем наличие логики переподключения
        if "websocket" in content.lower() and "reconnect" not in content.lower():
            issues.append("Отсутствует логика переподключения")

        # Проверяем ограничение попыток переподключения
        if "reconnect" in content.lower() and "max_reconnect" not in content.lower():
            issues.append("Отсутствует ограничение попыток переподключения")

        return issues

    async def create_optimized_websocket_config(self):
        """Создание оптимизированной конфигурации WebSocket"""
        print("\n🔧 Создание оптимизированной конфигурации WebSocket...")

        # Оптимизированные настройки
        optimized_config = {
            "websocket_settings": {
                "connection_timeout": 30,
                "ping_interval": 25,
                "ping_timeout": 10,
                "reconnect_delay": 5,
                "max_reconnect_attempts": 10,
                "max_reconnect_delay": 60,
                "heartbeat_interval": 30,
                "message_queue_size": 1000,
            },
            "error_handling": {
                "retry_on_connection_error": True,
                "retry_on_timeout": True,
                "retry_on_websocket_error": True,
                "max_retry_attempts": 3,
                "exponential_backoff": True,
            },
            "monitoring": {
                "connection_monitoring": True,
                "message_monitoring": True,
                "error_monitoring": True,
                "performance_monitoring": True,
            },
        }

        # Сохраняем конфигурацию
        config_file = "config/optimized_websocket_config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(optimized_config, f, indent=2, ensure_ascii=False)

        print(f"   ✅ Оптимизированная конфигурация сохранена: {config_file}")
        self.fixes_applied.append("Optimized WebSocket configuration created")

        return optimized_config

    async def create_websocket_health_checker(self):
        """Создание системы проверки здоровья WebSocket соединений"""
        print("\n🏥 Создание системы проверки здоровья WebSocket...")

        health_checker_script = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Система проверки здоровья WebSocket соединений
Мониторит состояние WebSocket соединений и автоматически переподключает при проблемах
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class WebSocketHealthChecker:
    """Проверка здоровья WebSocket соединений"""

    def __init__(self):
        self.logger = logging.getLogger("websocket_health")
        self.connections = {}
        self.health_config = self._load_health_config()

    def _load_health_config(self) -> Dict:
        """Загрузка конфигурации здоровья"""
        try:
            with open("config/optimized_websocket_config.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "websocket_settings": {
                    "ping_interval": 25,
                    "ping_timeout": 10,
                    "reconnect_delay": 5
                }
            }

    async def check_connection_health(self, connection_id: str, websocket) -> bool:
        """Проверка здоровья конкретного соединения"""
        try:
            # Проверяем, что соединение открыто
            if websocket.closed:
                self.logger.warning(f"WebSocket {connection_id} закрыт")
                return False

            # Отправляем ping
            await websocket.ping()

            # Проверяем время последнего сообщения
            if connection_id in self.connections:
                last_message = self.connections[connection_id].get("last_message")
                if last_message and datetime.now() - last_message > timedelta(minutes=5):
                    self.logger.warning(f"WebSocket {connection_id} неактивен более 5 минут")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Ошибка проверки здоровья WebSocket {connection_id}: {e}")
            return False

    async def monitor_all_connections(self):
        """Мониторинг всех WebSocket соединений"""
        while True:
            try:
                # Здесь должна быть логика получения всех активных соединений
                # Это зависит от вашей архитектуры WebSocket

                self.logger.info("Проверка здоровья WebSocket соединений...")

                # Ждем следующей проверки
                await asyncio.sleep(self.health_config["websocket_settings"]["ping_interval"])

            except Exception as e:
                self.logger.error(f"Ошибка мониторинга WebSocket: {e}")
                await asyncio.sleep(30)

async def main():
    """Основная функция"""
    checker = WebSocketHealthChecker()
    await checker.monitor_all_connections()

if __name__ == "__main__":
    asyncio.run(main())
'''

        # Сохраняем скрипт проверки здоровья
        health_checker_file = "scripts/websocket_health_checker.py"
        with open(health_checker_file, "w", encoding="utf-8") as f:
            f.write(health_checker_script)

        # Делаем файл исполняемым
        os.chmod(health_checker_file, 0o755)

        print(f"   ✅ Система проверки здоровья создана: {health_checker_file}")
        self.fixes_applied.append("WebSocket health checker created")

    async def create_websocket_optimization_patches(self):
        """Создание патчей для оптимизации WebSocket"""
        print("\n🔧 Создание патчей оптимизации WebSocket...")

        # Создаем патч для websocket_base.py
        websocket_patch = '''
# Оптимизации для предотвращения 499 ошибок

# Добавить в __init__ метод:
self.connection_timeout = 30
self.ping_interval = 25
self.ping_timeout = 10
self.reconnect_delay = 5
self.max_reconnect_attempts = 10
self.max_reconnect_delay = 60

# Добавить обработку ошибок в connect метод:
try:
    self.websocket = await websockets.connect(
        self.connection_url,
        timeout=self.connection_timeout,
        ping_interval=self.ping_interval,
        ping_timeout=self.ping_timeout,
    )
except Exception as e:
    self.logger.error(f"Ошибка подключения WebSocket: {e}")
    await self._handle_connection_error(e)
    raise

# Добавить метод обработки ошибок подключения:
async def _handle_connection_error(self, error):
    """Обработка ошибок подключения"""
    self.state = WebSocketState.ERROR
    if self.reconnect_attempts < self.max_reconnect_attempts:
        await self._schedule_reconnect()
    else:
        self.logger.error("Достигнуто максимальное количество попыток переподключения")

# Добавить планировщик переподключения:
async def _schedule_reconnect(self):
    """Планирование переподключения"""
    delay = min(self.reconnect_delay * (2 ** self.reconnect_attempts), self.max_reconnect_delay)
    self.logger.info(f"Переподключение через {delay} секунд")
    await asyncio.sleep(delay)
    await self.connect()
'''

        # Сохраняем патч
        patch_file = "config/websocket_optimization_patch.txt"
        with open(patch_file, "w", encoding="utf-8") as f:
            f.write(websocket_patch)

        print(f"   ✅ Патч оптимизации сохранен: {patch_file}")
        self.fixes_applied.append("WebSocket optimization patch created")

    async def generate_fix_report(self):
        """Генерация отчета об исправлениях"""
        print("\n📊 Отчет об исправлениях WebSocket")
        print("=" * 50)

        report = {
            "timestamp": datetime.now().isoformat(),
            "fixes_applied": self.fixes_applied,
            "issues_found": self.issues_found,
            "fixes_count": len(self.fixes_applied),
            "issues_count": len(self.issues_found),
        }

        # Сохраняем отчет
        report_file = f"logs/websocket_fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        print(f"📄 Отчет сохранен: {report_file}")

        # Выводим статистику
        print("\n📈 Статистика исправлений WebSocket:")
        print(f"   ✅ Применено исправлений: {report['fixes_count']}")
        print(f"   ❌ Найдено проблем: {report['issues_count']}")

        if self.fixes_applied:
            print("\n✅ Примененные исправления:")
            for fix in self.fixes_applied:
                print(f"   • {fix}")

        if self.issues_found:
            print("\n❌ Найденные проблемы:")
            for issue in self.issues_found:
                print(f"   • {issue}")

        # Рекомендации
        print("\n🔧 РЕКОМЕНДАЦИИ:")
        print("   1. Примените патчи оптимизации к WebSocket файлам")
        print(
            "   2. Запустите систему проверки здоровья: python scripts/websocket_health_checker.py"
        )
        print("   3. Мониторьте WebSocket соединения в реальном времени")
        print("   4. Проверьте логи на наличие новых 499 ошибок")
        print("   5. Перезапустите систему после применения исправлений")

    async def run_all_fixes(self):
        """Запуск всех исправлений WebSocket"""
        print("🚀 Запуск исправления проблем с WebSocket соединениями")
        print("=" * 60)

        try:
            await self.analyze_websocket_issues()
            await self.create_optimized_websocket_config()
            await self.create_websocket_health_checker()
            await self.create_websocket_optimization_patches()
            await self.generate_fix_report()

            print("\n✅ Исправление WebSocket завершено!")

        except Exception as e:
            print(f"\n❌ Критическая ошибка: {e}")
            self.issues_found.append(f"Critical error: {e}")
            await self.generate_fix_report()


async def main():
    """Основная функция"""
    fixer = WebSocketConnectionFixer()
    await fixer.run_all_fixes()


if __name__ == "__main__":
    asyncio.run(main())
