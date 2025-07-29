#!/usr/bin/env python3
"""
Реальная демонстрация работы с браузером через Playwright MCP
Показывает как Claude может открыть браузер и взаимодействовать с другими AI
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_agents import ClaudeCodeOptions, ClaudeCodeSDK, ThinkingMode


async def simple_browser_demo():
    """
    Простой пример: Claude открывает браузер и делает скриншот
    """
    print("🌐 ПРОСТАЯ ДЕМОНСТРАЦИЯ БРАУЗЕРА\n")

    sdk = ClaudeCodeSDK()

    # Настройки для работы с браузером
    options = ClaudeCodeOptions(
        model="sonnet",
        thinking_mode=ThinkingMode.NORMAL,
        allowed_tools=[
            "Write",
            # Playwright MCP инструменты
            "mcp__playwright__browser_navigate",
            "mcp__playwright__browser_take_screenshot",
            "mcp__playwright__browser_snapshot",
        ],
        max_turns=5,
    )

    task = """
    Используй Playwright чтобы:
    1. Открыть браузер (он откроется визуально, не в headless режиме)
    2. Перейти на https://coinmarketcap.com
    3. Подожди пока страница загрузится
    4. Сделай скриншот топ-10 криптовалют
    5. Сохрани скриншот как crypto_top10.png

    Это реальная задача с настоящим браузером!
    """

    print("🤖 Claude запускает браузер...\n")

    result = await sdk.query(task, options)
    print("\n✅ Готово! Проверьте файл crypto_top10.png")


async def ai_conversation_demo():
    """
    Демонстрация диалога с ChatGPT через браузер
    """
    print("\n\n💬 ДИАЛОГ С AI ЧЕРЕЗ БРАУЗЕР\n")

    sdk = ClaudeCodeSDK()

    options = ClaudeCodeOptions(
        model="opus",  # Для сложной задачи
        thinking_mode=ThinkingMode.THINK,
        allowed_tools=[
            "Write",
            "Read",
            "mcp__playwright__browser_navigate",
            "mcp__playwright__browser_click",
            "mcp__playwright__browser_type",
            "mcp__playwright__browser_snapshot",
            "mcp__playwright__browser_wait_for",
            "mcp__playwright__browser_take_screenshot",
        ],
        max_turns=20,
    )

    task = """
    Попробуй открыть ChatGPT и задать вопрос:

    1. Открой браузер (визуально, не headless)
    2. Перейди на https://chatgpt.com или https://chat.openai.com
    3. Если появится страница входа - сделай скриншот и сохрани как chatgpt_login.png
    4. Если есть доступ к чату - попробуй написать:
       "What are the key components of a high-frequency trading system?"
    5. Сделай скриншот результата

    Если не получается войти, создай файл ai_access_report.md с описанием:
    - Что ты увидел
    - Какие шаги предпринял
    - Почему не получилось
    - Альтернативные способы получить информацию

    ВАЖНО: Браузер откроется визуально, ты увидишь реальные действия!
    """

    print("🌐 Claude открывает браузер для диалога с AI...")
    print("⚠️  Вы увидите реальный браузер!\n")

    result = await sdk.query(task, options)
    print("\n📄 Результат сохранен")


async def market_research_demo():
    """
    Исследование рынка через браузер
    """
    print("\n\n📊 ИССЛЕДОВАНИЕ РЫНКА ЧЕРЕЗ БРАУЗЕР\n")

    sdk = ClaudeCodeSDK()

    options = ClaudeCodeOptions(
        model="sonnet",
        thinking_mode=ThinkingMode.NORMAL,
        allowed_tools=[
            "Write",
            "mcp__playwright__browser_navigate",
            "mcp__playwright__browser_snapshot",
            "mcp__playwright__browser_wait_for",
            "mcp__playwright__browser_take_screenshot",
            "mcp__sequential-thinking__sequentialthinking",  # Для анализа
        ],
        max_turns=15,
    )

    task = """
    Проведи быстрое исследование крипто рынка:

    1. Открой браузер (визуально)
    2. Зайди на TradingView.com
    3. Найди график BTC/USDT
    4. Сделай скриншот графика
    5. Зайди на CoinMarketCap.com
    6. Собери данные о топ-5 криптовалют:
       - Название
       - Цена
       - Изменение за 24ч
       - Капитализация
    7. Создай файл market_summary.md с:
       - Данными о топ-5 криптовалют
       - Общим состоянием рынка (растет/падает)
       - Скриншотами

    Используй Sequential Thinking для анализа данных.
    """

    print("📈 Claude исследует крипто рынок...")
    print("🌐 Браузер откроется визуально\n")

    result = await sdk.query(task, options)
    print("\n✅ Исследование завершено! Проверьте market_summary.md")


async def main():
    """Главное меню"""
    print("=" * 60)
    print("🌐 РЕАЛЬНАЯ РАБОТА С БРАУЗЕРОМ ЧЕРЕЗ PLAYWRIGHT")
    print("=" * 60)
    print("\n⚠️  ВАЖНО:")
    print("- Браузер будет открываться ВИЗУАЛЬНО (не headless)")
    print("- Вы увидите все действия в реальном времени")
    print("- Для некоторых сайтов может потребоваться авторизация\n")

    print("Выберите демонстрацию:")
    print("1. Простой скриншот криптовалют")
    print("2. Попытка диалога с ChatGPT")
    print("3. Исследование крипто рынка")
    print("4. Запустить все демонстрации")

    choice = input("\nВаш выбор (1-4): ")

    demos = {
        "1": simple_browser_demo,
        "2": ai_conversation_demo,
        "3": market_research_demo,
    }

    try:
        if choice == "4":
            for demo in demos.values():
                await demo()
                print("\n" + "=" * 60 + "\n")
        elif choice in demos:
            await demos[choice]()
        else:
            print("❌ Неверный выбор")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print("\n💡 Проверьте:")
        print("1. Установлен ли Playwright: npx playwright install chromium")
        print("2. Настроены ли MCP серверы")
        print("3. Работает ли Claude CLI")


if __name__ == "__main__":
    print("\n🚀 Запуск демонстрации работы с браузером...")
    print("\n📋 Требования:")
    print("1. Playwright: npx playwright install chromium")
    print("2. MCP Playwright сервер должен быть включен")
    print("3. Claude CLI должен быть авторизован")

    input("\nНажмите Enter для продолжения...")

    asyncio.run(main())
