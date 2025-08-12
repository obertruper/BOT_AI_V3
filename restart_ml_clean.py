#!/usr/bin/env python3
"""
Перезапуск системы с очисткой ML кеша в памяти
"""

import asyncio
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
load_dotenv()


async def main():
    """Перезапуск системы"""
    print("=" * 60)
    print("🔄 ПЕРЕЗАПУСК СИСТЕМЫ С ОБНОВЛЕННОЙ ML МОДЕЛЬЮ")
    print("=" * 60)

    # 1. Останавливаем старые процессы
    print("\n🛑 Останавливаем существующие процессы...")
    os.system("pkill -f 'python.*unified_launcher' 2>/dev/null")
    os.system("pkill -f 'python.*main.py' 2>/dev/null")
    await asyncio.sleep(2)
    print("✅ Процессы остановлены")

    # 2. Запускаем систему заново (кеш в памяти автоматически очистится)
    print("\n🚀 Запускаем систему с ML...")

    # Запускаем в фоне
    process = await asyncio.create_subprocess_shell(
        "source venv/bin/activate && python3 unified_launcher.py --mode=ml > data/logs/startup.log 2>&1 &",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    print("⏳ Ждем запуска системы...")
    await asyncio.sleep(10)

    # 3. Проверяем что система запустилась
    print("\n🔍 Проверяем статус системы...")

    # Проверяем процессы
    check = await asyncio.create_subprocess_shell(
        "ps aux | grep -E 'python.*unified_launcher' | grep -v grep",
        stdout=asyncio.subprocess.PIPE,
    )
    stdout, _ = await check.communicate()

    if stdout:
        print("✅ Система запущена")

        # Показываем последние логи
        print("\n📋 Последние логи:")
        log_file = f"data/logs/bot_trading_{time.strftime('%Y%m%d')}.log"
        os.system(f"tail -20 {log_file} | grep -E 'ML|signal|Signal'")
    else:
        print("❌ Система не запустилась. Проверьте логи:")
        print("  cat data/logs/startup.log")
        return

    # 4. Ждем и проверяем новые сигналы
    print("\n⏳ Ждем генерации новых сигналов (30 сек)...")
    await asyncio.sleep(30)

    # Проверяем новые сигналы в БД
    from database.connections.postgres import AsyncPGPool

    await AsyncPGPool.initialize()

    # Проверяем последние сигналы
    signals = await AsyncPGPool.fetch(
        """
        SELECT symbol, signal_type, confidence, created_at
        FROM signals
        WHERE created_at > NOW() - INTERVAL '1 minute'
        ORDER BY created_at DESC
        LIMIT 10
    """
    )

    if signals:
        print(f"\n✅ Новых сигналов создано: {len(signals)}")

        # Показываем распределение
        type_dist = {}
        for sig in signals:
            sig_type = sig["signal_type"]
            type_dist[sig_type] = type_dist.get(sig_type, 0) + 1

        print("\nРаспределение новых сигналов:")
        for sig_type, count in type_dist.items():
            print(f"  {sig_type}: {count}")

        print("\nПоследние сигналы:")
        for sig in signals[:5]:
            print(
                f"  {sig['symbol']}: {sig['signal_type']} (conf: {sig['confidence']:.3f}) - {sig['created_at']}"
            )
    else:
        print("\n⚠️ Новых сигналов пока нет")
        print("Проверьте логи: tail -f data/logs/bot_trading_$(date +%Y%m%d).log")

    await AsyncPGPool.close()

    print("\n" + "=" * 60)
    print("✅ Перезапуск завершен")
    print("\n📊 Команды для мониторинга:")
    print("  # Следить за сигналами:")
    print(
        "  tail -f data/logs/bot_trading_$(date +%Y%m%d).log | grep -E 'signal|Signal'"
    )
    print("\n  # Проверить статус:")
    print("  python3 unified_launcher.py --status")
    print("\n  # Мониторинг ML сигналов:")
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
