#!/usr/bin/env python3
"""Test script to verify cache_ttl fix"""

import asyncio
import sys
from datetime import UTC, datetime

# Add project to path
sys.path.insert(0, ".")


async def test_cache_fix():
    """Test that cache_ttl error is fixed"""

    try:
        # Import after adding to path
        from ml.realtime_indicator_calculator import RealTimeIndicatorCalculator

        print("✅ Импорт RealTimeIndicatorCalculator успешен")

        # Create instance with int cache_ttl
        calc = RealTimeIndicatorCalculator(cache_ttl=300)
        print(
            f"✅ Создан калькулятор с cache_ttl={calc.cache_ttl} (тип: {type(calc.cache_ttl).__name__})"
        )

        # Test cache with different timestamp types
        cache_key = "test_symbol_15m"

        # Test 1: Normal datetime timestamp (should work)
        calc.cache[cache_key] = ({"test": "data"}, datetime.now(UTC))
        result = calc._get_from_cache(cache_key)
        if result:
            print("✅ Тест 1: Нормальный datetime timestamp - работает")

        # Test 2: Int timestamp (should be converted)
        calc.cache[cache_key] = ({"test": "data2"}, int(datetime.now().timestamp()))
        result = calc._get_from_cache(cache_key)
        if result:
            print("✅ Тест 2: Int timestamp конвертирован и работает")

        # Test 3: Float timestamp in milliseconds
        calc.cache[cache_key] = ({"test": "data3"}, datetime.now().timestamp() * 1000)
        result = calc._get_from_cache(cache_key)
        if result:
            print("✅ Тест 3: Float milliseconds timestamp конвертирован и работает")

        print("\n🎉 Все тесты пройдены успешно!")
        return True

    except AttributeError as e:
        if "total_seconds" in str(e):
            print(f"❌ ОШИБКА total_seconds ВСЕ ЕЩЕ ЕСТЬ: {e}")
            return False
        else:
            print(f"❌ Другая AttributeError: {e}")
            raise
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_cache_fix())
    sys.exit(0 if success else 1)
