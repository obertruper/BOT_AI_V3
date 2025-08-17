#!/usr/bin/env python3
"""Debug script to find total_seconds error"""

import traceback
from datetime import UTC, datetime

UTC = UTC

# Симулируем ошибку
try:
    cache_ttl = 300  # int
    timestamp = 300  # тоже int по ошибке

    # Проверим разные сценарии
    print("Сценарий 1: datetime - int")
    try:
        result = (datetime.now(UTC) - timestamp).total_seconds()
    except Exception as e:
        print(f"  Ошибка: {e}")
        print("  Это наша ошибка? НЕТ - другое сообщение")

    print("\nСценарий 2: int.total_seconds()")
    try:
        result = timestamp.total_seconds()
    except Exception as e:
        print(f"  Ошибка: {e}")
        print(f"  Это наша ошибка? {'int' in str(e) and 'total_seconds' in str(e)}")

    print("\nСценарий 3: (datetime - datetime).total_seconds() < int.total_seconds()")
    try:
        now = datetime.now(UTC)
        before = datetime(2024, 1, 1, tzinfo=UTC)
        # Симулируем ошибку из логов
        if (now - before).total_seconds() < cache_ttl.total_seconds():
            print("OK")
    except Exception as e:
        print(f"  Ошибка: {e}")
        print(f"  Это наша ошибка? {'int' in str(e) and 'total_seconds' in str(e)}")

except Exception as e:
    print(f"Общая ошибка: {e}")
    traceback.print_exc()
