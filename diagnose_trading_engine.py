#!/usr/bin/env python3
"""
Диагностика проблем с Trading Engine
"""

import asyncio
import subprocess
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool

logger = setup_logger("diagnose_trading")


async def diagnose_trading_engine():
    """Диагностирует проблемы с торговым движком."""

    print("🔍 ДИАГНОСТИКА TRADING ENGINE\n")
    print("=" * 60)

    issues_found = []

    # 1. Проверка процессов
    print("\n1️⃣ Проверка запущенных процессов...")

    ps_result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
    processes = ps_result.stdout

    critical_processes = {
        "unified_launcher.py": False,
        "main.py": False,
        "web/launcher.py": False,
    }

    for proc in critical_processes:
        if proc in processes:
            critical_processes[proc] = True
            print(f"✅ {proc} запущен")
        else:
            print(f"❌ {proc} НЕ запущен")
            issues_found.append(f"{proc} не запущен")

    # 2. Проверка конфигурации
    print("\n2️⃣ Проверка конфигурации...")

    config_files = ["config/system.yaml", "config/trading.yaml", ".env"]

    for cfg in config_files:
        if Path(cfg).exists():
            print(f"✅ {cfg} существует")
        else:
            print(f"❌ {cfg} НЕ найден")
            issues_found.append(f"Файл конфигурации {cfg} не найден")

    # 3. Проверка логов на ошибки
    print("\n3️⃣ Проверка последних ошибок в логах...")

    log_files = [
        "data/logs/trading.log",
        "data/logs/error.log",
        "data/logs/bot_trading_20250806.log",
    ]

    error_patterns = ["ERROR", "CRITICAL", "Exception", "Failed", "Can't connect"]
    errors_found = []

    for log_file in log_files:
        if Path(log_file).exists():
            try:
                result = subprocess.run(
                    ["tail", "-n", "100", log_file], capture_output=True, text=True
                )

                for line in result.stdout.split("\n"):
                    for pattern in error_patterns:
                        if pattern in line:
                            errors_found.append(line.strip())
                            break
            except:
                pass

    if errors_found:
        print(f"❌ Найдено {len(errors_found)} ошибок:")
        for err in errors_found[-5:]:  # Показываем последние 5
            print(f"   {err[:100]}...")
        issues_found.append(f"Найдено {len(errors_found)} ошибок в логах")
    else:
        print("✅ Критических ошибок не найдено")

    # 4. Проверка инициализации компонентов
    print("\n4️⃣ Проверка компонентов системы...")

    # Проверяем через БД - есть ли активность
    component_checks = {
        "ML Manager": """
            SELECT COUNT(*) as count, MAX(created_at) as last_time
            FROM processed_market_data
            WHERE created_at > NOW() - INTERVAL '15 minutes'
        """,
        "Signal Processor": """
            SELECT COUNT(*) as count, MAX(created_at) as last_time
            FROM signals
            WHERE created_at > NOW() - INTERVAL '15 minutes'
        """,
        "Trading Engine": """
            SELECT COUNT(*) as count, MAX(created_at) as last_time
            FROM orders
            WHERE created_at > NOW() - INTERVAL '1 hour'
        """,
    }

    for component, query in component_checks.items():
        result = await AsyncPGPool.fetchrow(query)
        if result and result["count"] > 0:
            print(f"✅ {component}: активен ({result['count']} записей)")
        else:
            print(f"❌ {component}: НЕ активен")
            issues_found.append(f"{component} не активен")

    # 5. Проверка Signal Processing
    print("\n5️⃣ Проверка обработки сигналов...")

    # Есть ли необработанные сигналы?
    unprocessed = await AsyncPGPool.fetchrow(
        """
        SELECT COUNT(*) as count
        FROM signals s
        WHERE s.created_at > NOW() - INTERVAL '1 hour'
        AND NOT EXISTS (
            SELECT 1 FROM orders o
            WHERE o.strategy_name = s.strategy_name
            AND o.symbol = s.symbol
            AND o.created_at >= s.created_at
            AND o.created_at <= s.created_at + INTERVAL '5 minutes'
        )
    """
    )

    if unprocessed and unprocessed["count"] > 0:
        print(f"❌ {unprocessed['count']} необработанных сигналов")
        issues_found.append(f"{unprocessed['count']} сигналов не обработано")

        # Показываем примеры
        examples = await AsyncPGPool.fetch(
            """
            SELECT symbol, signal_type, strength, confidence, created_at
            FROM signals
            WHERE created_at > NOW() - INTERVAL '1 hour'
            ORDER BY created_at DESC
            LIMIT 3
        """
        )

        if examples:
            print("\n   Примеры необработанных сигналов:")
            for sig in examples:
                print(
                    f"   - {sig['symbol']} {sig['signal_type']} (сила: {sig['strength']:.2f})"
                )
    else:
        print("✅ Все сигналы обработаны")

    # 6. Проверка подключения к биржам
    print("\n6️⃣ Проверка подключения к биржам...")

    # Проверяем .env на наличие ключей
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path) as f:
            env_content = f.read()

        exchanges_with_keys = []
        for exchange in ["BYBIT", "BINANCE", "OKX", "BITGET"]:
            if f"{exchange}_API_KEY" in env_content:
                exchanges_with_keys.append(exchange)

        if exchanges_with_keys:
            print(f"✅ Найдены ключи для: {', '.join(exchanges_with_keys)}")
        else:
            print("❌ API ключи бирж не найдены в .env")
            issues_found.append("API ключи бирж не настроены")

    # 7. ДИАГНОЗ И РЕШЕНИЕ
    print("\n7️⃣ ДИАГНОЗ:")
    print("=" * 60)

    if not issues_found:
        print("✅ Критических проблем не обнаружено")
    else:
        print(f"❌ Обнаружено проблем: {len(issues_found)}")
        for i, issue in enumerate(issues_found, 1):
            print(f"   {i}. {issue}")

    # Основная проблема
    if "Trading Engine не активен" in str(issues_found):
        print("\n🔧 ОСНОВНАЯ ПРОБЛЕМА: Trading Engine не обрабатывает сигналы")
        print("\n📋 РЕШЕНИЕ:")
        print("1. Перезапустите систему с правильными параметрами:")
        print("   ```bash")
        print("   # Остановить все процессы")
        print("   pkill -f unified_launcher")
        print("   pkill -f main.py")
        print("   ")
        print("   # Запустить с ML и торговлей")
        print("   python3 unified_launcher.py --mode=ml")
        print("   ```")
        print("\n2. Проверьте инициализацию через API:")
        print("   ```bash")
        print("   curl http://localhost:8080/api/health")
        print("   ```")
        print("\n3. Убедитесь, что все компоненты активны")

    return issues_found


if __name__ == "__main__":
    issues = asyncio.run(diagnose_trading_engine())

    # Возвращаем код ошибки если есть проблемы
    sys.exit(0 if not issues else 1)
