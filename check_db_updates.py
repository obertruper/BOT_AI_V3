#!/usr/bin/env python3
"""
Проверка сохранения новых сигналов и расчетов в БД после внесенных исправлений
"""

import asyncio

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool

logger = setup_logger(__name__)


async def check_new_data():
    print("=" * 80)
    print("ПРОВЕРКА СОХРАНЕНИЯ НОВЫХ СИГНАЛОВ И РАСЧЕТОВ В БД")
    print("=" * 80)

    # 1. Проверяем ProcessedMarketData
    print("\n1. ProcessedMarketData (обработанные индикаторы):")
    result = await AsyncPGPool.fetchrow(
        """
        SELECT
            COUNT(*) as total_records,
            COUNT(DISTINCT symbol) as unique_symbols,
            MAX(datetime) as last_record,
            MIN(datetime) as first_record
        FROM processed_market_data
        WHERE datetime > NOW() - INTERVAL '1 hour'
    """
    )

    if result and result["total_records"] > 0:
        print(f"   ✅ Записей за последний час: {result['total_records']}")
        print(f"   ✅ Уникальных символов: {result['unique_symbols']}")
        print(f"   ✅ Последняя запись: {result['last_record']}")

        # Проверяем наличие ML признаков
        features_check = await AsyncPGPool.fetchrow(
            """
            SELECT COUNT(*) as with_features
            FROM processed_market_data
            WHERE datetime > NOW() - INTERVAL '1 hour'
            AND ml_features IS NOT NULL
        """
        )
        print(f"   ✅ Записей с ML признаками: {features_check['with_features']}")
    else:
        print("   ❌ Нет новых записей в ProcessedMarketData за последний час")

    # 2. Проверяем ML predictions
    print("\n2. ML Predictions (предсказания модели):")
    result = await AsyncPGPool.fetchrow(
        """
        SELECT
            COUNT(*) as total_predictions,
            COUNT(DISTINCT symbol) as unique_symbols,
            COUNT(CASE WHEN symbol != 'UNKNOWN' THEN 1 END) as valid_symbols,
            MAX(datetime) as last_prediction,
            AVG(features_count) as avg_features,
            COUNT(CASE WHEN features_array IS NOT NULL THEN 1 END) as with_features_array
        FROM ml_predictions
        WHERE datetime > NOW() - INTERVAL '1 hour'
    """
    )

    if result and result["total_predictions"] > 0:
        print(f"   ✅ Предсказаний за последний час: {result['total_predictions']}")
        print(f"   ✅ Уникальных символов: {result['unique_symbols']}")
        print(f"   ✅ Валидных символов (не UNKNOWN): {result['valid_symbols']}")
        print(f"   ✅ Последнее предсказание: {result['last_prediction']}")
        avg_features = result["avg_features"] if result["avg_features"] else 0
        print(f"   ✅ Среднее кол-во признаков: {avg_features:.0f}")
        print(f"   ✅ С сохраненным массивом признаков: {result['with_features_array']}")
    else:
        print("   ❌ Нет новых предсказаний в ml_predictions за последний час")

    # 3. Проверяем signals
    print("\n3. Signals (торговые сигналы):")
    result = await AsyncPGPool.fetchrow(
        """
        SELECT
            COUNT(*) as total_signals,
            COUNT(DISTINCT symbol) as unique_symbols,
            MAX(created_at) as last_signal,
            COUNT(DISTINCT signal_type) as signal_types
        FROM signals
        WHERE created_at > NOW() - INTERVAL '1 hour'
    """
    )

    if result and result["total_signals"] > 0:
        print(f"   ✅ Сигналов за последний час: {result['total_signals']}")
        print(f"   ✅ Уникальных символов: {result['unique_symbols']}")
        print(f"   ✅ Последний сигнал: {result['last_signal']}")
        print(f"   ✅ Типов сигналов: {result['signal_types']}")
    else:
        print("   ❌ Нет новых сигналов в signals за последний час")

    # 4. Проверяем последние 5 записей с полными данными
    print("\n4. Последние 5 ML предсказаний с деталями:")
    predictions = await AsyncPGPool.fetch(
        """
        SELECT
            symbol,
            datetime,
            features_count,
            signal_type,
            signal_confidence,
            predicted_return_15m,
            CASE WHEN features_array IS NOT NULL THEN 'Да' ELSE 'Нет' END as has_features
        FROM ml_predictions
        WHERE datetime > NOW() - INTERVAL '1 hour'
        AND symbol != 'UNKNOWN'
        ORDER BY datetime DESC
        LIMIT 5
    """
    )

    if predictions:
        for pred in predictions:
            conf_percent = pred["signal_confidence"] * 100 if pred["signal_confidence"] else 0
            return_val = pred["predicted_return_15m"] if pred["predicted_return_15m"] else 0
            print(
                f"   • {pred['symbol']:10} | {pred['datetime']} | Features: {pred['features_count']:3} | "
                f"Signal: {pred['signal_type']:6} | Conf: {conf_percent:.1f}% | "
                f"Return: {return_val:.4f} | Full array: {pred['has_features']}"
            )
    else:
        print("   Нет данных")

    # 5. Проверяем связку данных
    print("\n5. Проверка связки данных (processed → predictions → signals):")
    result = await AsyncPGPool.fetchrow(
        """
        WITH recent_data AS (
            SELECT
                p.symbol,
                p.datetime as proc_time,
                m.datetime as pred_time,
                s.created_at as sig_time,
                p.ml_features,
                m.signal_type as ml_signal,
                s.signal_type as final_signal
            FROM processed_market_data p
            LEFT JOIN ml_predictions m ON p.symbol = m.symbol
                AND ABS(EXTRACT(EPOCH FROM (p.datetime - m.datetime))) < 60
            LEFT JOIN signals s ON p.symbol = s.symbol
                AND ABS(EXTRACT(EPOCH FROM (p.datetime - s.created_at))) < 60
            WHERE p.datetime > NOW() - INTERVAL '10 minutes'
        )
        SELECT
            COUNT(*) as total_chains,
            COUNT(CASE WHEN pred_time IS NOT NULL THEN 1 END) as with_predictions,
            COUNT(CASE WHEN sig_time IS NOT NULL THEN 1 END) as with_signals
        FROM recent_data
    """
    )

    if result and result["total_chains"] > 0:
        print(f"   ✅ Цепочек данных: {result['total_chains']}")
        print(f"   ✅ С предсказаниями: {result['with_predictions']}")
        print(f"   ✅ С финальными сигналами: {result['with_signals']}")
    else:
        print("   ❌ Нет связанных данных за последние 10 минут")

    # 6. Проверяем системный статус
    print("\n6. Общая статистика системы:")

    # Проверяем что система работает
    is_running = await AsyncPGPool.fetchrow(
        """
        SELECT
            (SELECT COUNT(*) FROM raw_market_data WHERE timestamp > EXTRACT(EPOCH FROM NOW() - INTERVAL '5 minutes') * 1000) as recent_raw_data,
            (SELECT COUNT(*) FROM orders WHERE created_at > NOW() - INTERVAL '1 hour') as recent_orders,
            (SELECT COUNT(*) FROM trades WHERE created_at > NOW() - INTERVAL '1 hour') as recent_trades
    """
    )

    print(f"   • Свежих raw данных (5 мин): {is_running['recent_raw_data']}")
    print(f"   • Ордеров за час: {is_running['recent_orders']}")
    print(f"   • Сделок за час: {is_running['recent_trades']}")

    if is_running["recent_raw_data"] == 0:
        print("   ⚠️  Система возможно не запущена - нет свежих рыночных данных!")

    # 7. Дополнительная проверка качества данных
    print("\n7. Качество сохраненных данных:")

    # Проверяем примеры сохраненных данных
    sample = await AsyncPGPool.fetchrow(
        """
        SELECT
            symbol,
            jsonb_object_keys(ml_features::jsonb) as feature_key
        FROM processed_market_data
        WHERE ml_features IS NOT NULL
        AND datetime > NOW() - INTERVAL '1 hour'
        LIMIT 1
    """
    )

    if sample:
        # Подсчитываем количество признаков в одной записи
        feature_count = await AsyncPGPool.fetchrow(
            """
            SELECT
                symbol,
                jsonb_array_length(
                    CASE
                        WHEN jsonb_typeof(ml_features::jsonb) = 'array'
                        THEN ml_features::jsonb
                        ELSE '[]'::jsonb
                    END
                ) as features_count
            FROM processed_market_data
            WHERE ml_features IS NOT NULL
            AND datetime > NOW() - INTERVAL '1 hour'
            LIMIT 1
        """
        )

        if feature_count:
            print(
                f"   ✅ Пример: {feature_count['symbol']} содержит {feature_count['features_count']} ML признаков"
            )

    print("\n" + "=" * 80)
    print("ИТОГОВАЯ ОЦЕНКА:")

    # Подводим итог
    all_ok = True

    # Проверяем ProcessedMarketData
    proc_result = await AsyncPGPool.fetchrow(
        "SELECT COUNT(*) as cnt FROM processed_market_data WHERE datetime > NOW() - INTERVAL '1 hour'"
    )
    proc_check = proc_result["cnt"] if proc_result else 0
    if proc_check > 0:
        print("   ✅ ProcessedMarketData: РАБОТАЕТ")
    else:
        print("   ❌ ProcessedMarketData: НЕ СОХРАНЯЕТСЯ")
        all_ok = False

    # Проверяем ML predictions с правильными символами
    pred_result = await AsyncPGPool.fetchrow(
        "SELECT COUNT(*) as cnt FROM ml_predictions WHERE datetime > NOW() - INTERVAL '1 hour' AND symbol != 'UNKNOWN'"
    )
    pred_check = pred_result["cnt"] if pred_result else 0
    if pred_check > 0:
        print("   ✅ ML Predictions: РАБОТАЕТ (символы корректные)")
    else:
        print("   ❌ ML Predictions: НЕ СОХРАНЯЕТСЯ или символы = UNKNOWN")
        all_ok = False

    # Проверяем полные массивы признаков
    array_result = await AsyncPGPool.fetchrow(
        "SELECT COUNT(*) as cnt FROM ml_predictions WHERE datetime > NOW() - INTERVAL '1 hour' AND features_array IS NOT NULL"
    )
    array_check = array_result["cnt"] if array_result else 0
    if array_check > 0:
        print("   ✅ Features Array: СОХРАНЯЕТСЯ")
    else:
        print("   ❌ Features Array: НЕ СОХРАНЯЕТСЯ")
        all_ok = False

    if all_ok:
        print("\n🎉 ВСЕ ИСПРАВЛЕНИЯ РАБОТАЮТ КОРРЕКТНО!")
    else:
        print("\n⚠️  ТРЕБУЕТСЯ ПРОВЕРКА - не все данные сохраняются")

    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(check_new_data())
