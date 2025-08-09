"""
Исправление для правильного запуска процессов
"""

import os

# Устанавливаем переменную окружения для unified launcher
os.environ["UNIFIED_MODE"] = "true"

print("✅ Установлена переменная UNIFIED_MODE=true")
