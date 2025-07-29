#!/usr/bin/env python3
"""
CLI интерфейс для автоматизированной кросс-верификации
Простой способ запуска кросс-верификации из командной строки

Использование:
    python ai_agents/cli_cross_verification.py start "Описание задачи" "Содержание задачи"
    python ai_agents/cli_cross_verification.py status <task_id>
    python ai_agents/cli_cross_verification.py list
    python ai_agents/cli_cross_verification.py feedback <task_id>

Автор: BOT Trading v3 Team
"""

import asyncio
import argparse
import sys
import json
from pathlib import Path
from typing import Optional

# Добавляем путь к проекту
sys.path.append(str(Path(__file__).parent.parent))

from ai_agents.automated_cross_verification import AutomatedCrossVerification


class CrossVerificationCLI:
    """CLI интерфейс для кросс-верификации"""
    
    def __init__(self):
        self.cross_verifier = AutomatedCrossVerification()
    
    async def start_verification(self, description: str, task_content: str, max_iterations: Optional[int] = None):
        """Запуск новой кросс-верификации"""
        print(f"🚀 Запуск кросс-верификации: {description}")
        print("=" * 60)
        
        try:
            # Запускаем полный workflow
            task_id, report_path = await self.cross_verifier.run_full_workflow(
                description, task_content, max_iterations
            )
            
            print("✅ Кросс-верификация завершена!")
            print(f"📋 Task ID: {task_id}")
            print(f"📄 Отчет: {report_path}")
            
            # Показываем детальный статус
            await self.show_task_status(task_id)
            
            return task_id
            
        except Exception as e:
            print(f"❌ Ошибка при выполнении кросс-верификации: {e}")
            return None
    
    async def show_task_status(self, task_id: str):
        """Показать статус задачи"""
        status = self.cross_verifier.get_task_status(task_id)
        
        if "error" in status:
            print(f"❌ {status['error']}")
            return
        
        print(f"\n📊 Статус задачи: {task_id}")
        print(f"📝 Описание: {status['description']}")
        print(f"🔄 Статус: {status['status']}")
        print(f"🔢 Итераций: {status['iteration_count']}")
        print(f"📅 Создана: {status['created_at']}")
        
        if status.get('cross_report_path'):
            print(f"📄 Отчет: {status['cross_report_path']}")
        
        print(f"\n🤖 AI системы:")
        for ai_system, session_info in status['chat_sessions'].items():
            status_emoji = "✅" if session_info['status'] == "responded" else "❌"
            print(f"  {status_emoji} {ai_system}: {session_info['status']} "
                  f"(ответов: {session_info['responses_count']}, "
                  f"chat: {session_info['chat_id']})")
    
    def list_tasks(self):
        """Список всех задач"""
        tasks = self.cross_verifier.list_active_tasks()
        
        if not tasks:
            print("📋 Активных задач нет")
            return
        
        print(f"📋 Активные задачи ({len(tasks)}):")
        print("=" * 80)
        
        for task in tasks:
            status_emoji = {
                "created": "🆕",
                "in_progress": "🔄", 
                "feedback_received": "💬",
                "completed": "✅",
                "error": "❌"
            }.get(task['status'], "❓")
            
            print(f"{status_emoji} {task['task_id']}")
            print(f"   📝 {task['description']}")
            print(f"   🔄 {task['status']} (итераций: {task['iteration_count']})")
            print(f"   📅 {task['created_at']}")
            print()
    
    async def send_feedback(self, task_id: str):
        """Отправить обратную связь по задаче"""
        print(f"💬 Отправка feedback для задачи: {task_id}")
        
        try:
            feedback = await self.cross_verifier.send_cross_report_for_feedback(task_id)
            
            print("✅ Feedback получен от всех AI систем!")
            
            for ai_system, response in feedback.items():
                print(f"\n🤖 {ai_system}:")
                print(f"   📝 {response[:200]}{'...' if len(response) > 200 else ''}")
            
            # Обновляем отчет
            report_path = await self.cross_verifier.generate_cross_report(task_id)
            print(f"\n📄 Обновленный отчет: {report_path}")
            
        except Exception as e:
            print(f"❌ Ошибка при отправке feedback: {e}")


