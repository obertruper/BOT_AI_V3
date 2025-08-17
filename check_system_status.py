#!/usr/bin/env python3
"""
Проверка статуса системы и сохранения данных
"""

import asyncio
import subprocess

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool

logger = setup_logger(__name__)


async def check_system():
    print("=" * 80)
    print("ПРОВЕРКА СТАТУСА СИСТЕМЫ И ДАННЫХ")
    print("=" * 80)

    # 1. ProcessedMarketData
    result = await AsyncPGPool.fetchrow(
        """
        SELECT
            COUNT(*) as total,
            MAX(datetime) as last_date,
            MIN(datetime) as first_date
        FROM processed_market_data
        WHERE datetime > NOW() - INTERVAL '24 hours'
    """
    )
    print("\n1. ProcessedMarketData за 24 часа:")
    print(f"   Всего записей: {result['total']}")
    print(f"   Первая: {result['first_date']}")
    print(f"   Последняя: {result['last_date']}")

    # 2. ML Predictions
    result = await AsyncPGPool.fetchrow(
        """
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN symbol != 'UNKNOWN' THEN 1 END) as valid,
            MAX(datetime) as last_date
        FROM ml_predictions
        WHERE datetime > NOW() - INTERVAL '24 hours'
    """
    )
    print("\n2. ML Predictions за 24 часа:")
    print(f"   Всего: {result['total']}")
    print(f"   С валидным символом: {result['valid']}")
    print(f"   Последняя: {result['last_date']}")

    # 3. Raw Market Data - проверяем свежесть данных
    result = await AsyncPGPool.fetchrow(
        """
        SELECT
            COUNT(*) as cnt,
            MAX(datetime) as last_date
        FROM raw_market_data
        WHERE datetime > NOW() - INTERVAL '10 minutes'
    """
    )
    print("\n3. Raw Market Data (свежие):")
    print(f"   За 10 минут: {result['cnt']} записей")
    print(f"   Последняя: {result['last_date']}")

    # 4. Проверяем процессы системы
    print("\n4. Проверка процессов системы:")
    try:
        result = subprocess.run(["pgrep", "-f", "unified_launcher"], capture_output=True, text=True)
        if result.stdout:
            print("   ✅ unified_launcher запущен (PID: " + result.stdout.strip() + ")")
        else:
            print("   ❌ unified_launcher НЕ запущен")

        result = subprocess.run(["pgrep", "-f", "main.py"], capture_output=True, text=True)
        if result.stdout:
            print("   ✅ main.py запущен (PID: " + result.stdout.strip() + ")")
        else:
            print("   ❌ main.py НЕ запущен")
    except:
        print("   Не удалось проверить процессы")

    # 5. Последние ML predictions для анализа
    print("\n5. Последние 10 ML predictions (все время):")
    predictions = await AsyncPGPool.fetch(
        """
        SELECT
            symbol,
            datetime,
            features_count,
            signal_type,
            CASE WHEN features_array IS NOT NULL THEN 'Yes' ELSE 'No' END as has_array
        FROM ml_predictions
        ORDER BY datetime DESC
        LIMIT 10
    """
    )

    if predictions:
        for pred in predictions:
            print(
                f"   {pred['symbol']:10} | {pred['datetime']} | Features: {pred['features_count']:3} | {pred['signal_type']:6} | Array: {pred['has_array']}"
            )
    else:
        print("   Нет записей в ml_predictions")

    # 6. Проверяем содержимое ml_features в ProcessedMarketData
    print("\n6. Анализ ml_features в ProcessedMarketData:")
    sample = await AsyncPGPool.fetchrow(
        """
        SELECT
            symbol,
            datetime,
            pg_column_size(ml_features::text) as size_bytes,
            jsonb_typeof(ml_features::jsonb) as json_type
        FROM processed_market_data
        WHERE ml_features IS NOT NULL
        ORDER BY datetime DESC
        LIMIT 1
    """
    )

    if sample:
        print(f"   Символ: {sample['symbol']}")
        print(f"   Время: {sample['datetime']}")
        print(f"   Размер данных: {sample['size_bytes']} байт")
        print(f"   Тип JSON: {sample['json_type']}")

        # Попробуем получить первый элемент если это массив
        if sample["json_type"] == "object":
            keys_result = await AsyncPGPool.fetch(
                """
                SELECT jsonb_object_keys(ml_features::jsonb) as key
                FROM processed_market_data
                WHERE ml_features IS NOT NULL
                ORDER BY datetime DESC
                LIMIT 1
            """
            )
            if keys_result:
                print(f"   Количество ключей в объекте: {len(keys_result)}")
                print(f"   Примеры ключей: {', '.join([r['key'] for r in keys_result[:5]])}")

    # 7. Итоговая оценка
    print("\n" + "=" * 80)
    print("ИТОГОВАЯ ОЦЕНКА:")

    proc_data = await AsyncPGPool.fetchrow(
        "SELECT COUNT(*) as cnt FROM processed_market_data WHERE datetime > NOW() - INTERVAL '1 hour'"
    )
    ml_data = await AsyncPGPool.fetchrow(
        "SELECT COUNT(*) as cnt FROM ml_predictions WHERE datetime > NOW() - INTERVAL '1 hour'"
    )

    if proc_data["cnt"] > 0:
        print("   ✅ ProcessedMarketData: СОХРАНЯЕТСЯ")
    else:
        print("   ⚠️  ProcessedMarketData: НЕТ НОВЫХ ДАННЫХ")

    if ml_data["cnt"] > 0:
        print("   ✅ ML Predictions: СОХРАНЯЕТСЯ")
    else:
        print("   ⚠️  ML Predictions: НЕТ НОВЫХ ДАННЫХ (система не запущена?)")

    print("\nРЕКОМЕНДАЦИИ:")
    print("1. Запустить систему: python3 unified_launcher.py --mode=ml")
    print("2. Подождать несколько минут для генерации сигналов")
    print("3. Перезапустить этот скрипт для проверки")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(check_system())
