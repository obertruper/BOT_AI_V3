#!/usr/bin/env python3
"""
Простой тест системы автоматического обновления данных
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# Устанавливаем переменные окружения
os.environ["PGPORT"] = "5555"
os.environ["PGUSER"] = "obertruper"
os.environ["PGDATABASE"] = "bot_trading_v3"


async def test_data_status():
    """Тестирование статуса данных"""
    print("🧪 Проверка статуса данных в системе...\n")

    from core.config.config_manager import get_global_config_manager
    from data.data_update_service import DataUpdateService
    from database.connections.postgres import AsyncPGPool

    # Инициализация
    config_manager = get_global_config_manager()
    data_service = DataUpdateService(config_manager)

    print("1️⃣ Инициализация DataUpdateService...")

    try:
        # Запуск службы
        await data_service.start()
        print("   ✅ Служба запущена")

        # Получение статуса данных
        print("\n2️⃣ Проверка статуса данных...")

        data_status = await data_service.get_data_status(force_refresh=True)

        print(f"   Найдено конфигураций: {len(data_status)}")

        # Анализ по каждому символу
        total_gaps = 0
        symbols_need_update = []

        for key, status in data_status.items():
            print(f"\n   📊 {status.symbol} ({status.interval_minutes} мин):")
            print(f"      - Свечей в БД: {status.candles_count}")
            print(f"      - Последние данные: {status.latest_timestamp}")
            print(
                f"      - Готов для ML: {'✅' if status.is_sufficient_for_ml else '❌'}"
            )
            print(f"      - Пропусков: {len(status.gaps)}")

            if status.gaps:
                total_gaps += len(status.gaps)
                symbols_need_update.append(status.symbol)
                for gap in status.gaps[:1]:  # Показываем первый пропуск
                    print(
                        f"        Gap: {gap.start_time} - {gap.end_time} ({gap.expected_candles} свечей)"
                    )

        # Выводы
        print("\n📊 ИТОГО:")
        print(f"   - Всего символов: {len(data_status)}")
        print(f"   - Символов с пропусками: {len(symbols_need_update)}")
        print(f"   - Общее количество пропусков: {total_gaps}")

        if symbols_need_update:
            print(
                f"\n⚠️  Символы требующие обновления: {', '.join(symbols_need_update)}"
            )
            print("\n🔄 Запускаем заполнение критических пропусков...")

            # Даем службе время начать загрузку
            await asyncio.sleep(5)

            # Проверяем начало загрузки
            pool = await AsyncPGPool.get_pool()

            for symbol in symbols_need_update[:3]:  # Проверяем первые 3 символа
                count = await pool.fetchval(
                    """
                    SELECT COUNT(*) FROM raw_market_data
                    WHERE symbol = $1
                    AND interval_minutes = 15
                    AND datetime > NOW() - INTERVAL '1 minute'
                """,
                    symbol,
                )

                if count > 0:
                    print(
                        f"   ✅ {symbol}: началась загрузка новых данных ({count} свечей)"
                    )
                else:
                    print(f"   ⏳ {symbol}: ожидание загрузки...")

        else:
            print("\n✅ Все данные актуальны!")

        # Остановка службы
        print("\n5️⃣ Остановка службы...")
        await data_service.stop()
        print("   ✅ Служба остановлена")

        print("\n✅ Проверка завершена!")

    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
        import traceback

        traceback.print_exc()

        # Убедимся что служба остановлена
        if data_service.is_running:
            await data_service.stop()


if __name__ == "__main__":
    asyncio.run(test_data_status())