def main():
    """Основная функция CLI"""
    parser = argparse.ArgumentParser(
        description="Автоматизированная кросс-верификация с тремя AI системами",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  # Запуск новой кросс-верификации
  python ai_agents/cli_cross_verification.py start "Стратегия скальпинга" "Разработай стратегию скальпинга для BTC с использованием RSI и MACD"
  
  # Просмотр статуса задачи  
  python ai_agents/cli_cross_verification.py status cross_verification_20250713_150000
  
  # Список всех задач
  python ai_agents/cli_cross_verification.py list
  
  # Отправка feedback
  python ai_agents/cli_cross_verification.py feedback cross_verification_20250713_150000
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Доступные команды')
    
    # Команда start
    start_parser = subparsers.add_parser('start', help='Запуск новой кросс-верификации')
    start_parser.add_argument('description', help='Описание задачи')
    start_parser.add_argument('task_content', help='Содержание задачи для AI')
    start_parser.add_argument('--max-iterations', type=int, default=5, 
                             help='Максимальное количество итераций (по умолчанию: 5)')
    
    # Команда status
    status_parser = subparsers.add_parser('status', help='Показать статус задачи')
    status_parser.add_argument('task_id', help='ID задачи')
    
    # Команда list
    list_parser = subparsers.add_parser('list', help='Список всех задач')
    
    # Команда feedback
    feedback_parser = subparsers.add_parser('feedback', help='Отправить feedback по задаче')
    feedback_parser.add_argument('task_id', help='ID задачи')
    
    # Команда interactive
    interactive_parser = subparsers.add_parser('interactive', help='Интерактивный режим')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Создаем CLI
    cli = CrossVerificationCLI()
    
    # Выполняем команды
    if args.command == 'start':
        asyncio.run(cli.start_verification(
            args.description, 
            args.task_content, 
            args.max_iterations
        ))
    
    elif args.command == 'status':
        asyncio.run(cli.show_task_status(args.task_id))
    
    elif args.command == 'list':
        cli.list_tasks()
    
    elif args.command == 'feedback':
        asyncio.run(cli.send_feedback(args.task_id))
    
    elif args.command == 'interactive':
        asyncio.run(interactive_mode(cli))


async def interactive_mode(cli: CrossVerificationCLI):
    """Интерактивный режим"""
    print("🤖 Интерактивный режим кросс-верификации")
    print("Введите 'help' для справки, 'exit' для выхода")
    print("=" * 50)
    
    while True:
        try:
            command = input("\n> ").strip()
            
            if command.lower() in ['exit', 'quit', 'q']:
                print("👋 До свидания!")
                break
            
            elif command.lower() in ['help', 'h']:
                print("""
Доступные команды:
  start <описание> <содержание>  - Запуск новой кросс-верификации
  status <task_id>              - Статус задачи  
  list                          - Список всех задач
  feedback <task_id>            - Отправить feedback
  help                          - Эта справка
  exit                          - Выход
                """)
            
            elif command.lower() == 'list':
                cli.list_tasks()
            
            elif command.startswith('status '):
                task_id = command.split(' ', 1)[1]
                await cli.show_task_status(task_id)
            
            elif command.startswith('feedback '):
                task_id = command.split(' ', 1)[1]
                await cli.send_feedback(task_id)
            
            elif command.startswith('start '):
                parts = command.split(' ', 2)
                if len(parts) < 3:
                    print("❌ Использование: start <описание> <содержание>")
                    continue
                
                description = parts[1]
                task_content = parts[2]
                await cli.start_verification(description, task_content)
            
            else:
                print(f"❌ Неизвестная команда: {command}")
                print("Введите 'help' для справки")
        
        except KeyboardInterrupt:
            print("\n👋 До свидания!")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    main()