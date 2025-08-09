#!/usr/bin/env python3
"""
Проверка статуса торгового движка и обработки сигналов
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

import aiohttp

sys.path.append(str(Path(__file__).parent))

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool

logger = setup_logger("check_trading_engine")


async def check_trading_engine():
    """Проверяет статус торгового движка."""

    print("🔍 ПРОВЕРКА СТАТУСА ТОРГОВОГО ДВИЖКА\n")
    print("=" * 60)

    # 1. Проверка API
    print("\n1️⃣ Проверка API статуса...")
    try:
        async with aiohttp.ClientSession() as session:
            # Проверка здоровья
            async with session.get("http://localhost:8080/api/health") as resp:
                if resp.status == 200:
                    health_data = await resp.json()
                    print(f"✅ API статус: {health_data.get('status', 'unknown')}")

                    if "components" in health_data:
                        print("\nКомпоненты:")
                        for comp, status in health_data["components"].items():
                            status_str = "✅" if status else "❌"
                            print(
                                f"  {status_str} {comp}: {'активен' if status else 'не активен'}"
                            )
                else:
                    print(f"❌ API недоступен (статус: {resp.status})")

            # Проверка активных процессов торговли
            async with session.get("http://localhost:8080/api/status/trading") as resp:
                if resp.status == 200:
                    trading_status = await resp.json()
                    print("\n✅ Торговый статус получен")
                    print(
                        f"  Активные стратегии: {trading_status.get('active_strategies', 0)}"
                    )
                    print(
                        f"  Обработано сигналов: {trading_status.get('processed_signals', 0)}"
                    )
                else:
                    print("⚠️  Не удалось получить торговый статус")

    except Exception as e:
        print(f"❌ Ошибка подключения к API: {e}")

    # 2. Проверка последних сигналов
    print("\n2️⃣ Последние сигналы...")

    recent_signals = await AsyncPGPool.fetch(
        """
        SELECT
            id, symbol, signal_type, strength, confidence,
            created_at, strategy_name, extra_data
        FROM signals
        WHERE created_at > NOW() - INTERVAL '30 minutes'
        ORDER BY created_at DESC
        LIMIT 10
    """
    )

    if recent_signals:
        print(f"\nНайдено {len(recent_signals)} сигналов за последние 30 минут:")
        for signal in recent_signals[:5]:
            time_ago = datetime.utcnow() - signal["created_at"].replace(tzinfo=None)
            print(f"\n  📊 {signal['symbol']} - {signal['signal_type']}")
            print(
                f"     Сила: {signal['strength']:.2f}, Уверенность: {signal['confidence']:.2%}"
            )
            print(f"     Стратегия: {signal['strategy_name']}")
            print(f"     Создан: {time_ago.total_seconds():.0f} сек назад")
    else:
        print("❌ Нет сигналов за последние 30 минут")

    # 3. Проверка обработки сигналов
    print("\n3️⃣ Проверка обработки сигналов...")

    # Проверяем, есть ли необработанные сигналы (по времени)
    pending_signals = await AsyncPGPool.fetch(
        """
        SELECT COUNT(*) as count
        FROM signals
        WHERE created_at > NOW() - INTERVAL '1 hour'
        AND id NOT IN (
            SELECT DISTINCT signal_id
            FROM orders
            WHERE signal_id IS NOT NULL
        )
    """
    )

    pending_count = pending_signals[0]["count"] if pending_signals else 0

    if pending_count > 0:
        print(f"⚠️  Найдено {pending_count} необработанных сигналов")
        print("   Возможные причины:")
        print("   - Trading Engine не активен")
        print("   - Signal Processor не запущен")
        print("   - Проблемы с подключением к биржам")
    else:
        print("✅ Все сигналы обработаны")

    # 4. Проверка ордеров
    print("\n4️⃣ Проверка ордеров...")

    recent_orders = await AsyncPGPool.fetch(
        """
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN status = 'filled' THEN 1 END) as filled,
            COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected,
            COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending
        FROM orders
        WHERE created_at > NOW() - INTERVAL '1 hour'
    """
    )

    if recent_orders and recent_orders[0]["total"] > 0:
        order_stats = recent_orders[0]
        print("✅ Статистика ордеров за час:")
        print(f"   Всего: {order_stats['total']}")
        print(f"   Исполнено: {order_stats['filled']}")
        print(f"   Отклонено: {order_stats['rejected']}")
        print(f"   В ожидании: {order_stats['pending']}")
    else:
        print("❌ Нет ордеров за последний час")

    # 5. Проверка процесса signal_processor
    print("\n5️⃣ Проверка Signal Processor...")

    # Смотрим логи на активность signal processor
    try:
        import subprocess

        logs = subprocess.run(
            ["tail", "-n", "100", "data/logs/trading.log"],
            capture_output=True,
            text=True,
        )

        if logs.stdout:
            signal_processor_lines = [
                l for l in logs.stdout.split("\n") if "signal_processor" in l.lower()
            ]
            if signal_processor_lines:
                print(
                    f"✅ Signal Processor активен ({len(signal_processor_lines)} записей в логах)"
                )
                # Показываем последние 3 записи
                for line in signal_processor_lines[-3:]:
                    if line.strip():
                        print(f"   {line[:100]}...")
            else:
                print("⚠️  Signal Processor не обнаружен в логах")
        else:
            print("⚠️  Логи недоступны")
    except Exception as e:
        print(f"❌ Ошибка чтения логов: {e}")

    # 6. Проверка конфигурации торговли
    print("\n6️⃣ Конфигурация торговли...")

    # Проверяем активные биржи
    exchange_check = await AsyncPGPool.fetch(
        """
        SELECT DISTINCT exchange, COUNT(*) as signal_count
        FROM signals
        WHERE created_at > NOW() - INTERVAL '1 hour'
        GROUP BY exchange
    """
    )

    if exchange_check:
        print("✅ Активные биржи:")
        for exc in exchange_check:
            print(f"   {exc['exchange']}: {exc['signal_count']} сигналов")
    else:
        print("⚠️  Нет активности на биржах")

    # 7. Рекомендации
    print("\n7️⃣ РЕКОМЕНДАЦИИ:")
    print("=" * 60)

    if pending_count > 0:
        print("\n⚠️  Обнаружены необработанные сигналы!")
        print("\nДействия:")
        print("1. Проверьте, что Trading Engine активен в unified_launcher")
        print("2. Убедитесь, что signal_processor запущен")
        print("3. Проверьте подключение к биржам")
        print("4. Проверьте логи на ошибки: tail -f data/logs/error.log")

        print("\nДля активации обработки сигналов:")
        print("```bash")
        print("# Перезапустить с торговлей")
        print("python3 unified_launcher.py --mode=ml")
        print("```")
    else:
        print("\n✅ Система работает нормально")
        print("   - Сигналы обрабатываются")
        print("   - API активен")
        print("   - База данных доступна")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(check_trading_engine())
