#!/usr/bin/env python3
"""
Быстрый тест для проверки критической валидации направления vs доходности
"""

import os
import sys

import numpy as np

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ml.logic.signal_quality_analyzer import SignalQualityAnalyzer


def test_direction_validation():
    """Тестируем критическую валидацию направления"""

    print("🧪 ТЕСТ КРИТИЧЕСКОЙ ВАЛИДАЦИИ НАПРАВЛЕНИЯ vs ДОХОДНОСТИ")
    print("=" * 60)

    # Создаем анализатор
    analyzer = SignalQualityAnalyzer()

    # Тест 1: LONG сигнал с положительными доходностями (должен остаться LONG)
    print("\n1️⃣ Тест LONG сигнал + положительные доходности:")
    future_returns_positive = np.array([0.005, 0.008, 0.003, 0.002])  # Все положительные
    result1 = analyzer._validate_direction_vs_returns("LONG", future_returns_positive)
    print(f"   Результат: {result1} (ожидается LONG)")

    # Тест 2: LONG сигнал с отрицательными доходностями (должен стать SHORT)
    print("\n2️⃣ Тест LONG сигнал + отрицательные доходности:")
    future_returns_negative = np.array([-0.005, -0.008, -0.003, -0.002])  # Все отрицательные
    result2 = analyzer._validate_direction_vs_returns("LONG", future_returns_negative)
    print(f"   Результат: {result2} (ожидается SHORT)")

    # Тест 3: SHORT сигнал с отрицательными доходностями (должен остаться SHORT)
    print("\n3️⃣ Тест SHORT сигнал + отрицательные доходности:")
    result3 = analyzer._validate_direction_vs_returns("SHORT", future_returns_negative)
    print(f"   Результат: {result3} (ожидается SHORT)")

    # Тест 4: SHORT сигнал с положительными доходностями (должен стать LONG)
    print("\n4️⃣ Тест SHORT сигнал + положительные доходности:")
    result4 = analyzer._validate_direction_vs_returns("SHORT", future_returns_positive)
    print(f"   Результат: {result4} (ожидается LONG)")

    # Тест 5: Смешанные доходности с нулевой взвешенной суммой (должен стать NEUTRAL)
    print("\n5️⃣ Тест LONG сигнал + нулевые/смешанные доходности:")
    future_returns_mixed = np.array([0.001, -0.001, 0.0001, -0.0001])  # Почти нулевые
    result5 = analyzer._validate_direction_vs_returns("LONG", future_returns_mixed)
    print(f"   Результат: {result5} (ожидается NEUTRAL)")

    # Тест 6: NEUTRAL сигнал (должен остаться без изменений)
    print("\n6️⃣ Тест NEUTRAL сигнал:")
    result6 = analyzer._validate_direction_vs_returns("NEUTRAL", future_returns_mixed)
    print(f"   Результат: {result6} (ожидается NEUTRAL)")

    print("\n" + "=" * 60)
    print("✅ Все тесты выполнены! Проверьте результаты выше.")

    # Проверим корректность результатов
    tests_passed = 0
    total_tests = 6

    if result1 == "LONG":
        tests_passed += 1
    if result2 == "SHORT":
        tests_passed += 1
    if result3 == "SHORT":
        tests_passed += 1
    if result4 == "LONG":
        tests_passed += 1
    if result5 == "NEUTRAL":
        tests_passed += 1
    if result6 == "NEUTRAL":
        tests_passed += 1

    print(f"\n📊 ИТОГ: {tests_passed}/{total_tests} тестов прошли успешно")
    if tests_passed == total_tests:
        print("🎉 ВСЕ ТЕСТЫ ПРОШЛИ! Валидация работает корректно")
    else:
        print("❌ ЕСТЬ ОШИБКИ! Нужна доработка валидации")


if __name__ == "__main__":
    test_direction_validation()
