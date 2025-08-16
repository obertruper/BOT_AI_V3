#!/usr/bin/env python3
"""
Быстрая кросс-верификация - упрощенный интерфейс
Для частого использования с минимальными настройками

Использование:
    python ai_agents/quick_cross_verify.py "Описание задачи" "Содержание задачи"

Автор: BOT Trading v3 Team
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.append(str(Path(__file__).parent.parent))

from ai_agents.automated_cross_verification import AutomatedCrossVerification


async def quick_verify(description: str, task_content: str):
    """Быстрая кросс-верификация с автоматическими настройками"""

    print("🚀 Быстрая кросс-верификация BOT Trading v3")
    print("=" * 60)
    print(f"📋 Задача: {description}")
    print("🎯 AI системы: ChatGPT o3-pro, Grok v4, Claude Opus 4")
    print("=" * 60)

    # Создаем систему с дефолтными настройками
    cross_verifier = AutomatedCrossVerification()

    try:
        # Быстрый запуск (максимум 3 итерации)
        task_id, report_path = await cross_verifier.run_full_workflow(
            description=description, task_content=task_content, max_iterations=3
        )

        print("\n" + "=" * 60)
        print("✅ КРОСС-ВЕРИФИКАЦИЯ ЗАВЕРШЕНА!")
        print("=" * 60)
        print(f"📋 Task ID: {task_id}")
        print(f"📄 Отчет: {report_path}")

        # Показываем краткую статистику
        status = cross_verifier.get_task_status(task_id)
        print(f"🔢 Итераций: {status['iteration_count']}")

        successful_ai = sum(
            1 for session in status["chat_sessions"].values() if session["status"] == "responded"
        )
        total_ai = len(status["chat_sessions"])
        print(f"🤖 Успешных AI: {successful_ai}/{total_ai}")

        print("\n🎯 Результаты:")
        for ai_system, session_info in status["chat_sessions"].items():
            status_emoji = "✅" if session_info["status"] == "responded" else "❌"
            print(
                f"   {status_emoji} {ai_system.upper()}: {session_info['responses_count']} ответов"
            )

        print(f"\n📖 Читайте детальный анализ в: {report_path}")

        return task_id, report_path

    except Exception as e:
        print(f"\n❌ Ошибка при кросс-верификации: {e}")
        print("🔧 Проверьте:")
        print("   - Доступность интернета")
        print("   - Конфигурацию MCP серверов")
        print("   - Логи в logs/cross_verification.log")
        return None, None


def main():
    """Основная функция"""
    if len(sys.argv) != 3:
        print("❌ Неправильное использование!")
        print("\nИспользование:")
        print('   python ai_agents/quick_cross_verify.py "Описание задачи" "Содержание задачи"')
        print("\nПримеры:")
        print(
            '   python ai_agents/quick_cross_verify.py "Стратегия скальпинга" "Разработай стратегию скальпинга для BTC"'
        )
        print(
            '   python ai_agents/quick_cross_verify.py "Риск-менеджмент" "Как настроить stop-loss для крипто трейдинга"'
        )
        print(
            '   python ai_agents/quick_cross_verify.py "Архитектура бота" "Оптимальная архитектура для HFT бота"'
        )
        sys.exit(1)

    description = sys.argv[1]
    task_content = sys.argv[2]

    # Запускаем быструю кросс-верификацию
    asyncio.run(quick_verify(description, task_content))


if __name__ == "__main__":
    main()
