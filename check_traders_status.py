#!/usr/bin/env python3
"""
Проверка статуса трейдеров и генерации ML сигналов
"""

import asyncio
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

# Устанавливаем переменные окружения
os.environ["PGPORT"] = "5555"
os.environ["PGUSER"] = "obertruper"
os.environ["PGDATABASE"] = "bot_trading_v3"


async def check_traders():
    """Проверка трейдеров и сигналов"""
    from core.config.config_manager import get_global_config_manager
    from database.connections.postgres import AsyncPGPool

    print(
        f"\n🔍 ПРОВЕРКА ТРЕЙДЕРОВ И ML СИГНАЛОВ - {datetime.now().strftime('%H:%M:%S')}"
    )
    print("=" * 60)

    try:
        pool = await AsyncPGPool.get_pool()
        config_manager = get_global_config_manager()
        config = config_manager.get_config()

        # 1. Проверяем конфигурацию трейдеров
        print("\n1️⃣ КОНФИГУРАЦИЯ ТРЕЙДЕРОВ:")

        traders = config.get("traders", [])
        ml_traders = [t for t in traders if t.get("strategy") == "ml_signal"]

        for trader in ml_traders:
            print(f"\n   🤖 {trader['id']}:")
            print(f"      Enabled: {trader.get('enabled', False)}")
            print(f"      Exchange: {trader.get('exchange', 'N/A')}")
            print(f"      Symbols: {trader.get('symbols', [])[:3]}...")

            strategy_config = trader.get("strategy_config", {})
            print(
                f"      Min confidence: {strategy_config.get('min_confidence', 0.6):.0%}"
            )
            print(
                f"      Signal interval: {strategy_config.get('signal_interval', 60)} сек"
            )

        # 2. Проверяем процессы трейдеров
        print("\n2️⃣ АКТИВНЫЕ ПРОЦЕССЫ:")

        # Проверяем, запущены ли трейдеры
        from core.system.process_manager import ProcessManager

        # Пытаемся получить статус процессов
        try:
            process_manager = ProcessManager()
            processes = process_manager.get_all_statuses()

            ml_processes = {k: v for k, v in processes.items() if "ml" in k.lower()}

            if ml_processes:
                for name, status in ml_processes.items():
                    print(f"   {name}: {status}")
            else:
                print("   ❌ Нет активных ML процессов")
        except Exception as e:
            print(f"   ⚠️ Не удалось получить статус процессов: {e}")

        # 3. Проверяем последние сигналы в БД
        print("\n3️⃣ ПОСЛЕДНИЕ СИГНАЛЫ В БД:")

        # Сигналы за последний час
        signals = await pool.fetch(
            """
            SELECT
                symbol,
                signal_type,
                confidence,
                strength,
                strategy_name,
                created_at
            FROM signals
            WHERE created_at > NOW() - INTERVAL '1 hour'
            ORDER BY created_at DESC
            LIMIT 20
        """
        )

        if signals:
            # Группируем по стратегии
            by_strategy = {}
            for sig in signals:
                strategy = sig["strategy_name"]
                if strategy not in by_strategy:
                    by_strategy[strategy] = []
                by_strategy[strategy].append(sig)

            for strategy, sigs in by_strategy.items():
                print(f"\n   📊 {strategy}: {len(sigs)} сигналов")
                for sig in sigs[:3]:  # Показываем первые 3
                    print(
                        f"      {sig['created_at'].strftime('%H:%M:%S')} - {sig['symbol']}: "
                        f"{sig['signal_type']} ({sig['confidence']:.0%})"
                    )
        else:
            print("   ❌ Нет сигналов за последний час")

        # 4. Проверяем логи ошибок
        print("\n4️⃣ ПОСЛЕДНИЕ ОШИБКИ ML:")

        # Читаем последние строки из логов
        log_file = "logs/core.log"
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                lines = f.readlines()

            # Ищем ML ошибки в последних 100 строках
            ml_errors = []
            for line in lines[-100:]:
                if "ERROR" in line and (
                    "ML" in line or "ml_" in line or "signal" in line
                ):
                    ml_errors.append(line.strip())

            if ml_errors:
                print(f"   Найдено {len(ml_errors)} ошибок:")
                for error in ml_errors[-5:]:  # Последние 5
                    # Обрезаем длинные строки
                    if len(error) > 100:
                        error = error[:97] + "..."
                    print(f"      {error}")
            else:
                print("   ✅ Нет ML ошибок в последних логах")

        # 5. Проверяем планировщик сигналов
        print("\n5️⃣ ПЛАНИРОВЩИК ML СИГНАЛОВ:")

        # Проверяем таблицу jobs если есть
        try:
            jobs = await pool.fetch(
                """
                SELECT name, status, last_run, next_run
                FROM scheduled_jobs
                WHERE name LIKE '%ml%' OR name LIKE '%signal%'
                ORDER BY next_run
                LIMIT 5
            """
            )

            if jobs:
                for job in jobs:
                    print(f"   {job['name']}: {job['status']}")
                    print(f"      Last run: {job['last_run']}")
                    print(f"      Next run: {job['next_run']}")
            else:
                print("   ℹ️ Нет запланированных ML задач")
        except Exception:
            print("   ℹ️ Таблица scheduled_jobs не найдена")

        # 6. Рекомендации
        print("\n6️⃣ РЕКОМЕНДАЦИИ:")

        if not ml_traders:
            print("   ⚠️ Нет настроенных ML трейдеров!")
            print("   💡 Проверьте config/traders.yaml")
        elif not any(t.get("enabled") for t in ml_traders):
            print("   ⚠️ Все ML трейдеры отключены!")
            print("   💡 Установите enabled: true в config/traders.yaml")
        elif not signals:
            print("   ⚠️ ML трейдеры настроены, но сигналы не генерируются")
            print("   💡 Проверьте:")
            print("      - Актуальность данных (должны быть свежие свечи)")
            print("      - Логи ошибок в logs/core.log")
            print("      - Минимальную уверенность (возможно слишком высокая)")
        else:
            print("   ✅ Система работает, сигналы генерируются")

        print("\n" + "=" * 60)

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await AsyncPGPool.close_pool()


if __name__ == "__main__":
    asyncio.run(check_traders())
