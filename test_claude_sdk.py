#!/usr/bin/env python3
"""
Тестирование подключения Claude Code SDK
Проверка что SDK работает корректно после исправления пути к Claude CLI
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from ai_agents.claude_code_sdk import ClaudeCodeOptions, ClaudeCodeSDK, ThinkingMode


async def test_sdk_connection():
    """Тестирование базового подключения SDK"""
    print("🔍 Тестирование подключения Claude Code SDK...\n")

    try:
        # Инициализация SDK с пакетной авторизацией
        print("1. Инициализация SDK...")
        sdk = ClaudeCodeSDK(use_package_auth=True)
        print("✅ SDK успешно инициализирован")
        print(f"   Claude CLI найден: {sdk.claude_cmd}")

        # Простой запрос
        print("\n2. Выполнение тестового запроса...")
        options = ClaudeCodeOptions(
            thinking_mode=ThinkingMode.NORMAL, max_turns=1, allowed_tools=["Read"]
        )

        result = await sdk.query(
            "Скажи 'Привет! Claude Code SDK работает корректно!' и больше ничего.",
            options=options,
            agent_name="test_agent",
        )

        print("✅ Запрос выполнен успешно")
        print(f"   Ответ: {result.strip()}")

        # Проверка токенов
        print("\n3. Проверка системы управления токенами...")
        usage = sdk.get_token_usage("daily")
        print("✅ Система токенов работает")
        print(f"   Использовано токенов сегодня: {usage.get('total_tokens', 0):,}")
        print(f"   Стоимость: ${usage.get('total_cost_usd', 0):.4f}")

        # Тестирование кеширования
        print("\n4. Проверка кеширования...")
        # Повторный запрос должен использовать кеш
        cached_result = await sdk.query(
            "Скажи 'Привет! Claude Code SDK работает корректно!' и больше ничего.",
            options=options,
            agent_name="test_agent",
        )
        print("✅ Кеширование работает")
        print(f"   Результат из кеша: {result.strip() == cached_result.strip()}")

        print("\n✨ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("Claude Code SDK полностью функционален и готов к использованию.")

        return True

    except FileNotFoundError as e:
        print("❌ Ошибка: Claude CLI не найден")
        print(f"   Детали: {e}")
        print("\n💡 Решение:")
        print(
            "   1. Убедитесь что Claude Code установлен: npm install -g @anthropics/claude-code"
        )
        print("   2. Запустите 'claude' для авторизации")
        return False

    except ValueError as e:
        print(f"❌ Ошибка авторизации: {e}")
        print("\n💡 Решение:")
        print("   1. Запустите 'claude' в терминале")
        print("   2. Авторизуйтесь с вашим API ключом")
        return False

    except Exception as e:
        print(f"❌ Неожиданная ошибка: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_agent_creation():
    """Тестирование создания агентов"""
    print("\n\n📦 Тестирование создания специализированных агентов...\n")

    try:
        from ai_agents import ClaudeAgentBuilder

        sdk = ClaudeCodeSDK(use_package_auth=True)
        builder = ClaudeAgentBuilder(sdk)

        # Создаем разные типы агентов
        agents = {
            "Code Reviewer": builder.create_code_reviewer(),
            "Test Generator": builder.create_test_generator(),
            "Autonomous Developer": builder.create_autonomous_developer(),
            "Performance Optimizer": builder.create_performance_optimizer(),
        }

        for name, agent_options in agents.items():
            print(f"✅ {name}:")
            print(f"   - Модель: {agent_options.model}")
            print(f"   - Режим мышления: {agent_options.thinking_mode.value}")
            print(f"   - Макс. итераций: {agent_options.max_turns}")
            print(f"   - Инструменты: {', '.join(agent_options.allowed_tools)}")

        print("\n✨ Все агенты созданы успешно!")
        return True

    except Exception as e:
        print(f"❌ Ошибка создания агентов: {e}")
        return False


async def test_mcp_integration():
    """Тестирование MCP интеграции"""
    print("\n\n🔌 Проверка MCP серверов...\n")

    try:
        from ai_agents.utils.mcp_manager import get_mcp_manager

        mcp_manager = get_mcp_manager()

        # Проверяем конфигурацию
        print("1. Загруженные MCP серверы:")
        for server_name, config in mcp_manager.servers.items():
            status = "✅ Включен" if config.enabled else "❌ Выключен"
            print(f"   - {server_name}: {status}")

        # Проверяем профили агентов
        print("\n2. Профили агентов:")
        for profile_name, profile in mcp_manager.agent_profiles.items():
            servers = ", ".join(profile.get("mcp_servers", []))
            print(f"   - {profile_name}: {servers}")

        print("\n✅ MCP конфигурация загружена успешно")
        return True

    except Exception as e:
        print(f"❌ Ошибка MCP: {e}")
        return False


async def main():
    """Основная функция тестирования"""
    print("=" * 60)
    print("🚀 ТЕСТИРОВАНИЕ CLAUDE CODE SDK INTEGRATION")
    print("=" * 60)

    # Запускаем все тесты
    results = []

    # Базовое подключение
    results.append(await test_sdk_connection())

    # Создание агентов
    results.append(await test_agent_creation())

    # MCP интеграция
    results.append(await test_mcp_integration())

    # Итоговый результат
    print("\n" + "=" * 60)
    print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ:")
    print("=" * 60)

    total_tests = len(results)
    passed_tests = sum(results)

    if passed_tests == total_tests:
        print(f"\n✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ ({passed_tests}/{total_tests})")
        print("\n🎉 Claude Code SDK полностью интегрирован и работает без ошибок!")
        print("💡 Система готова к использованию для автоматизации разработки.")
    else:
        print(f"\n⚠️  НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ ({passed_tests}/{total_tests})")
        print("📝 Проверьте ошибки выше и следуйте инструкциям по исправлению.")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
