#!/usr/bin/env python3
"""
Перезапуск ML модели с очисткой кеша и обновленными порогами
"""

import asyncio
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Добавляем корневую директорию в путь Python
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()


def kill_existing_processes():
    """Убиваем существующие процессы бота"""
    print("🔍 Ищем запущенные процессы...")

    # Убиваем процессы
    os.system("pkill -f 'python.*unified_launcher' 2>/dev/null")
    os.system("pkill -f 'python.*main.py' 2>/dev/null")
    time.sleep(2)

    print("✅ Существующие процессы остановлены")


def clear_ml_cache():
    """Очищаем кеш ML модели"""
    print("🧹 Очищаем кеш ML модели...")

    # Удаляем файлы кеша если есть
    cache_dirs = ["data/cache", "data/ml_cache", "ml/cache", ".cache"]

    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir):
            os.system(f"rm -rf {cache_dir}")
            print(f"  Удален: {cache_dir}")

    # Очищаем Redis кеш если используется
    try:
        import redis

        r = redis.Redis(host="localhost", port=6379, db=0)
        r.flushdb()
        print("  Redis кеш очищен")
    except:
        pass

    print("✅ Кеш очищен")


def verify_ml_thresholds():
    """Проверяем что пороги ML модели обновлены"""
    print("🔍 Проверяем пороги ML модели...")

    ml_manager_path = "ml/ml_manager.py"
    with open(ml_manager_path, "r") as f:
        content = f.read()

    # Проверяем новые пороги
    if "weighted_direction < 0.8" in content and "weighted_direction < 1.2" in content:
        print("✅ Пороги ML модели обновлены корректно:")
        print("  LONG: < 0.8")
        print("  SHORT: 0.8 - 1.2")
        print("  NEUTRAL: >= 1.2")
        return True
    else:
        print("❌ Пороги ML модели не обновлены!")
        return False


async def start_system():
    """Запускаем систему с ML"""
    print("\n🚀 Запускаем систему с обновленной ML моделью...")

    # Запускаем через unified_launcher с режимом ML
    cmd = "python3 unified_launcher.py --mode=ml"

    print(f"Выполняем: {cmd}")
    process = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    # Ждем немного и проверяем статус
    await asyncio.sleep(5)

    if process.returncode is None:
        print("✅ Система запущена с ML режимом")

        # Читаем первые логи
        print("\n📋 Первые логи:")
        try:
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5.0)
            if stdout:
                print(stdout.decode()[:1000])
        except asyncio.TimeoutError:
            # Процесс все еще работает - это хорошо
            print("  Система работает...")

            # Проверяем логи
            log_file = f"data/logs/bot_trading_{time.strftime('%Y%m%d')}.log"
            if os.path.exists(log_file):
                os.system(f"tail -20 {log_file}")
    else:
        print("❌ Ошибка запуска системы")
        stderr = await process.stderr.read()
        print(stderr.decode())


async def monitor_signals():
    """Мониторим новые сигналы"""
    print("\n📊 Мониторинг новых ML сигналов...")

    from database.connections.postgres import AsyncPGPool

    await AsyncPGPool.initialize()

    # Запоминаем текущее количество
    initial_count = await AsyncPGPool.fetchval(
        "SELECT COUNT(*) FROM signals WHERE DATE(created_at) = CURRENT_DATE"
    )

    print(f"Сигналов за сегодня до перезапуска: {initial_count}")

    # Ждем 30 секунд
    await asyncio.sleep(30)

    # Проверяем новые сигналы
    new_count = await AsyncPGPool.fetchval(
        "SELECT COUNT(*) FROM signals WHERE DATE(created_at) = CURRENT_DATE"
    )

    if new_count > initial_count:
        print(f"✅ Новых сигналов создано: {new_count - initial_count}")

        # Проверяем распределение типов
        type_dist = await AsyncPGPool.fetch(
            """
            SELECT signal_type, COUNT(*) as count
            FROM signals
            WHERE created_at > NOW() - INTERVAL '1 minute'
            GROUP BY signal_type
        """
        )

        print("\nРаспределение новых сигналов:")
        for row in type_dist:
            print(f"  {row['signal_type']}: {row['count']}")

        # Показываем последние сигналы
        latest = await AsyncPGPool.fetch(
            """
            SELECT symbol, signal_type, confidence, suggested_price
            FROM signals
            ORDER BY created_at DESC
            LIMIT 5
        """
        )

        print("\nПоследние 5 сигналов:")
        for sig in latest:
            print(
                f"  {sig['symbol']}: {sig['signal_type']} (conf: {sig['confidence']:.3f}) @ ${sig['suggested_price']}"
            )
    else:
        print("⚠️ Новых сигналов пока нет")

    await AsyncPGPool.close()


async def main():
    """Основная функция"""
    print("=" * 60)
    print("🔄 ПЕРЕЗАПУСК ML МОДЕЛИ С ОБНОВЛЕННЫМИ ПОРОГАМИ")
    print("=" * 60)

    # 1. Останавливаем существующие процессы
    kill_existing_processes()

    # 2. Очищаем кеш
    clear_ml_cache()

    # 3. Проверяем пороги
    if not verify_ml_thresholds():
        print("❌ Остановлено: пороги не обновлены")
        return

    # 4. Запускаем систему
    await start_system()

    # 5. Мониторим сигналы
    await monitor_signals()

    print("\n" + "=" * 60)
    print("✅ Перезапуск завершен")
    print("📋 Для мониторинга используйте:")
    print("  tail -f data/logs/bot_trading_$(date +%Y%m%d).log | grep -E 'ML|signal'")
    print("  python3 scripts/monitor_ml_signals.py")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Прервано пользователем")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()
