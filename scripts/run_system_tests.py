#!/usr/bin/env python3
"""
Полное тестирование системы BOT_AI_V3
"""

import asyncio
import subprocess
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.logger import setup_logger

logger = setup_logger("system_tests")


async def run_system_tests():
    """Запуск всех тестов системы"""

    logger.info("🧪 Запуск полного тестирования системы BOT_AI_V3...")

    tests = [
        (
            "Проверка конфигурации",
            "python -c 'from core.config.config_manager import ConfigManager; print(\"✅ ConfigManager OK\")'",
        ),
        (
            "Проверка ML модели",
            "python -c 'from ml.logic.patchtst_model import UnifiedPatchTST; print(\"✅ ML Model OK\")'",
        ),
        (
            "Проверка ExchangeFactory",
            "python -c 'from exchanges.factory import ExchangeFactory; print(\"✅ ExchangeFactory OK\")'",
        ),
        (
            "Проверка базы данных",
            "python -c 'from database.connections.postgres import AsyncPGPool; print(\"✅ Database OK\")'",
        ),
        (
            "Проверка TradingEngine",
            "python -c 'from trading.engine import TradingEngine; print(\"✅ TradingEngine OK\")'",
        ),
        (
            "Проверка SystemOrchestrator",
            "python -c 'from core.system.orchestrator import SystemOrchestrator; print(\"✅ SystemOrchestrator OK\")'",
        ),
    ]

    results = []

    for test_name, command in tests:
        try:
            logger.info(f"🔍 {test_name}...")
            result = subprocess.run(command, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"✅ {test_name}: УСПЕХ")
                results.append((test_name, True, result.stdout.strip()))
            else:
                logger.error(f"❌ {test_name}: ОШИБКА")
                logger.error(f"   Ошибка: {result.stderr}")
                results.append((test_name, False, result.stderr.strip()))

        except Exception as e:
            logger.error(f"❌ {test_name}: ИСКЛЮЧЕНИЕ - {e}")
            results.append((test_name, False, str(e)))

    # Вывод результатов
    logger.info("\n" + "=" * 50)
    logger.info("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    logger.info("=" * 50)

    passed = sum(1 for _, success, _ in results if success)
    total = len(results)

    for test_name, success, output in results:
        status = "✅ УСПЕХ" if success else "❌ ОШИБКА"
        logger.info(f"{status} {test_name}")
        if output:
            logger.info(f"   {output}")

    logger.info(f"\n📈 ИТОГО: {passed}/{total} тестов прошли успешно")

    if passed == total:
        logger.info("🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        return True
    else:
        logger.error("⚠️ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛИЛИСЬ!")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_system_tests())
    sys.exit(0 if success else 1)
