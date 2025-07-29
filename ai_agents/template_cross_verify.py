#!/usr/bin/env python3
"""
Кросс-верификация с использованием готовых шаблонов workflow
Упрощает запуск типовых задач

Использование:
    python ai_agents/template_cross_verify.py scalping_strategy "Детали стратегии скальпинга"
    python ai_agents/template_cross_verify.py hft_architecture "Анализ архитектуры для HFT"
    python ai_agents/template_cross_verify.py --list  # Показать все шаблоны

Автор: BOT Trading v3 Team
"""

import asyncio
import sys
import argparse
from pathlib import Path
from typing import Optional

# Добавляем путь к проекту
sys.path.append(str(Path(__file__).parent.parent))

from ai_agents.automated_cross_verification import AutomatedCrossVerification
from ai_agents.workflow_templates import WorkflowTemplates, QUICK_WORKFLOWS, TaskType


class TemplateCrossVerification:
    """Кросс-верификация с шаблонами"""
    
    def __init__(self):
        self.cross_verifier = AutomatedCrossVerification()
        self.templates = WorkflowTemplates.get_all_templates()
    
    async def run_template_verification(
        self, 
        template_name: str, 
        task_content: str,
        custom_params: Optional[dict] = None
    ):
        """Запуск кросс-верификации с шаблоном"""
        
        if template_name not in QUICK_WORKFLOWS:
            print(f"❌ Шаблон '{template_name}' не найден!")
            print("📋 Доступные шаблоны:")
            self.list_templates()
            return None, None
        
        workflow_config = QUICK_WORKFLOWS[template_name]
        template_type = workflow_config["template_type"]
        template = self.templates[template_type]
        
        print(f"🚀 Запуск кросс-верификации с шаблоном: {template_name}")
        print(f"📋 Описание: {workflow_config['description']}")
        print(f"🎯 Тип задачи: {template_type.value}")
        print("=" * 60)
        
        # Объединяем параметры
        params = workflow_config.get("params", {})
        if custom_params:
            params.update(custom_params)
        
        params["task_description"] = workflow_config["description"]
        params["task_content"] = task_content
        
        # Форматируем промпт
        formatted_prompt = WorkflowTemplates.format_prompt(template, **params)
        
        try:
            # Запускаем кросс-верификацию
            task_id, report_path = await self.cross_verifier.run_full_workflow(
                description=f"{workflow_config['description']} ({template_name})",
                task_content=formatted_prompt,
                max_iterations=template.max_iterations
            )
            
            print("\n" + "="*60)
            print("✅ КРОСС-ВЕРИФИКАЦИЯ ЗАВЕРШЕНА!")
            print("="*60)
            print(f"📋 Task ID: {task_id}")
            print(f"📄 Отчет: {report_path}")
            
            # Показываем результаты
            status = self.cross_verifier.get_task_status(task_id)
            print(f"🔢 Итераций: {status['iteration_count']}")
            
            successful_ai = sum(1 for session in status['chat_sessions'].values() 
                               if session['status'] == 'responded')
            total_ai = len(status['chat_sessions'])
            print(f"🤖 Успешных AI: {successful_ai}/{total_ai}")
            
            # Показываем follow-up вопросы
            if template.follow_up_questions:
                print(f"\n💡 Рекомендуемые follow-up вопросы:")
                for i, question in enumerate(template.follow_up_questions, 1):
                    print(f"   {i}. {question}")
            
            print(f"\n📖 Читайте детальный анализ в: {report_path}")
            
            return task_id, report_path
            
        except Exception as e:
            print(f"\n❌ Ошибка при кросс-верификации: {e}")
            return None, None
    
    def list_templates(self):
        """Показать все доступные шаблоны"""
        print("\n📋 Доступные шаблоны workflow:")
        print("=" * 60)
        
        for template_name, config in QUICK_WORKFLOWS.items():
            template_type = config["template_type"]
            template = self.templates[template_type]
            
            print(f"🔧 {template_name}")
            print(f"   📝 {config['description']}")
            print(f"   🎯 Тип: {template_type.value}")
            print(f"   🔄 Итераций: {template.max_iterations}")
            print(f"   🤖 AI системы: {', '.join(template.ai_systems)}")
            
            # Показываем параметры
            params = config.get("params", {})
            if params:
                print(f"   ⚙️ Параметры: {', '.join(f'{k}={v}' for k, v in params.items())}")
            
            print()
    
    def show_template_details(self, template_name: str):
        """Показать детали конкретного шаблона"""
        if template_name not in QUICK_WORKFLOWS:
            print(f"❌ Шаблон '{template_name}' не найден!")
            return
        
        workflow_config = QUICK_WORKFLOWS[template_name]
        template_type = workflow_config["template_type"]
        template = self.templates[template_type]
        
        print(f"\n📋 Детали шаблона: {template_name}")
        print("=" * 60)
        print(f"🎯 Описание: {workflow_config['description']}")
        print(f"📊 Тип задачи: {template_type.value}")
        print(f"🔄 Максимум итераций: {template.max_iterations}")
        print(f"🤖 AI системы: {', '.join(template.ai_systems)}")
        
        # Параметры
        params = workflow_config.get("params", {})
        if params:
            print(f"\n⚙️ Предустановленные параметры:")
            for key, value in params.items():
                print(f"   • {key}: {value}")
        
        # Follow-up вопросы
        if template.follow_up_questions:
            print(f"\n💡 Рекомендуемые follow-up вопросы:")
            for i, question in enumerate(template.follow_up_questions, 1):
                print(f"   {i}. {question}")
        
        # Примеры использования
        print(f"\n📖 Пример использования:")
        print(f"   python ai_agents/template_cross_verify.py {template_name} \"Ваша задача здесь\"")


