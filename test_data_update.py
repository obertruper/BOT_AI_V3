#!/usr/bin/env python3
"""
Тест системы автоматического обновления данных
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


async def test_data_update():
    """Тестирование автообновления данных"""
    print("🧪 Тестирование системы автообновления данных...\n")

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
        for key, status in data_status.items():
            print(f"\n   📊 {status.symbol} ({status.interval_minutes} мин):")
            print(f"      - Свечей в БД: {status.candles_count}")
            print(f"      - Последние данные: {status.latest_timestamp}")
            print(
                f"      - Готов для ML: {'✅' if status.is_sufficient_for_ml else '❌'}"
            )
            print(f"      - Пропусков: {len(status.gaps)}")

            if status.gaps:
                for gap in status.gaps[:2]:  # Показываем первые 2 пропуска
                    print(
                        f"        Gap: {gap.start_time} - {gap.end_time} ({gap.expected_candles} свечей)"
                    )

        # Проверка обновления данных
        print("\n3️⃣ Тестирование обновления данных...")

        # Получаем количество данных до обновления
        pool = await AsyncPGPool.get_pool()
        before_count = await pool.fetchval(
            """
            SELECT COUNT(*) FROM raw_market_data
            WHERE symbol = 'BTCUSDT'
            AND interval_minutes = 15
            AND datetime > NOW() - INTERVAL '1 hour'
        """
        )

        print(f"   Свечей за последний час ДО обновления: {before_count}")

        # Ждем одно обновление (60 секунд)
        print("\n   ⏳ Ждем автоматического обновления (60 сек)...")
        await asyncio.sleep(65)

        # Проверяем после обновления
        after_count = await pool.fetchval(
            """
            SELECT COUNT(*) FROM raw_market_data
            WHERE symbol = 'BTCUSDT'
            AND interval_minutes = 15
            AND datetime > NOW() - INTERVAL '1 hour'
        """
        )

        print(f"   Свечей за последний час ПОСЛЕ обновления: {after_count}")

        if after_count > before_count:
            print(
                f"   ✅ Данные обновились! Добавлено {after_count - before_count} новых свечей"
            )
        else:
            print("   ⚠️ Новых данных не появилось (возможно, рынок закрыт)")

        # Проверка работы с биржей
        print("\n4️⃣ Тестирование получения данных с биржи...")

        from exchanges.bybit.bybit_exchange import BybitExchange

        exchange = BybitExchange(
            api_key=os.getenv("BYBIT_API_KEY"),
            api_secret=os.getenv("BYBIT_API_SECRET"),
            sandbox=False,
        )

        # Получаем последние свечи
        candles = await exchange.get_recent_candles(
            symbol="BTCUSDT", interval_minutes=15, count=5
        )

        print(f"   Получено {len(candles)} свечей с биржи:")
        for candle in candles[-3:]:  # Показываем последние 3
            print(
                f"      {candle.timestamp}: O={candle.open_price} H={candle.high_price} "
                f"L={candle.low_price} C={candle.close_price} V={candle.volume}"
            )

        # Остановка службы
        print("\n5️⃣ Остановка службы...")
        await data_service.stop()
        print("   ✅ Служба остановлена")

        print("\n✅ Тестирование завершено успешно!")

    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
        import traceback

        traceback.print_exc()

        # Убедимся что служба остановлена
        if data_service.is_running:
            await data_service.stop()


if __name__ == "__main__":
    asyncio.run(test_data_update())
