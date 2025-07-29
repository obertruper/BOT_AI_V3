#!/usr/bin/env python3
"""
Простой тест системы кросс-проверки через Playwright MCP
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к ai_agents
sys.path.append(str(Path(__file__).parent))

from ai_agents import cross_verify, intelligent_ask, smart_ask


async def test_simple_query():
    """Тест простого запроса"""
    print("🧪 Тестирую простой запрос...")

    try:
        result = await smart_ask("Что такое Python?")

        print("✅ Результат получен:")
        print(f"   Сложность: {result['complexity_score']}/10")
        print(f"   Кросс-проверка: {result['verification_used']}")
        print(f"   Модели: {result['models_used']}")
        print(f"   Ответ: {result['response'][:200]}...")

        return True

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


async def test_complex_query():
    """Тест сложного запроса с кросс-проверкой"""
    print("\n🧪 Тестирую сложный запрос с кросс-проверкой...")

    try:
        result = await smart_ask(
            "!кросс! Проанализируйте архитектуру микросервисов и оптимизацию производительности",
            force_cross_verify=True,
        )

        print("✅ Результат кросс-проверки:")
        print(f"   Сложность: {result['complexity_score']}/10")
        print(f"   Кросс-проверка: {result['verification_used']}")
        print(f"   Модели: {result['models_used']}")
        print(f"   Уверенность: {result['confidence_score']:.2f}")

        if result.get("analysis"):
            analysis = result["analysis"]
            print(f"   Согласие: {analysis.get('agreement_level', 'unknown')}")

        print(f"   Ответ: {result['response'][:300]}...")

        return True

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


async def test_cross_verify_direct():
    """Прямой тест кросс-проверки"""
    print("\n🧪 Тестирую прямую кросс-проверку...")

    try:
        result = await cross_verify(
            "Какие преимущества у языка Python?", models=["grok4", "openai_pro"]
        )

        print("✅ Прямая кросс-проверка:")

        for model, data in result.items():
            print(f"   {model}: {data['status']}")
            if data["status"] == "success":
                print(f"      Ответ: {data['response'][:150]}...")
            else:
                print(f"      Ошибка: {data['error']}")

        return True

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


async def test_browser_tabs():
    """Тест работы с браузерными вкладками"""
    print("\n🧪 Тестирую работу с браузерными вкладками...")

    try:
        # Попробуем простой запрос к Grok через интерфейс
        await intelligent_ask("Привет! Как дела?", force_cross_verify=False)

        print("✅ Браузерные вкладки работают")
        return True

    except Exception as e:
        print(f"❌ Проблема с браузером: {e}")
        print("💡 Убедитесь что у вас открыты вкладки Grok 4 и OpenAI 3 Pro")
        return False


async def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестов системы кросс-проверки")
    print("=" * 60)

    tests = [
        ("Простой запрос", test_simple_query),
        ("Сложный запрос", test_complex_query),
        ("Прямая кросс-проверка", test_cross_verify_direct),
        ("Браузерные вкладки", test_browser_tabs),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)

        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Критическая ошибка в {test_name}: {e}")
            results.append((test_name, False))

    # Итоги
    print("\n📊 ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 60)

    passed = 0
    for test_name, success in results:
        status = "✅ ПРОШЕЛ" if success else "❌ ПРОВАЛЕН"
        print(f"{status:10} {test_name}")
        if success:
            passed += 1

    print(f"\nРезультат: {passed}/{len(results)} тестов прошли")

    if passed == len(results):
        print("🎉 Все тесты прошли! Система кросс-проверки готова к использованию.")
    else:
        print(
            "⚠️ Некоторые тесты провалены. Проверьте настройки браузера и MCP серверов."
        )

    return passed == len(results)


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Фатальная ошибка: {e}")
        sys.exit(1)
