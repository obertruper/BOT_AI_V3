#!/usr/bin/env python3
"""
Тестовый скрипт для проверки исправления API компонента
"""

import subprocess
import sys
import time

import requests


def test_api_startup():
    """Тест запуска API"""
    print("🧪 Тестирование запуска API компонента...")

    # Запуск API в фоне
    process = subprocess.Popen(
        ["venv/bin/python", "web/launcher.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Ждём запуска
    print("⏳ Ожидание запуска API...")
    time.sleep(5)

    try:
        # Проверяем health check
        response = requests.get("http://localhost:8080/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ API успешно запущен и отвечает на health check")
            health_data = response.json()
            print(f"📊 Status: {health_data.get('status', 'unknown')}")
            success = True
        else:
            print(f"❌ API вернул код {response.status_code}")
            success = False

    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка подключения к API: {e}")
        success = False

    finally:
        # Завершаем процесс
        process.terminate()
        process.wait(timeout=5)
        print("🛑 API процесс завершён")

    return success


def test_unified_launcher():
    """Тест запуска через unified_launcher"""
    print("🧪 Тестирование unified_launcher в API режиме...")

    # Запуск через unified_launcher
    process = subprocess.Popen(
        ["venv/bin/python", "unified_launcher.py", "--mode=api"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Ждём запуска
    print("⏳ Ожидание запуска через unified_launcher...")
    time.sleep(10)

    try:
        # Проверяем API
        response = requests.get("http://localhost:8080/", timeout=5)
        if response.status_code == 200:
            print("✅ unified_launcher успешно запустил API")
            api_data = response.json()
            print(f"📊 API Version: {api_data.get('version', 'unknown')}")
            success = True
        else:
            print(f"❌ API через unified_launcher вернул код {response.status_code}")
            success = False

    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка подключения к API через unified_launcher: {e}")
        success = False

    finally:
        # Завершаем процесс
        process.terminate()
        process.wait(timeout=10)
        print("🛑 unified_launcher процесс завершён")

    return success


def main():
    """Главная функция тестирования"""
    print("=" * 60)
    print("🔧 Тестирование исправления API компонента BOT_AI_V3")
    print("=" * 60)

    # Тест 1: Прямой запуск API
    direct_success = test_api_startup()
    print()

    # Тест 2: Запуск через unified_launcher
    launcher_success = test_unified_launcher()
    print()

    # Результаты
    print("=" * 60)
    print("📋 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print(f"📌 Прямой запуск API: {'✅ УСПЕХ' if direct_success else '❌ ОШИБКА'}")
    print(
        f"📌 Через unified_launcher: {'✅ УСПЕХ' if launcher_success else '❌ ОШИБКА'}"
    )

    if direct_success and launcher_success:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО! API исправлен.")
        return 0
    else:
        print("\n⚠️ ЕСТЬ ПРОБЛЕМЫ, требуется дополнительная отладка.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
