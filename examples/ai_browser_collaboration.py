#!/usr/bin/env python3
"""
Реальная демонстрация: Claude Code SDK запускает браузер и общается с ChatGPT и Grok
для совместного решения задачи по оптимизации торговой стратегии
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_agents import ClaudeCodeOptions, ClaudeCodeSDK, ThinkingMode


async def real_browser_ai_collaboration():
    """
    Реальный пример: Claude открывает браузер и общается с другими AI
    """
    print("🚀 РЕАЛЬНАЯ КОЛЛАБОРАЦИЯ AI ЧЕРЕЗ БРАУЗЕР\n")
    print("Claude будет:")
    print("1. Открывать браузер с Playwright")
    print("2. Заходить на ChatGPT и Grok")
    print("3. Вести диалог с ними о торговой стратегии")
    print("4. Собирать их ответы и создавать финальное решение\n")

    sdk = ClaudeCodeSDK()

    # Настройки с браузерными возможностями
    options = ClaudeCodeOptions(
        model="opus",  # Для сложной задачи нужна мощная модель
        thinking_mode=ThinkingMode.THINK_HARD,
        allowed_tools=[
            "Read",
            "Write",
            "Edit",
            "Bash",
            # MCP браузерные инструменты
            "mcp__playwright__browser_navigate",
            "mcp__playwright__browser_click",
            "mcp__playwright__browser_type",
            "mcp__playwright__browser_snapshot",
            "mcp__playwright__browser_wait_for",
            "mcp__playwright__browser_take_screenshot",
            # Sequential thinking для планирования
            "mcp__sequential-thinking__sequentialthinking",
        ],
        max_turns=30,  # Много шагов для полного диалога
    )

    # Задача для коллаборации
    task = """
    Используй Playwright чтобы открыть браузер и провести коллаборацию с ChatGPT и Grok
    для создания оптимальной торговой стратегии.

    ВАЖНО: Это реальная задача, не симуляция!

    Шаги:
    1. Открой браузер через Playwright
    2. Зайди на chat.openai.com (или chatgpt.com)
    3. Задай ChatGPT вопрос: "Какие ключевые компоненты должна включать высокочастотная
       торговая стратегия для криптовалют? Дай 5 конкретных компонентов с объяснением."
    4. Дождись ответа и сохрани его
    5. Открой новую вкладку и зайди на grok.x.ai (или x.com/i/grok)
    6. Покажи Grok ответ ChatGPT и спроси: "ChatGPT предложил эти компоненты для HFT
       стратегии: [вставь ответ]. Что ты думаешь? Что бы ты добавил или изменил?"
    7. Сохрани ответ Grok
    8. Вернись к ChatGPT и покажи ему ответ Grok для финального мнения
    9. На основе всего диалога создай файл strategy_components.md с:
       - Консолидированным списком компонентов
       - Обоснованием каждого
       - Планом имплементации

    Делай скриншоты важных моментов диалога.
    Если нужна авторизация, укажи это и предложи альтернативный план.
    """

    print("🤖 Claude запускает браузер и начинает коллаборацию...\n")

    try:
        result = await sdk.query(task, options)
        print("\n✅ Коллаборация завершена!")
        print("\n📄 Результат сохранен в strategy_components.md")

        # Проверяем созданные файлы
        if Path("strategy_components.md").exists():
            print("\n📋 Содержимое стратегии:")
            with open("strategy_components.md", "r") as f:
                print(f.read()[:500] + "...")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print("\n💡 Возможные причины:")
        print("- Нужна авторизация на сайтах AI")
        print("- Браузер не установлен (запустите: npx playwright install)")
        print("- MCP Playwright сервер не настроен")


async def automated_cross_verification():
    """
    Автоматическая кросс-верификация решения через несколько AI
    """
    print("\n\n🔄 АВТОМАТИЧЕСКАЯ КРОСС-ВЕРИФИКАЦИЯ\n")

    sdk = ClaudeCodeSDK()

    # Сначала Claude создает торговую стратегию
    print("1️⃣ Claude создает базовую стратегию...")

    strategy_task = """
    Создай простую momentum-based торговую стратегию для BTC/USDT.
    Включи:
    1. Условия входа в позицию
    2. Размер позиции и risk management
    3. Stop loss и take profit
    4. Условия выхода

    Сохрани в momentum_strategy.py с полной имплементацией.
    """

    strategy_options = ClaudeCodeOptions(
        model="sonnet", allowed_tools=["Write"], max_turns=3
    )

    await sdk.query(strategy_task, strategy_options)
    print("✅ Базовая стратегия создана")

    # Теперь проверяем через браузер с другими AI
    print("\n2️⃣ Запускаем кросс-верификацию через браузер...")

    verification_task = """
    Открой браузер и проведи кросс-верификацию созданной momentum_strategy.py:

    1. Прочитай код стратегии из momentum_strategy.py
    2. Открой ChatGPT и попроси проверить эту стратегию на:
       - Логические ошибки
       - Риски и уязвимости
       - Предложения по улучшению
    3. Если есть доступ к Claude.ai, открой в новой вкладке и попроси
       второе мнение о стратегии
    4. Создай файл strategy_verification_report.md с:
       - Найденными проблемами
       - Предложениями от каждого AI
       - Финальными рекомендациями
       - Уровнем уверенности (1-10)

    Если не можешь получить доступ к AI сайтам, создай план
    альтернативной верификации через доступные инструменты.
    """

    verification_options = ClaudeCodeOptions(
        model="opus",
        thinking_mode=ThinkingMode.THINK,
        allowed_tools=[
            "Read",
            "Write",
            "mcp__playwright__browser_navigate",
            "mcp__playwright__browser_click",
            "mcp__playwright__browser_type",
            "mcp__playwright__browser_snapshot",
            "mcp__playwright__browser_take_screenshot",
        ],
        max_turns=20,
    )

    await sdk.query(verification_task, verification_options)
    print("✅ Кросс-верификация завершена")


async def multi_ai_research():
    """
    Исследование через несколько AI источников
    """
    print("\n\n🔬 MULTI-AI ИССЛЕДОВАНИЕ\n")

    sdk = ClaudeCodeSDK()

    research_task = """
    Проведи исследование "Лучшие практики для низколатентной торговли крипто"
    используя несколько источников:

    1. Открой браузер через Playwright
    2. Исследуй через поисковые системы:
       - Google: "crypto HFT low latency best practices 2024"
       - Проверь первые 3-5 результатов
    3. Если возможно, задай вопросы на:
       - ChatGPT: технические аспекты низкой латентности
       - Claude.ai: архитектурные решения
       - Perplexity.ai: последние исследования и papers
    4. Собери информацию о:
       - Оптимальные языки программирования (Rust vs C++ vs Go)
       - Архитектурные паттерны
       - Сетевые оптимизации
       - Hardware рекомендации
    5. Создай comprehensive отчет low_latency_research.md

    Делай скриншоты ключевых находок.
    Если какие-то сайты недоступны, используй альтернативные источники.
    """

    research_options = ClaudeCodeOptions(
        model="opus",
        thinking_mode=ThinkingMode.THINK_HARDER,
        allowed_tools=[
            "Write",
            "Edit",
            "mcp__playwright__browser_navigate",
            "mcp__playwright__browser_click",
            "mcp__playwright__browser_type",
            "mcp__playwright__browser_snapshot",
            "mcp__playwright__browser_wait_for",
            "mcp__playwright__browser_take_screenshot",
            "mcp__sequential-thinking__sequentialthinking",
        ],
        max_turns=40,
    )

    print("🔍 Claude проводит multi-source исследование...")
    print("Это может занять несколько минут...\n")

    await sdk.query(research_task, research_options)
    print("\n✅ Исследование завершено!")


async def live_market_analysis():
    """
    Реальный анализ рынка через браузер
    """
    print("\n\n📊 LIVE MARKET ANALYSIS\n")

    sdk = ClaudeCodeSDK()

    market_task = """
    Проведи реальный анализ текущего состояния крипто рынка:

    1. Открой браузер
    2. Зайди на TradingView.com или CoinMarketCap.com
    3. Собери данные о:
       - Топ 10 криптовалют по капитализации
       - Их изменение за 24ч
       - Общий sentiment рынка
    4. Зайди на crypto новостные сайты (CoinDesk, CoinTelegraph)
    5. Найди 3-5 ключевых новостей влияющих на рынок
    6. Если возможно, спроси мнение у AI:
       - "Based on current market data [data], what's the short-term outlook?"
    7. Создай market_analysis_report.md с:
       - Текущим состоянием рынка
       - Ключевыми новостями
       - Техническим анализом (если доступен)
       - Прогнозом на ближайшие 24-48 часов
       - Рекомендациями для трейдеров

    Сделай скриншоты графиков и ключевых данных.
    """

    market_options = ClaudeCodeOptions(
        model="sonnet",
        thinking_mode=ThinkingMode.NORMAL,
        allowed_tools=[
            "Write",
            "mcp__playwright__browser_navigate",
            "mcp__playwright__browser_snapshot",
            "mcp__playwright__browser_take_screenshot",
            "mcp__playwright__browser_wait_for",
        ],
        max_turns=25,
    )

    print("📈 Claude анализирует реальный рынок...")
    await sdk.query(market_task, market_options)
    print("\n✅ Анализ рынка завершен!")


async def main():
    """Главное меню для выбора демонстрации"""
    print("=" * 60)
    print("🌐 РЕАЛЬНАЯ AI КОЛЛАБОРАЦИЯ ЧЕРЕЗ БРАУЗЕР")
    print("=" * 60)
    print("\nВыберите демонстрацию:")
    print("1. AI коллаборация через браузер (ChatGPT + Grok)")
    print("2. Автоматическая кросс-верификация стратегии")
    print("3. Multi-AI исследование")
    print("4. Live анализ крипто рынка")
    print("5. Запустить все демонстрации")

    choice = input("\nВаш выбор (1-5): ")

    demos = {
        "1": ("AI Коллаборация", real_browser_ai_collaboration),
        "2": ("Кросс-верификация", automated_cross_verification),
        "3": ("Multi-AI исследование", multi_ai_research),
        "4": ("Live Market анализ", live_market_analysis),
    }

    try:
        if choice == "5":
            for name, func in demos.values():
                print(f"\n\n{'='*60}")
                print(f"Запуск: {name}")
                print("=" * 60)
                await func()
        elif choice in demos:
            await demos[choice][1]()
        else:
            print("❌ Неверный выбор")
    except KeyboardInterrupt:
        print("\n\n⚠️ Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print("\n💡 Убедитесь что:")
        print("- Playwright установлен: npx playwright install")
        print("- MCP серверы настроены в ai_agents/configs/mcp_servers.yaml")
        print("- Claude CLI авторизован")


if __name__ == "__main__":
    print("\n⚠️  ВАЖНО: Для работы нужно:")
    print("1. Установленный Playwright: npx playwright install chromium")
    print("2. Настроенные MCP серверы")
    print("3. Возможно потребуется авторизация на AI сайтах")
    print("\nНажмите Enter для продолжения или Ctrl+C для отмены...")
    input()

    asyncio.run(main())
