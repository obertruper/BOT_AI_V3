#!/usr/bin/env python3
"""
Скрипт для исправления вызовов logger_factory.get_logger
Удаляет параметр component=, который больше не поддерживается
"""

import re
from pathlib import Path

# Путь к корню проекта
project_root = Path(__file__).parent.parent

# Паттерн для поиска
pattern = re.compile(r'(logger_factory\.get_logger\([^,]+), component="[^"]+"\)')


def fix_file(file_path):
    """Исправляет вызовы get_logger в файле"""
    with open(file_path, "r") as f:
        content = f.read()

    # Заменяем все вхождения
    new_content = pattern.sub(r"\1)", content)

    if new_content != content:
        with open(file_path, "w") as f:
            f.write(new_content)
        print(f"Исправлен: {file_path}")
        return True
    return False


# Файлы для исправления
files_to_fix = [
    "web/api/websocket/manager.py",
    "web/api/endpoints/monitoring.py",
    "web/api/endpoints/exchanges.py",
    "web/api/endpoints/traders.py",
    "web/api/endpoints/auth.py",
    "web/api/endpoints/strategies.py",
    "web/integration/mock_services.py",
    "web/integration/web_integration.py",
    "web/integration/web_orchestrator_bridge.py",
]

total_fixed = 0
for file_path in files_to_fix:
    full_path = project_root / file_path
    if full_path.exists():
        if fix_file(full_path):
            total_fixed += 1
    else:
        print(f"Файл не найден: {file_path}")

print(f"\nВсего исправлено файлов: {total_fixed}")
