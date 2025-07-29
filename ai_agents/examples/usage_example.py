"""
Примеры использования AI агентов для автоматизации разработки
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.append(str(Path(__file__).parent.parent.parent))

from ai_agents import (  # Основные функции; SDK; Утилиты
    ClaudeAgentBuilder,
    ClaudeCodeSDK,
    analyze_project_architecture,
    autonomous_development,
    generate_tests,
    get_mcp_manager,
    review_code,
)


async def example_code_review():
    """Пример проверки кода"""
    print("\n=== Code Review Example ===")

    # Проверяем конкретный файл
    result = await review_code("ai_agents/agent_manager.py")
    print("Code review completed. First 500 chars:")
    print(result[:500] + "...")


async def example_test_generation():
    """Пример генерации тестов"""
    print("\n=== Test Generation Example ===")

    # Генерируем тесты для модуля
    result = await generate_tests("exchanges/bybit/client.py")
    print("Tests generated successfully")


async def example_architecture_analysis():
    """Пример анализа архитектуры"""
    print("\n=== Architecture Analysis Example ===")

    # Анализируем архитектуру всего проекта
    analysis = await analyze_project_architecture()

    print(f"Total modules: {analysis.metrics['total_modules']}")
    print(f"Total LOC: {analysis.metrics['total_lines_of_code']}")
    print(f"Average complexity: {analysis.metrics['average_complexity']}")
    print(f"Circular dependencies: {len(analysis.circular_dependencies)}")

    # Первые 3 рекомендации
    print("\nTop recommendations:")
    for i, rec in enumerate(analysis.recommendations[:3], 1):
        print(f"{i}. {rec}")


async def example_autonomous_development():
    """Пример автономной разработки функции"""
    print("\n=== Autonomous Development Example ===")

    # Автономно разрабатываем новую функцию
    result = await autonomous_development(
        """
    Создать WebSocket manager для real-time обновлений торговых данных.
    Должен поддерживать:
    - Подключение к нескольким биржам одновременно
    - Автоматическое переподключение при сбоях
    - Подписку на различные типы данных (ордера, сделки, стакан)
    - Эффективное управление подписками
    - Метрики производительности
    """
    )

    print(f"Development status: {'Success' if result else 'Failed'}")


async def example_collaborative_agents():
    """Пример совместной работы агентов"""
    print("\n=== Collaborative Development Example ===")

    from ai_agents import collaborative_development

    # Задача для совместной разработки
    task = """
    Реализовать новую торговую стратегию 'Grid Trading':
    1. Сначала проанализировать архитектуру для интеграции
    2. Разработать стратегию с учетом существующих паттернов
    3. Создать comprehensive тесты
    4. Оптимизировать производительность
    5. Провести security audit
    """

    # Агенты работают последовательно
    results = await collaborative_development(
        task,
        agents=[
            "architect_agent",  # Анализ архитектуры
            "strategy_developer",  # Разработка стратегии
            "test_generator",  # Создание тестов
            "performance_optimizer",  # Оптимизация
            "security_auditor",  # Проверка безопасности
        ],
    )

    print("Collaborative development completed")
    for agent, result in results.items():
        print(f"- {agent}: {'✓' if result else '✗'}")


async def example_custom_agent():
    """Пример создания кастомного агента"""
    print("\n=== Custom Agent Example ===")

    # Создаем SDK и билдер
    sdk = ClaudeCodeSDK()
    builder = ClaudeAgentBuilder(sdk)

    # Создаем кастомного агента для анализа торговых данных
    from ai_agents import ClaudeCodeOptions, ThinkingMode

    custom_options = ClaudeCodeOptions(
        system_prompt="""Вы эксперт по анализу торговых данных.
        Анализируйте паттерны, аномалии и возможности.
        Предоставляйте actionable insights.""",
        thinking_mode=ThinkingMode.THINK_HARD,
        allowed_tools=["Read", "Task", "Bash"],
        max_turns=10,
    )

    # Используем агента
    result = await sdk.query(
        "Проанализируйте структуру данных в data/market_data и предложите оптимизации",
        custom_options,
    )

    print("Custom agent analysis completed")


async def example_mcp_configuration():
    """Пример работы с MCP конфигурацией"""
    print("\n=== MCP Configuration Example ===")

    manager = get_mcp_manager()

    # Проверяем конфигурацию
    print(manager.get_config_summary())

    # Проверяем окружение
    print("\nEnvironment validation:")
    for check, result in manager.validate_environment().items():
        status = "✓" if result else "✗"
        print(f"  {status} {check}")


async def main():
    """Запуск всех примеров"""
    print("AI Agents Usage Examples")
    print("========================")

    # Проверяем окружение
    await example_mcp_configuration()

    # Примеры использования агентов
    # Раскомментируйте нужные примеры:

    # await example_code_review()
    # await example_test_generation()
    await example_architecture_analysis()
    # await example_autonomous_development()
    # await example_collaborative_agents()
    # await example_custom_agent()

    print("\n✓ All examples completed!")


if __name__ == "__main__":
    # Запускаем примеры
    asyncio.run(main())
