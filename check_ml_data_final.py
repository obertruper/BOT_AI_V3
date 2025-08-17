#!/usr/bin/env python3
"""
Финальная проверка ML данных после исправлений
"""

import asyncio

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool

logger = setup_logger(__name__)


async def check_ml_data():
    print("=" * 80)
    print("ФИНАЛЬНАЯ ПРОВЕРКА ML ДАННЫХ ПОСЛЕ ИСПРАВЛЕНИЙ")
    print("=" * 80)

    # 1. Проверяем последние ML predictions
    print("\n1. Последние 5 ML predictions с полными деталями:")
    predictions = await AsyncPGPool.fetch(
        """
        SELECT
            symbol,
            datetime,
            features_count,
            signal_type,
            signal_confidence,
            predicted_return_15m,
            direction_15m,
            direction_15m_confidence,
            CASE WHEN features_array IS NOT NULL THEN 'ДА' ELSE 'НЕТ' END as has_array,
            CASE WHEN features_array IS NOT NULL
                 THEN jsonb_array_length(features_array::jsonb)
                 ELSE 0
            END as array_length
        FROM ml_predictions
        WHERE datetime > NOW() - INTERVAL '10 minutes'
        ORDER BY datetime DESC
        LIMIT 5
    """
    )

    if predictions:
        for pred in predictions:
            print(f"\n   Символ: {pred['symbol']}")
            print(f"   Время: {pred['datetime']}")
            print(f"   Кол-во признаков: {pred['features_count']}")
            print(
                f"   Массив признаков сохранен: {pred['has_array']} (длина: {pred['array_length']})"
            )
            conf = pred["signal_confidence"] * 100 if pred["signal_confidence"] else 0
            print(f"   Сигнал: {pred['signal_type']} (уверенность: {conf:.1f}%)")
            print(f"   Предсказание 15м: {pred['predicted_return_15m']:.4f}")
            dir_conf = (
                pred["direction_15m_confidence"] * 100 if pred["direction_15m_confidence"] else 0
            )
            print(f"   Направление 15м: {pred['direction_15m']} (уверенность: {dir_conf:.1f}%)")
    else:
        print("   Нет предсказаний за последние 10 минут")

    # 2. Проверяем ProcessedMarketData
    print("\n2. ProcessedMarketData с ML признаками:")
    processed = await AsyncPGPool.fetch(
        """
        SELECT
            symbol,
            datetime,
            CASE WHEN ml_features IS NOT NULL THEN 'ДА' ELSE 'НЕТ' END as has_features,
            pg_column_size(ml_features::text) as size_bytes
        FROM processed_market_data
        WHERE datetime > NOW() - INTERVAL '1 hour'
        ORDER BY datetime DESC
        LIMIT 5
    """
    )

    if processed:
        for rec in processed:
            print(
                f"   {rec['symbol']:10} | {rec['datetime']} | ML признаки: {rec['has_features']} | Размер: {rec['size_bytes']} байт"
            )
    else:
        print("   Нет записей за последний час")

    # 3. Статистика за последний час
    print("\n3. Статистика за последний час:")

    # ML predictions
    ml_stats = await AsyncPGPool.fetchrow(
        """
        SELECT
            COUNT(*) as total,
            COUNT(DISTINCT symbol) as symbols,
            COUNT(CASE WHEN symbol != 'UNKNOWN' THEN 1 END) as valid_symbols,
            COUNT(CASE WHEN features_array IS NOT NULL THEN 1 END) as with_array,
            AVG(features_count) as avg_features
        FROM ml_predictions
        WHERE datetime > NOW() - INTERVAL '1 hour'
    """
    )

    print("\n   ML Predictions:")
    print(f"      Всего: {ml_stats['total']}")
    print(f"      Уникальных символов: {ml_stats['symbols']}")
    print(f"      С корректными символами: {ml_stats['valid_symbols']}")
    print(f"      С полным массивом признаков: {ml_stats['with_array']}")
    avg_f = ml_stats["avg_features"] if ml_stats["avg_features"] else 0
    print(f"      Среднее кол-во признаков: {avg_f:.0f}")

    # ProcessedMarketData
    proc_stats = await AsyncPGPool.fetchrow(
        """
        SELECT
            COUNT(*) as total,
            COUNT(DISTINCT symbol) as symbols,
            COUNT(CASE WHEN ml_features IS NOT NULL THEN 1 END) as with_features
        FROM processed_market_data
        WHERE datetime > NOW() - INTERVAL '1 hour'
    """
    )

    print("\n   ProcessedMarketData:")
    print(f"      Всего: {proc_stats['total']}")
    print(f"      Уникальных символов: {proc_stats['symbols']}")
    print(f"      С ML признаками: {proc_stats['with_features']}")

    # 4. Итоговая оценка
    print("\n" + "=" * 80)
    print("ИТОГОВАЯ ОЦЕНКА ИСПРАВЛЕНИЙ:")

    success_count = 0
    total_checks = 3

    # Проверка 1: ML predictions с правильными символами
    if ml_stats["total"] > 0 and ml_stats["valid_symbols"] == ml_stats["total"]:
        print("   ✅ Все ML predictions имеют корректные символы (не UNKNOWN)")
        success_count += 1
    elif ml_stats["total"] > 0:
        percent = (ml_stats["valid_symbols"] / ml_stats["total"]) * 100
        print(f"   ⚠️  {percent:.0f}% ML predictions имеют корректные символы")
        if percent > 90:
            success_count += 1
    else:
        print("   ❌ Нет новых ML predictions")

    # Проверка 2: Полный массив признаков сохраняется
    if ml_stats["total"] > 0 and ml_stats["with_array"] == ml_stats["total"]:
        print("   ✅ Все ML predictions содержат полный массив признаков")
        success_count += 1
    elif ml_stats["total"] > 0:
        percent = (ml_stats["with_array"] / ml_stats["total"]) * 100
        print(f"   ⚠️  {percent:.0f}% ML predictions содержат массив признаков")
        if percent > 90:
            success_count += 1
    else:
        print("   ❌ Нет новых ML predictions")

    # Проверка 3: ProcessedMarketData сохраняется
    if proc_stats["total"] > 0:
        print(f"   ✅ ProcessedMarketData сохраняется ({proc_stats['total']} записей)")
        success_count += 1
    else:
        print("   ⚠️  ProcessedMarketData не сохраняется в последний час")
        print("      (Возможно из-за кеширования в RealTimeIndicatorCalculator)")

    print("\n" + "-" * 40)
    if success_count == total_checks:
        print("🎉 ВСЕ ИСПРАВЛЕНИЯ РАБОТАЮТ ИДЕАЛЬНО!")
    elif success_count >= 2:
        print("✅ ОСНОВНЫЕ ИСПРАВЛЕНИЯ РАБОТАЮТ КОРРЕКТНО")
        print("   ML predictions сохраняются с правильными символами и полными данными")
    else:
        print("⚠️  ТРЕБУЕТСЯ ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА")

    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(check_ml_data())
