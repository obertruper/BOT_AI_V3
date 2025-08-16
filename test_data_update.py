#!/usr/bin/env python3
"""
Тест системы автоматического обновления данных
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

from core.config.config_manager import ConfigManager
from database.connections.postgres import AsyncPGPool

# Загружаем переменные окружения
load_dotenv()


async def test_data_updates():
    """Проверка системы автоматического обновления данных"""

    print("=" * 60)
    print("🔍 ПРОВЕРКА СИСТЕМЫ АВТООБНОВЛЕНИЯ ДАННЫХ")
    print("=" * 60)

    # Загружаем конфигурацию
    config_manager = ConfigManager()
    config = config_manager.get_config()
    data_config = config.get("data_management", {})

    print("\n📋 Конфигурация data_management:")
    print(f"   • auto_update: {data_config.get('auto_update', False)}")
    print(
        f"   • update_interval: {data_config.get('update_interval', 60)} сек ({data_config.get('update_interval', 60) / 60:.1f} мин)"
    )
    print(f"   • initial_load_days: {data_config.get('initial_load_days', 7)} дней")
    print(f"   • min_candles_for_ml: {data_config.get('min_candles_for_ml', 96)} свечей")
    print(f"   • check_on_startup: {data_config.get('check_on_startup', True)}")

    # Проверяем данные в БД
    print("\n📊 Проверка данных в базе:")

    try:
        # Проверка общего количества данных
        total = await AsyncPGPool.fetch("SELECT COUNT(*) as cnt FROM raw_market_data")
        print(f"   • Всего записей: {total[0]['cnt']}")

        # Проверка свежих данных (последний час)
        fresh_1h = await AsyncPGPool.fetch(
            """SELECT COUNT(*) as cnt, COUNT(DISTINCT symbol) as symbols
               FROM raw_market_data
               WHERE timestamp > EXTRACT(EPOCH FROM NOW() - INTERVAL '1 hour') * 1000"""
        )
        print(
            f"   • За последний час: {fresh_1h[0]['cnt']} записей ({fresh_1h[0]['symbols']} символов)"
        )

        # Проверка данных за последние 24 часа
        fresh_24h = await AsyncPGPool.fetch(
            """SELECT COUNT(*) as cnt, COUNT(DISTINCT symbol) as symbols
               FROM raw_market_data
               WHERE timestamp > EXTRACT(EPOCH FROM NOW() - INTERVAL '24 hours') * 1000"""
        )
        print(
            f"   • За последние 24 часа: {fresh_24h[0]['cnt']} записей ({fresh_24h[0]['symbols']} символов)"
        )

        # Проверка последнего обновления по символам
        last_updates = await AsyncPGPool.fetch(
            """SELECT symbol,
                      MAX(timestamp) as last_timestamp,
                      COUNT(*) as candle_count
               FROM raw_market_data
               GROUP BY symbol
               ORDER BY last_timestamp DESC
               LIMIT 5"""
        )

        print("\n   📈 Последние обновления по символам:")
        for row in last_updates:
            # Конвертируем timestamp из миллисекунд
            last_time = (
                datetime.fromtimestamp(row["last_timestamp"] / 1000)
                if row["last_timestamp"]
                else None
            )
            if last_time:
                age = datetime.now() - last_time
                age_str = (
                    f"{age.days}д {age.seconds // 3600}ч"
                    if age.days > 0
                    else f"{age.seconds // 3600}ч {(age.seconds % 3600) // 60}м"
                )
                print(
                    f"      • {row['symbol']}: {row['candle_count']} свечей, последняя {age_str} назад"
                )
            else:
                print(f"      • {row['symbol']}: {row['candle_count']} свечей")

        # Проверка готовности для ML (минимум 96 свечей)
        ml_ready = await AsyncPGPool.fetch(
            """SELECT symbol, COUNT(*) as cnt
               FROM raw_market_data
               GROUP BY symbol
               HAVING COUNT(*) >= 96"""
        )
        print(f"\n   🤖 Символов готовых для ML (≥96 свечей): {len(ml_ready)}")

    except Exception as e:
        print(f"   ❌ Ошибка проверки БД: {e}")

    # Проверка DataUpdateService
    print("\n🔄 Проверка DataUpdateService:")
    try:
        from data.data_update_service import DataUpdateService

        service = DataUpdateService(config_manager)
        print("   ✅ DataUpdateService инициализирован")
        print(
            f"   • Интервал обновления: {service.update_interval} сек ({service.update_interval / 60:.1f} мин)"
        )
        print(f"   • Автообновление: {'Включено' if service.auto_update else 'Отключено'}")

    except Exception as e:
        print(f"   ❌ Ошибка инициализации DataUpdateService: {e}")

    print("\n" + "=" * 60)
    print("📌 РЕЗЮМЕ:")

    if data_config.get("auto_update", False):
        interval_min = data_config.get("update_interval", 60) / 60
        print(f"✅ Автообновление ВКЛЮЧЕНО (каждые {interval_min:.1f} минут)")
    else:
        print("⚠️ Автообновление ОТКЛЮЧЕНО")

    if fresh_1h[0]["cnt"] > 0:
        print("✅ Есть свежие данные (за последний час)")
    else:
        print("⚠️ Нет свежих данных - требуется загрузка")

    print("\n🚀 При запуске через ./start_with_logs.sh:")
    print("   1. Автоматически проверит свежесть данных")
    print("   2. Загрузит недостающие данные если нужно")
    print(
        f"   3. Запустит автообновление каждые {data_config.get('update_interval', 60) / 60:.1f} минут"
    )

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_data_updates())
