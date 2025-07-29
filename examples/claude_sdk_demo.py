#!/usr/bin/env python3
"""
Демонстрация работы Claude Code SDK - простой пример
Показывает как SDK автоматизирует задачи разработки
"""
import asyncio
from pathlib import Path
import sys

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_agents import ClaudeCodeSDK, ClaudeCodeOptions, ThinkingMode


async def simple_example():
    """Простой пример: Claude анализирует код и предлагает улучшения"""
    print("🎯 ПРОСТОЙ ПРИМЕР: Анализ кода\n")
    
    # 1. Создаем SDK - это наш "пульт управления"
    sdk = ClaudeCodeSDK()
    
    # 2. Настраиваем параметры - что Claude может делать
    options = ClaudeCodeOptions(
        model="sonnet",                    # Используем модель Sonnet
        thinking_mode=ThinkingMode.NORMAL, # Обычный режим мышления
        allowed_tools=["Read", "Grep"],    # Может читать файлы и искать
        max_turns=3                        # Максимум 3 действия
    )
    
    # 3. Даем задание
    task = """
    Проанализируй файл trading/engine.py и скажи:
    1. Какие основные функции он выполняет?
    2. Есть ли потенциальные проблемы?
    3. Что можно улучшить?
    
    Будь краток - 3-5 пунктов.
    """
    
    # 4. Claude выполняет задание
    print("🤖 Claude анализирует код...")
    result = await sdk.query(task, options)
    
    print("\n📋 Результат анализа:")
    print(result)
    
    # 5. Проверяем использование токенов
    usage = sdk.get_token_usage()
    print(f"\n💰 Использовано токенов: {usage.get('total_tokens', 0):,}")


async def thinking_example():
    """Пример с пошаговым мышлением для сложной задачи"""
    print("\n\n🧠 ПРИМЕР С МЫШЛЕНИЕМ: Решение сложной задачи\n")
    
    sdk = ClaudeCodeSDK()
    
    # Включаем режим "думать вслух"
    options = ClaudeCodeOptions(
        model="sonnet",
        thinking_mode=ThinkingMode.THINK_HARD,  # Глубокое обдумывание
        allowed_tools=["Read", "Write", "Edit", "Bash"],
        max_turns=10
    )
    
    task = """
    Создай простую функцию для расчета скользящей средней (moving average) 
    для торговых данных. Функция должна:
    1. Принимать список цен и период
    2. Обрабатывать edge cases
    3. Быть оптимизированной
    4. Иметь docstring и type hints
    
    Сохрани в файл examples/moving_average.py
    """
    
    print("🤖 Claude думает над задачей...")
    print("(В режиме THINK_HARD он будет размышлять пошагово)\n")
    
    result = await sdk.query(task, options)
    
    print("\n✅ Задача выполнена!")
    print("📄 Файл создан: examples/moving_average.py")


async def mcp_sequential_thinking_example():
    """Пример использования MCP Sequential Thinking для сложного анализа"""
    print("\n\n🔮 MCP SEQUENTIAL THINKING: Пошаговое решение\n")
    
    sdk = ClaudeCodeSDK()
    
    # Используем Sequential Thinking через MCP
    options = ClaudeCodeOptions(
        model="opus",  # Для сложных задач лучше Opus
        thinking_mode=ThinkingMode.NORMAL,
        allowed_tools=[
            "Read", "Grep", "Task",
            "mcp__sequential-thinking__sequentialthinking"  # MCP инструмент
        ],
        max_turns=15
    )
    
    task = """
    Используй Sequential Thinking чтобы проанализировать архитектуру 
    торгового бота в этом проекте:
    
    1. Начни с изучения основных компонентов
    2. Найди связи между ними
    3. Определи потенциальные узкие места
    4. Предложи улучшения архитектуры
    
    Думай пошагово, пересматривай свои выводы если нужно.
    """
    
    print("🧩 Claude использует Sequential Thinking MCP...")
    print("Это позволяет ему:")
    print("- Думать пошагово")
    print("- Пересматривать предыдущие мысли")
    print("- Строить гипотезы и проверять их")
    print("- Адаптировать план по ходу анализа\n")
    
    result = await sdk.query(task, options)
    
    print("\n📊 Результат анализа с Sequential Thinking:")
    print(result[:500] + "..." if len(result) > 500 else result)


