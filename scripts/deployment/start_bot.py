#!/usr/bin/env python3
"""
Простой скрипт для запуска бота с минимальным выводом
"""

import asyncio
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# Устанавливаем переменные окружения
os.environ["PGPORT"] = "5555"
os.environ["PGUSER"] = "obertruper"
os.environ["PGDATABASE"] = "bot_trading_v3"


async def start_bot():
    """Запуск торгового бота"""
    print(f"\n🚀 ЗАПУСК ТОРГОВОГО БОТА - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)

    from core.config.config_manager import get_global_config_manager
    from core.system.orchestrator import SystemOrchestrator
    from database.connections.postgres import AsyncPGPool

    try:
        # Инициализация
        config_manager = get_global_config_manager()
        print("✅ Конфигурация загружена")

        # Проверка API ключей
        api_key = os.getenv("BYBIT_API_KEY")
        api_secret = os.getenv("BYBIT_API_SECRET")

        if not api_key or not api_secret:
            print("❌ ОШИБКА: Не найдены API ключи Bybit в .env файле!")
            return

        print(f"✅ API ключи загружены (ключ: {api_key[:10]}...)")

        # Проверка подключения к БД
        pool = await AsyncPGPool.get_pool()
        result = await pool.fetchval(
            "SELECT COUNT(*) FROM raw_market_data WHERE symbol='BTCUSDT' AND interval_minutes=15"
        )
        print(f"✅ База данных подключена (BTCUSDT: {result} свечей)")

        # Создание оркестратора
        orchestrator = SystemOrchestrator(config_manager)
        print("✅ Оркестратор создан")

        # Инициализация системы
        print("\n🔧 Инициализация компонентов...")
        await orchestrator.initialize()
        print("✅ Все компоненты инициализированы")

        # Запуск системы
        print("\n🎯 Запуск торговли...")
        await orchestrator.start()
        print("✅ Система запущена")

        # Получение статуса
        status = await orchestrator.get_system_status()
        print("\n📊 СТАТУС СИСТЕМЫ:")
        print(f"   - Запущен: {status['system']['is_running']}")
        print(
            f"   - Здоровье: {'✅ OK' if status['health']['is_healthy'] else '❌ ПРОБЛЕМЫ'}"
        )
        print(f"   - Активные компоненты: {len(status['components']['active'])}")
        print(f"   - Активные трейдеры: {status['traders']['active']}")

        if not status["health"]["is_healthy"]:
            print("\n⚠️ Проблемы:")
            for issue in status["health"]["issues"]:
                print(f"   - {issue}")

        print("\n✅ БОТ УСПЕШНО ЗАПУЩЕН И РАБОТАЕТ!")
        print("   Нажмите Ctrl+C для остановки")
        print("=" * 60)

        # Основной цикл с периодическим выводом статуса
        while True:
            await asyncio.sleep(60)  # Каждую минуту

            # Краткий статус
            status = await orchestrator.get_system_status()
            trades = status["traders"]["total_trades"]

            # Проверяем последние ML сигналы
            ml_status = await pool.fetchrow(
                """
                SELECT COUNT(*) as signals, MAX(created_at) as latest
                FROM signals
                WHERE created_at > NOW() - INTERVAL '5 minutes'
            """
            )

            print(
                f"\n[{datetime.now().strftime('%H:%M:%S')}] "
                f"Трейдеры: {status['traders']['active']} | "
                f"Сделок: {trades} | "
                f"ML сигналов (5мин): {ml_status['signals'] if ml_status else 0}"
            )

    except KeyboardInterrupt:
        print("\n\n⏹️ Получен сигнал остановки...")

    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Останавливаем систему
        print("\n🛑 Остановка системы...")
        if "orchestrator" in locals():
            await orchestrator.shutdown()

        # Закрываем соединения
        await AsyncPGPool.close_pool()

        print("✅ Система остановлена")


if __name__ == "__main__":
    asyncio.run(start_bot())