async def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(
        description="Кросс-верификация с готовыми шаблонами workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  # Стратегия скальпинга
  python ai_agents/template_cross_verify.py scalping_strategy "Разработай стратегию скальпинга BTC с RSI и MACD"
  
  # Арбитражная стратегия  
  python ai_agents/template_cross_verify.py arbitrage_strategy "Арбитраж между Binance и Bybit"
  
  # HFT архитектура
  python ai_agents/template_cross_verify.py hft_architecture "Архитектура для латентности <1мс"
  
  # Система рисков
  python ai_agents/template_cross_verify.py risk_system "Comprehensive риск-менеджмент для портфеля $100K"
  
  # Оптимизация производительности
  python ai_agents/template_cross_verify.py trading_engine_optimization "Ускорить обработку ордеров в 10 раз"
  
  # Показать все шаблоны
  python ai_agents/template_cross_verify.py --list
  
  # Детали конкретного шаблона
  python ai_agents/template_cross_verify.py --details scalping_strategy
        """
    )
    
    parser.add_argument('template_name', nargs='?', help='Название шаблона')
    parser.add_argument('task_content', nargs='?', help='Содержание задачи')
    parser.add_argument('--list', action='store_true', help='Показать все шаблоны')
    parser.add_argument('--details', metavar='TEMPLATE', help='Показать детали шаблона')
    
    args = parser.parse_args()
    
    # Создаем систему
    template_verifier = TemplateCrossVerification()
    
    if args.list:
        template_verifier.list_templates()
        return
    
    if args.details:
        template_verifier.show_template_details(args.details)
        return
    
    if not args.template_name or not args.task_content:
        print("❌ Необходимо указать название шаблона и содержание задачи!")
        print("\nИспользование:")
        print("   python ai_agents/template_cross_verify.py <template_name> <task_content>")
        print("\nДля просмотра шаблонов:")
        print("   python ai_agents/template_cross_verify.py --list")
        sys.exit(1)
    
    # Запускаем кросс-верификацию с шаблоном
    await template_verifier.run_template_verification(
        args.template_name, 
        args.task_content
    )


if __name__ == "__main__":
    asyncio.run(main())