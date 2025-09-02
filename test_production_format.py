#!/usr/bin/env python3
"""
Тест исправления формата в продакшне
"""
import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from core.logger import setup_logger

logger = setup_logger(__name__)

async def main():
    """Запуск системы на 30 секунд для проверки исправления"""
    try:
        logger.info("🚀 Запуск системы для проверки исправления формата ML...")
        
        # Запускаем unified_launcher на короткое время
        from unified_launcher import main as launcher_main
        
        # Создаем задачу запуска системы
        system_task = asyncio.create_task(launcher_main())
        
        # Ждем 30 секунд
        await asyncio.sleep(30)
        
        # Останавливаем систему
        system_task.cancel()
        
        try:
            await system_task
        except asyncio.CancelledError:
            logger.info("✅ Система остановлена")
            
        logger.info("✅ Тест завершен - проверьте логи на предупреждения!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка в тесте: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("🎉 Тест завершен успешно - проверьте логи!")
    else:
        print("⚠️ Были ошибки при тестировании")