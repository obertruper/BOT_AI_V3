#!/usr/bin/env python3
"""
Проверка баланса и процессов системы
"""

import asyncio
import os

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool

logger = setup_logger("balance_checker")


async def check_trading_balance():
    """Проверка торгового баланса"""

    logger.info("\n" + "=" * 60)
    logger.info("💰 ПРОВЕРКА БАЛАНСА")
    logger.info("=" * 60)

    # Проверяем конфигурацию
    import yaml

    with open("config/trading.yaml") as f:
        config = yaml.safe_load(f)

    logger.info("📊 Конфигурация торговли:")
    logger.info(f"  • Фиксированный баланс: ${config['balance']['fixed_balance']}")
    logger.info(f"  • Использовать фиксированный: {config['balance']['use_fixed_balance']}")
    logger.info(f"  • Размер позиции: ${config['position_sizing']['fixed_position_size_usd']}")
    logger.info(f"  • Риск на сделку: {config['risk_management']['max_risk_per_trade']:.1%}")

    # Проверяем переменные окружения
    bybit_key = os.getenv("BYBIT_API_KEY")
    if bybit_key:
        logger.info(f"\n✅ API ключ Bybit установлен (длина: {len(bybit_key)})")
    else:
        logger.warning("⚠️ API ключ Bybit не найден в .env")

    # Проверяем записи о балансе в БД
    query = """
        SELECT
            exchange,
            symbol,
            total_balance,
            available_balance,
            locked_balance,
            updated_at
        FROM account_balances
        WHERE updated_at > NOW() - INTERVAL '24 hours'
        ORDER BY updated_at DESC
    """

    rows = await AsyncPGPool.fetch(query)

    if rows:
        logger.info("\n📊 Балансы в БД (последние 24ч):")
        for row in rows[:5]:
            logger.info(f"  • {row['exchange']} {row['symbol']}: ${row['total_balance']:.2f}")
            logger.info(
                f"    Доступно: ${row['available_balance']:.2f}, Заблокировано: ${row['locked_balance']:.2f}"
            )
    else:
        logger.info("\n📊 Используется фиксированный баланс (нет записей в БД)")
        logger.info(f"  • USDT: ${config['balance']['fixed_balance']}")

    return config["balance"]["fixed_balance"]


async def check_ml_processes():
    """Проверка ML процессов"""

    logger.info("\n" + "=" * 60)
    logger.info("🔧 ПРОВЕРКА ПРОЦЕССОВ")
    logger.info("=" * 60)

    # Проверяем активные процессы
    import subprocess

    result = subprocess.run(["ps", "aux"], capture_output=True, text=True)

    processes = {"unified_launcher": 0, "ml_manager": 0, "trading_engine": 0, "signal_scheduler": 0}

    for line in result.stdout.split("\n"):
        for proc in processes:
            if proc in line and "grep" not in line:
                processes[proc] += 1

    logger.info("📊 Активные процессы:")
    for proc, count in processes.items():
        if count > 0:
            status = "✅" if count == 1 else "⚠️"
            logger.info(f"  {status} {proc}: {count} процесс(ов)")

    # Проверяем потоки в БД
    query = """
        SELECT
            COUNT(DISTINCT pid) as unique_pids,
            COUNT(*) as total_connections
        FROM pg_stat_activity
        WHERE datname = 'bot_trading_v3'
          AND state = 'active'
    """

    result = await AsyncPGPool.fetch(query)
    if result:
        row = result[0]
        logger.info("\n📊 Подключения к БД:")
        logger.info(f"  • Уникальных PID: {row['unique_pids']}")
        logger.info(f"  • Всего подключений: {row['total_connections']}")

    return processes


