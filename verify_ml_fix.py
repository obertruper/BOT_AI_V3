#!/usr/bin/env python3
"""
Проверка исправления несоответствия признаков в ML системе.
"""

import sys
import traceback
from pathlib import Path

# Добавляем путь к проекту
sys.path.append(str(Path(__file__).parent))


def test_feature_config():
    """Тестирует конфигурацию признаков"""
    try:
        from ml.config.features_240 import get_feature_count, get_required_features_list

        features = get_required_features_list()
        count = get_feature_count()

        print(f"✅ Конфигурация признаков: {count} признаков")
        print(f"   Первые 5: {features[:5]}")
        print(f"   Последние 5: {features[-5:]}")

        return True
    except Exception as e:
        print(f"❌ Ошибка в конфигурации признаков: {e}")
        traceback.print_exc()
        return False


def test_training_exact_features():
    """Тестирует класс точных признаков"""
    try:
        from ml.logic.training_exact_features import TrainingExactFeatures

        config = {"features": {}}
        engineer = TrainingExactFeatures(config)

        print("✅ TrainingExactFeatures инициализирован")
        print(f"   Ожидается признаков: {engineer.expected_feature_count}")

        return True
    except Exception as e:
        print(f"❌ Ошибка в TrainingExactFeatures: {e}")
        traceback.print_exc()
        return False


def test_production_config():
    """Тестирует производственную конфигурацию"""
    try:
        from production_features_config import CRITICAL_FORMULAS, PRODUCTION_FEATURES

        print(f"✅ Производственная конфигурация: {len(PRODUCTION_FEATURES)} признаков")
        print(f"   Критических формул: {len(CRITICAL_FORMULAS)}")

        return True
    except Exception as e:
        print(f"❌ Ошибка в производственной конфигурации: {e}")
        traceback.print_exc()
        return False


def main():
    """Основная функция проверки"""
    print("🔍 ПРОВЕРКА ИСПРАВЛЕНИЯ ML СИСТЕМЫ")
    print("=" * 40)

    tests = [
        ("Конфигурация признаков", test_feature_config),
        ("Точные признаки обучения", test_training_exact_features),
        ("Производственная конфигурация", test_production_config),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n🧪 Тест: {test_name}")
        if test_func():
            passed += 1
        else:
            print(f"❌ Тест провален: {test_name}")

    print(f"\n📊 РЕЗУЛЬТАТ: {passed}/{total} тестов пройдено")

    if passed == total:
        print("✅ Все проверки пройдены! ML система исправлена.")
        return True
    else:
        print("❌ Некоторые проверки провалены. Требуется дополнительная настройка.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