async def autonomous_development_example():
    """Пример автономной разработки - Claude сам все делает"""
    print("\n\n🚀 АВТОНОМНАЯ РАЗРАБОТКА: Claude все делает сам\n")
    
    from ai_agents import autonomous_development
    
    task = """
    Создай утилиту для мониторинга производительности торговых стратегий:
    
    1. Класс PerformanceMonitor в файле monitoring/performance.py
    2. Методы для отслеживания:
       - Прибыль/убыток (PnL)
       - Винрейт (процент успешных сделок)
       - Максимальная просадка
       - Коэффициент Шарпа
    3. Сохранение метрик в JSON
    4. Генерация отчетов
    5. Напиши тесты
    
    Работай полностью автономно.
    """
    
    print("🤖 Claude работает автономно...")
    print("Он будет:")
    print("1. EXPLORE - Изучать существующий код")
    print("2. PLAN - Планировать реализацию")
    print("3. IMPLEMENT - Писать код")
    print("4. TEST - Создавать и запускать тесты")
    print("5. REFINE - Улучшать на основе результатов\n")
    
    result = await autonomous_development(task)
    
    print("\n✅ Автономная разработка завершена!")
    print(f"Результат: {result.summary}")


async def collaborative_example():
    """Пример совместной работы нескольких агентов"""
    print("\n\n👥 КОЛЛАБОРАЦИЯ: Несколько агентов работают вместе\n")
    
    from ai_agents import MultiModelOrchestrator, AgentConfig
    
    orchestrator = MultiModelOrchestrator()
    
    # Создаем специализированных агентов
    architect = orchestrator.create_agent("claude", AgentConfig(
        name="architect",
        role="Архитектор системы",
        system_prompt="Ты опытный архитектор. Проектируй чистую архитектуру.",
        allowed_tools=["Read", "Write"],
        thinking_mode=ThinkingMode.THINK
    ))
    
    developer = orchestrator.create_agent("claude", AgentConfig(
        name="developer", 
        role="Разработчик",
        system_prompt="Ты опытный разработчик. Пиши чистый, эффективный код.",
        allowed_tools=["Read", "Write", "Edit", "Bash"],
        thinking_mode=ThinkingMode.NORMAL
    ))
    
    tester = orchestrator.create_agent("claude", AgentConfig(
        name="tester",
        role="QA инженер", 
        system_prompt="Ты QA инженер. Находи баги и пиши тесты.",
        allowed_tools=["Read", "Write", "Bash"],
        thinking_mode=ThinkingMode.NORMAL
    ))
    
    print("👥 Агенты созданы:")
    print("- 🏗️ Архитектор - проектирует структуру")
    print("- 💻 Разработчик - пишет код")
    print("- 🧪 Тестировщик - проверяет качество\n")
    
    # Они работают по очереди
    task = "Создать модуль для работы с WebSocket для real-time данных с бирж"
    
    print(f"📋 Задача: {task}\n")
    
    # 1. Архитектор проектирует
    print("1️⃣ Архитектор проектирует структуру...")
    design = await architect.execute_task(f"Спроектируй архитектуру для: {task}")
    
    # 2. Разработчик реализует
    print("2️⃣ Разработчик пишет код на основе дизайна...")
    code = await developer.execute_task(
        f"Реализуй следующий дизайн: {design[:200]}...",
        context={"design": design}
    )
    
    # 3. Тестировщик проверяет
    print("3️⃣ Тестировщик создает тесты...")
    tests = await tester.execute_task(
        "Напиши unit тесты для созданного WebSocket модуля",
        context={"implementation": code}
    )
    
    print("\n✅ Коллаборация завершена!")
    print("Все агенты выполнили свои роли")


async def main():
    """Запуск всех примеров"""
    print("=" * 60)
    print("🎓 ДЕМОНСТРАЦИЯ CLAUDE CODE SDK")
    print("=" * 60)
    
    examples = [
        ("Простой пример", simple_example),
        ("Пример с мышлением", thinking_example),
        ("MCP Sequential Thinking", mcp_sequential_thinking_example),
        ("Автономная разработка", autonomous_development_example),
        ("Коллаборация агентов", collaborative_example)
    ]
    
    print("\nВыберите пример для запуска:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"{i}. {name}")
    print("0. Запустить все примеры")
    
    choice = input("\nВаш выбор (0-5): ")
    
    try:
        choice = int(choice)
        if choice == 0:
            # Запускаем все
            for name, func in examples:
                await func()
        elif 1 <= choice <= len(examples):
            # Запускаем выбранный
            await examples[choice-1][1]()
        else:
            print("❌ Неверный выбор")
    except ValueError:
        print("❌ Введите число")


if __name__ == "__main__":
    print("\n🚀 Запуск демонстрации Claude Code SDK...")
    print("ℹ️  Убедитесь, что Claude CLI настроен и авторизован\n")
    
    asyncio.run(main())