async def check_signal_generation():
    """Проверка генерации сигналов"""

    logger.info("\n" + "=" * 60)
    logger.info("📡 ПРОВЕРКА ГЕНЕРАЦИИ СИГНАЛОВ")
    logger.info("=" * 60)

    # Проверяем частоту сигналов
    query = """
        SELECT
            DATE_TRUNC('minute', created_at) as minute,
            COUNT(*) as signal_count,
            COUNT(DISTINCT symbol) as unique_symbols
        FROM signals
        WHERE created_at > NOW() - INTERVAL '10 minutes'
        GROUP BY minute
        ORDER BY minute DESC
    """

    rows = await AsyncPGPool.fetch(query)

    if rows:
        logger.info("📊 Сигналы за последние 10 минут:")
        for row in rows[:5]:
            logger.info(
                f"  • {row['minute'].strftime('%H:%M')}: {row['signal_count']} сигналов, {row['unique_symbols']} символов"
            )

        total = sum(row["signal_count"] for row in rows)
        avg = total / len(rows) if rows else 0
        logger.info(f"\n  Среднее: {avg:.1f} сигналов/минуту")

        if avg > 50:
            logger.warning("⚠️ Слишком много сигналов - возможны дубликаты процессов!")
        elif avg > 20:
            logger.info("✅ Нормальная частота генерации")
        else:
            logger.info("📊 Умеренная частота генерации")
    else:
        logger.warning("⚠️ Нет сигналов за последние 10 минут")


async def check_order_creation():
    """Проверка создания ордеров"""

    logger.info("\n" + "=" * 60)
    logger.info("📋 ПРОВЕРКА СОЗДАНИЯ ОРДЕРОВ")
    logger.info("=" * 60)

    # Проверяем последние попытки создания ордеров
    query = """
        SELECT
            symbol,
            side,
            status,
            error_message,
            created_at
        FROM orders
        WHERE created_at > NOW() - INTERVAL '1 hour'
        ORDER BY created_at DESC
        LIMIT 20
    """

    rows = await AsyncPGPool.fetch(query)

    if rows:
        success = sum(1 for r in rows if r["status"] in ["filled", "open", "partially_filled"])
        failed = sum(1 for r in rows if r["status"] in ["cancelled", "rejected", "failed"])

        logger.info("📊 Статистика ордеров (последний час):")
        logger.info(f"  • Успешных: {success}")
        logger.info(f"  • Неудачных: {failed}")

        # Показываем ошибки
        errors = [r for r in rows if r["error_message"]]
        if errors:
            logger.warning("\n⚠️ Последние ошибки:")
            for err in errors[:3]:
                logger.warning(f"  • {err['symbol']}: {err['error_message']}")
    else:
        logger.info("📊 Нет ордеров за последний час")
        logger.info("  Возможные причины:")
        logger.info("  • Недостаточно баланса")
        logger.info("  • Нет подходящих сигналов")
        logger.info("  • Проблемы с API подключением")


async def main():
    """Основная функция"""

    logger.info("\n" + "=" * 80)
    logger.info("🔍 ПРОВЕРКА СИСТЕМЫ ТОРГОВЛИ")
    logger.info("=" * 80)

    # 1. Проверка баланса
    balance = await check_trading_balance()

    # 2. Проверка процессов
    processes = await check_ml_processes()

    # 3. Проверка генерации сигналов
    await check_signal_generation()

    # 4. Проверка создания ордеров
    await check_order_creation()

    # Итоги
    logger.info("\n" + "=" * 80)
    logger.info("📊 ИТОГИ")
    logger.info("=" * 80)

    if balance >= 100:
        logger.info(f"✅ Баланс достаточен: ${balance}")
    else:
        logger.warning(f"⚠️ Низкий баланс: ${balance}")

    if processes["unified_launcher"] == 2:  # core + api
        logger.info("✅ Процессы работают корректно (не дублируются)")
    else:
        logger.warning(f"⚠️ Проблема с процессами: {processes['unified_launcher']} launcher'ов")

    logger.info("\n💡 Рекомендации:")
    logger.info("  1. Убедитесь что API ключи корректны")
    logger.info("  2. Проверьте логи на ошибки подключения")
    logger.info("  3. Используйте фиксированный баланс $500 для тестов")


if __name__ == "__main__":
    asyncio.run(main())
