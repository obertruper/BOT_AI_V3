#!/usr/bin/env python3
"""
Упрощенный тест исправлений
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

print("🚀 Тестирование исправлений...")

# Тест 1: Импорты
try:
    from core.config.config_manager import ConfigManager
    from ml.realtime_indicator_calculator import RealTimeIndicatorCalculator
    from trading.sltp.enhanced_manager import EnhancedSLTPManager

    print("✅ Тест импортов: успешно")
    imports_ok = True
except Exception as e:
    print(f"❌ Тест импортов: {e}")
    imports_ok = False

# Тест 2: Конфигурация
try:
    config_manager = ConfigManager()
    print("✅ Тест конфигурации: успешно")
    config_ok = True
except Exception as e:
    print(f"❌ Тест конфигурации: {e}")
    config_ok = False

# Тест 3: SL/TP Manager
try:
    if config_ok:
        sltp_manager = EnhancedSLTPManager(config_manager)
        print("✅ Тест SL/TP менеджера: успешно")
        sltp_ok = True
    else:
        print("⏭️ Тест SL/TP менеджера: пропущен (конфигурация не работает)")
        sltp_ok = False
except Exception as e:
    print(f"❌ Тест SL/TP менеджера: {e}")
    sltp_ok = False

# Тест 4: ML Calculator
try:
    calculator = RealTimeIndicatorCalculator(use_inference_mode=True)
    print("✅ Тест ML калькулятора: успешно")
    ml_ok = True
except Exception as e:
    print(f"❌ Тест ML калькулятора: {e}")
    ml_ok = False

# Итоги
total_tests = 4
passed = sum([imports_ok, config_ok, sltp_ok, ml_ok])
print("\n" + "=" * 50)
print("📊 ИТОГИ ТЕСТИРОВАНИЯ:")
print("=" * 50)
print(f"   Импорты: {'✅' if imports_ok else '❌'}")
print(f"   Конфигурация: {'✅' if config_ok else '❌'}")
print(f"   SL/TP менеджер: {'✅' if sltp_ok else '❌'}")
print(f"   ML калькулятор: {'✅' if ml_ok else '❌'}")
print(f"\n🏁 Результат: {passed}/{total_tests} тестов пройдено")

if passed == total_tests:
    print("🎉 Все исправления работают корректно!")
else:
    print(f"⚠️ {total_tests - passed} тестов провалено")
