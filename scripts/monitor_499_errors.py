#!/usr/bin/env python3
"""
Система мониторинга 499 ошибок
Автоматически отслеживает и уведомляет о 499 ошибках
"""

import asyncio
import os
import re
import sys
from datetime import datetime

# Добавляем корень проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Error499Monitor:
    """Мониторинг 499 ошибок"""

    def __init__(self):
        self.error_patterns = [
            r"499.*error",
            r"Client.*closed.*request",
            r"Connection.*closed.*prematurely",
            r"WebSocket.*closed",
            r"timeout.*error",
            r"Connection.*timeout",
        ]
        self.error_count = 0
        self.last_check = datetime.now()

    async def monitor_logs(self):
        """Мониторинг логов на предмет 499 ошибок"""
        log_files = [
            "data/logs/trading.log",
            "data/logs/system.log",
            "logs/trading.log",
            "logs/system.log",
        ]

        for log_file in log_files:
            if os.path.exists(log_file):
                await self._check_log_file(log_file)

    async def _check_log_file(self, log_file: str):
        """Проверка конкретного лог файла"""
        try:
            with open(log_file, encoding="utf-8") as f:
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
        print("📊 Отчет мониторинга 499 ошибок")
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
