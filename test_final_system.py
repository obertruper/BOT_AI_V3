#!/usr/bin/env python3
"""
Финальный тест системы BOT_AI_V3
"""

import asyncio
import os
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


async def test_system():
    """Проверка всех компонентов системы"""

    print("=" * 60)
    print("🔍 ФИНАЛЬНАЯ ПРОВЕРКА СИСТЕМЫ BOT_AI_V3")
    print("=" * 60)

    # 1. Проверка БД
    print("\n📊 1. База данных (PostgreSQL:5555)")
    try:
        from database.connections.postgres import AsyncPGPool

        result = await AsyncPGPool.fetch("SELECT version()")
        print("   ✅ Подключение успешно")

        # Проверка данных
        data_check = await AsyncPGPool.fetch(
            "SELECT COUNT(*) as cnt FROM raw_market_data WHERE timestamp > EXTRACT(EPOCH FROM NOW() - INTERVAL '1 hour') * 1000"
        )
        fresh_data = data_check[0]["cnt"] > 0
        print(
            f"   {'✅' if fresh_data else '⚠️'} Свежие данные: {'Да' if fresh_data else 'Нет'} ({data_check[0]['cnt']} записей)"
        )

    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

    # 2. Проверка Bybit API
    print("\n🏦 2. Bybit API")
    try:
        from exchanges.factory import ExchangeFactory

        factory = ExchangeFactory()

        api_key = os.getenv("BYBIT_API_KEY")
        api_secret = os.getenv("BYBIT_API_SECRET")

        if api_key and api_secret:
            client = factory.create_client(
                exchange_type="bybit",
                api_key=api_key,
                api_secret=api_secret,
                sandbox=False,
            )

            await client.connect()

            # Получаем баланс
            balance = await client.get_balance()
            if balance:
                print("   ✅ Подключение успешно")
                usdt_balance = next((b for b in balance if b.currency == "USDT"), None)
                if usdt_balance:
                    print(f"   💰 Баланс USDT: {usdt_balance.free:.2f}")
            else:
                print("   ⚠️ Не удалось получить баланс")

            await client.disconnect()
        else:
            print("   ❌ API ключи не найдены")

    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

    # 3. Проверка ML системы
    print("\n🤖 3. ML система")
    try:
        from core.config.config_manager import ConfigManager
        from ml.ml_manager import MLManager

        config_manager = ConfigManager()
        ml_manager = MLManager(config_manager.get_config())

        # Проверяем инициализацию
        await ml_manager.initialize()
        print("   ✅ ML Manager инициализирован")

        # Проверяем модель
        if ml_manager.model:
            print("   ✅ Модель загружена: UnifiedPatchTST")
        else:
            print("   ⚠️ Модель не загружена")

    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

    # 4. Проверка конфигурации
    print("\n⚙️ 4. Конфигурация")
    try:
        from core.config.config_manager import ConfigManager

        config_manager = ConfigManager()
        config = config_manager.get_config()

        # Проверяем критические настройки
        data_management = config.get("data_management", {})
        print(
            f"   ✅ Автообновление данных: {data_management.get('auto_update', False)}"
        )
        print(
            f"   ✅ Интервал обновления: {data_management.get('update_interval', 60)} сек"
        )

        # Проверяем exchanges
        exchanges = config.get("exchanges", {})
        enabled_exchanges = [
            name for name, conf in exchanges.items() if conf.get("enabled")
        ]
        print(f"   ✅ Активные биржи: {', '.join(enabled_exchanges)}")

    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

    # 5. Проверка портов
    print("\n🌐 5. Сетевые порты")
    import socket

    ports_to_check = [
        (5555, "PostgreSQL"),
        (8080, "API сервер"),
        (5173, "Веб-интерфейс"),
    ]

    for port, name in ports_to_check:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("localhost", port))
        sock.close()

        if result == 0:
            print(f"   ✅ Порт {port} ({name}): Занят/Работает")
        else:
            print(f"   ⚠️ Порт {port} ({name}): Свободен")

    print("\n" + "=" * 60)
    print("✅ ПРОВЕРКА ЗАВЕРШЕНА")
    print("=" * 60)
    print("\n🚀 Для запуска системы используйте:")
    print("   ./start_with_logs.sh")
    print("\n🛑 Для остановки:")
    print("   ./stop_all.sh")


if __name__ == "__main__":
    asyncio.run(test_system())
