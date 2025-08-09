#!/usr/bin/env python3
"""
Скрипт быстрого запуска торговой системы с ML генерацией сигналов
Выполняет все необходимые проверки перед запуском
"""

import asyncio
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.logger import setup_logger

logger = setup_logger("start_trading")


def check_environment():
    """Проверка окружения"""
    logger.info("🔍 Проверка окружения...")

    checks_passed = True

    # 1. Проверка .env файла
    if not Path(".env").exists():
        logger.error("❌ Файл .env не найден!")
        logger.info("   Создайте .env на основе .env.example")
        checks_passed = False
    else:
        logger.info("✅ Файл .env найден")

        # Проверяем ключевые переменные
        required_vars = [
            "PGUSER",
            "PGPASSWORD",
            "PGDATABASE",
            "BYBIT_API_KEY",
            "BYBIT_API_SECRET",
        ]
        missing_vars = []

        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            logger.error(f"❌ Отсутствуют переменные: {', '.join(missing_vars)}")
            checks_passed = False
        else:
            logger.info("✅ Основные переменные окружения установлены")

    # 2. Проверка PostgreSQL
    try:
        result = subprocess.run(
            [
                "psql",
                "-p",
                "5555",
                "-U",
                "obertruper",
                "-d",
                "bot_trading_v3",
                "-c",
                "SELECT 1;",
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PGPASSWORD": os.getenv("PGPASSWORD", "")},
        )

        if result.returncode == 0:
            logger.info("✅ PostgreSQL доступен на порту 5555")
        else:
            logger.error("❌ PostgreSQL недоступен")
            logger.error(f"   {result.stderr}")
            checks_passed = False

    except Exception as e:
        logger.error(f"❌ Ошибка проверки PostgreSQL: {e}")
        checks_passed = False

    # 3. Проверка Python модулей
    try:
        import ccxt
        import numpy
        import pandas
        import torch

        logger.info("✅ Основные Python модули установлены")
    except ImportError as e:
        logger.error(f"❌ Отсутствуют модули: {e}")
        logger.info("   Выполните: pip install -r requirements.txt")
        checks_passed = False

    return checks_passed


async def apply_migrations():
    """Применение миграций БД"""
    logger.info("🔄 Применение миграций БД...")

    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"], capture_output=True, text=True
        )

        if result.returncode == 0:
            logger.info("✅ Миграции применены успешно")
            return True
        else:
            logger.error(f"❌ Ошибка миграций: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"❌ Ошибка при применении миграций: {e}")
        return False


async def check_data_availability():
    """Проверка доступности данных"""
    logger.info("📊 Проверка доступности данных...")

    try:
        # Запускаем скрипт проверки
        result = subprocess.run(
            [sys.executable, "scripts/check_data_availability.py"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            logger.info("✅ Данные доступны для ML")
            return True
        else:
            logger.warning("⚠️ Недостаточно данных для некоторых символов")
            logger.info("💡 Рекомендуется загрузить исторические данные:")
            logger.info("   python scripts/load_historical_data.py")

            # Спрашиваем пользователя
            response = input("\n❓ Продолжить без полных данных? (y/N): ")
            return response.lower() == "y"

    except Exception as e:
        logger.error(f"❌ Ошибка проверки данных: {e}")
        return False


async def start_system():
    """Запуск основной системы"""
    logger.info("\n🚀 ЗАПУСК ТОРГОВОЙ СИСТЕМЫ...")
    logger.info("=" * 50)

    try:
        # Запускаем main.py
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
        )

        # Выводим логи в реальном времени
        for line in iter(process.stdout.readline, ""):
            print(line, end="")

            # Проверяем ключевые сообщения
            if "ML Signal Scheduler запущен" in line:
                logger.info("\n🤖 ML СИСТЕМА АКТИВНА!")
            elif "Система готова к работе" in line:
                logger.info("\n✅ СИСТЕМА ПОЛНОСТЬЮ ЗАПУЩЕНА!")
                logger.info("📊 Мониторинг: http://localhost:8080")
                logger.info("📚 API: http://localhost:8080/api/docs")
            elif "Критическая ошибка" in line:
                logger.error("\n❌ КРИТИЧЕСКАЯ ОШИБКА!")

        process.wait()

    except KeyboardInterrupt:
        logger.info("\n⌨️ Остановка по запросу пользователя...")
        process.terminate()
        process.wait()
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске: {e}")


async def main():
    """Основная функция"""
    logger.info("🎯 BOT_AI_V3 - Запуск торговой системы с ML")
    logger.info(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)

    # 1. Проверка окружения
    if not check_environment():
        logger.error("\n❌ Проверка окружения не пройдена!")
        logger.info("❗ Исправьте ошибки выше и попробуйте снова")
        return

    # 2. Применение миграций
    if not await apply_migrations():
        logger.error("\n❌ Не удалось применить миграции!")
        return

    # 3. Проверка данных
    if not await check_data_availability():
        logger.error("\n❌ Отменено пользователем")
        return

    # 4. Запуск системы
    logger.info("\n✅ Все проверки пройдены!")
    logger.info("🚀 Запускаем торговую систему...\n")

    await start_system()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Завершение работы")
    except Exception as e:
        logger.error(f"\n❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()
