#!/usr/bin/env python3
"""
Проверка качества данных ML - входных параметров и выходных в БД
Проверяет на NaN, нули и нерелевантные значения
"""

import asyncio

import numpy as np
import pandas as pd

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool

logger = setup_logger("ml_data_quality")


async def check_processed_market_data():
    """Проверка данных в таблице processed_market_data"""

    logger.info("\n" + "=" * 60)
    logger.info("📊 ПРОВЕРКА ТАБЛИЦЫ processed_market_data")
    logger.info("=" * 60)

    # Получаем последние данные
    query = """
        SELECT *
        FROM processed_market_data
        WHERE timestamp > EXTRACT(EPOCH FROM NOW() - INTERVAL '1 hour') * 1000
        ORDER BY timestamp DESC
        LIMIT 100
    """

    rows = await AsyncPGPool.fetch(query)

    if not rows:
        logger.warning("⚠️ Нет данных за последний час")
        return False

    # Конвертируем в DataFrame для анализа
    df = pd.DataFrame([dict(row) for row in rows])

    logger.info(f"📈 Найдено {len(df)} записей за последний час")

    # Проверяем каждую колонку с числовыми данными
    numeric_columns = df.select_dtypes(include=[np.number]).columns

    issues = []

    for col in numeric_columns:
        # Пропускаем системные колонки
        if col in ["id", "timestamp", "created_at", "updated_at"]:
            continue

        # Проверка на NaN
        nan_count = df[col].isna().sum()
        if nan_count > 0:
            issues.append(f"❌ {col}: {nan_count} NaN значений")

        # Проверка на нули (для колонок где не должно быть нулей)
        if col not in ["returns_5m", "returns_15m", "returns_30m", "rsi_diff", "macd_diff"]:
            zero_count = (df[col] == 0).sum()
            if zero_count > len(df) * 0.5:  # Если больше 50% нулей
                issues.append(f"⚠️ {col}: {zero_count}/{len(df)} нулевых значений")

        # Проверка на inf
        inf_count = np.isinf(df[col].replace([None], 0)).sum()
        if inf_count > 0:
            issues.append(f"❌ {col}: {inf_count} inf значений")

        # Проверка диапазонов для специфичных индикаторов
        if "rsi" in col.lower():
            out_of_range = ((df[col] < 0) | (df[col] > 100)).sum()
            if out_of_range > 0:
                issues.append(f"❌ {col}: {out_of_range} значений вне диапазона [0, 100]")

    # Выводим статистику по ключевым полям
    logger.info("\n📊 Статистика ключевых полей:")

    key_fields = [
        "symbol",
        "close",
        "volume",
        "rsi_14",
        "macd",
        "bb_upper",
        "bb_lower",
        "returns_5m",
        "returns_15m",
        "returns_30m",
    ]

    for field in key_fields:
        if field in df.columns:
            if field == "symbol":
                unique = df[field].nunique()
                logger.info(f"  • {field}: {unique} уникальных символов")
            else:
                mean_val = df[field].mean()
                std_val = df[field].std()
                min_val = df[field].min()
                max_val = df[field].max()
                logger.info(
                    f"  • {field}: mean={mean_val:.4f}, std={std_val:.4f}, min={min_val:.4f}, max={max_val:.4f}"
                )

    # Проверяем временные метки
    logger.info("\n⏰ Проверка временных меток:")
    timestamps = df["timestamp"].values
    time_diffs = np.diff(sorted(timestamps))

    if len(time_diffs) > 0:
        avg_diff = np.mean(time_diffs) / 1000 / 60  # в минутах
        logger.info(f"  • Средний интервал между записями: {avg_diff:.2f} минут")

        if avg_diff > 5:
            issues.append(f"⚠️ Большие промежутки между данными: {avg_diff:.2f} минут")

    # Выводим найденные проблемы
    if issues:
        logger.warning("\n⚠️ НАЙДЕННЫЕ ПРОБЛЕМЫ:")
        for issue in issues:
            logger.warning(f"  {issue}")
        return False
    else:
        logger.info("\n✅ Все данные в норме!")
        return True


async def check_ml_predictions():
    """Проверка предсказаний ML модели в таблице signals"""

    logger.info("\n" + "=" * 60)
    logger.info("🤖 ПРОВЕРКА ML ПРЕДСКАЗАНИЙ (signals)")
    logger.info("=" * 60)

    query = """
        SELECT *
        FROM signals
        WHERE created_at > NOW() - INTERVAL '1 hour'
        AND strategy_name LIKE '%ml%'
        ORDER BY created_at DESC
        LIMIT 50
    """

    rows = await AsyncPGPool.fetch(query)

    if not rows:
        logger.warning("⚠️ Нет ML сигналов за последний час")
        return False

    logger.info(f"📈 Найдено {len(rows)} ML сигналов за последний час")

    issues = []
    signal_stats = {"total": len(rows), "buy": 0, "sell": 0, "symbols": set(), "strengths": []}

    for row in rows:
        # Проверяем основные поля
        if not row["symbol"]:
            issues.append("❌ Пустой символ в сигнале")

        # Проверяем signal_type вместо direction
        signal_type = row.get("signal_type", "")
        if signal_type not in ["BUY", "SELL"]:
            issues.append(f"❌ Неверный тип сигнала: {signal_type}")
        else:
            signal_stats["buy" if signal_type == "BUY" else "sell"] += 1

        signal_stats["symbols"].add(row["symbol"])

        # Проверяем strength (не signal_strength)
        strength = float(row["strength"]) if row.get("strength") else 0
        if strength <= 0 or strength > 1:
            issues.append(f"❌ Неверная сила сигнала: {strength} для {row['symbol']}")
        else:
            signal_stats["strengths"].append(strength)

        # Проверяем цены suggested_*
        for price_field in ["suggested_price", "suggested_stop_loss", "suggested_take_profit"]:
            if row.get(price_field):
                price = float(row[price_field])
                if price <= 0:
                    issues.append(f"❌ Неверная цена {price_field}: {price} для {row['symbol']}")
                elif price > 1000000:  # Слишком большая цена
                    issues.append(
                        f"⚠️ Подозрительная цена {price_field}: {price} для {row['symbol']}"
                    )

    # Выводим статистику
    logger.info("\n📊 Статистика сигналов:")
    logger.info(f"  • Всего сигналов: {signal_stats['total']}")
    logger.info(
        f"  • BUY: {signal_stats['buy']} ({signal_stats['buy'] / signal_stats['total'] * 100:.1f}%)"
    )
    logger.info(
        f"  • SELL: {signal_stats['sell']} ({signal_stats['sell'] / signal_stats['total'] * 100:.1f}%)"
    )
    logger.info(f"  • Уникальных символов: {len(signal_stats['symbols'])}")

    if signal_stats["strengths"]:
        avg_strength = np.mean(signal_stats["strengths"])
        logger.info(f"  • Средняя сила сигнала: {avg_strength:.3f}")

        # Проверяем распределение
        if avg_strength < 0.4 or avg_strength > 0.6:
            issues.append(f"⚠️ Несбалансированная средняя сила: {avg_strength:.3f}")

    # Проверяем частоту сигналов
    if rows:
        first_time = rows[-1]["created_at"]
        last_time = rows[0]["created_at"]
        time_span = (last_time - first_time).total_seconds() / 60  # в минутах

        if time_span > 0:
            signals_per_minute = len(rows) / time_span
            logger.info(f"  • Частота: {signals_per_minute:.2f} сигналов/минуту")

            if signals_per_minute > 10:
                issues.append(
                    f"⚠️ Слишком высокая частота: {signals_per_minute:.2f} сигналов/минуту"
                )

    # Выводим проблемы
    if issues:
        logger.warning("\n⚠️ НАЙДЕННЫЕ ПРОБЛЕМЫ:")
        for issue in issues[:10]:  # Показываем первые 10
            logger.warning(f"  {issue}")
        if len(issues) > 10:
            logger.warning(f"  ... и еще {len(issues) - 10} проблем")
        return False
    else:
        logger.info("\n✅ ML предсказания в норме!")
        return True


async def check_feature_engineering():
    """Проверка процесса feature engineering"""

    logger.info("\n" + "=" * 60)
    logger.info("🔧 ПРОВЕРКА FEATURE ENGINEERING")
    logger.info("=" * 60)

    # Проверяем последние обработанные данные
    query = """
        SELECT
            symbol,
            COUNT(*) as count,
            MIN(timestamp) as min_ts,
            MAX(timestamp) as max_ts,
            AVG(close) as avg_close,
            AVG(volume) as avg_volume
        FROM processed_market_data
        WHERE timestamp > EXTRACT(EPOCH FROM NOW() - INTERVAL '1 hour') * 1000
        GROUP BY symbol
    """

    rows = await AsyncPGPool.fetch(query)

    if not rows:
        logger.error("❌ Нет обработанных данных!")
        return False

    logger.info("📊 Статистика по символам:")

    for row in rows:
        time_range = (row["max_ts"] - row["min_ts"]) / 1000 / 60  # в минутах
        logger.info(f"  • {row['symbol']}: {row['count']} записей за {time_range:.1f} минут")
        logger.info(
            f"    Средняя цена: ${row['avg_close']:.2f}, Средний объем: {row['avg_volume']:.0f}"
        )

    # Проверяем консистентность данных
    query = """
        SELECT DISTINCT symbol
        FROM processed_market_data
        WHERE timestamp > EXTRACT(EPOCH FROM NOW() - INTERVAL '5 minutes') * 1000
    """

    recent_symbols = await AsyncPGPool.fetch(query)
    recent_symbols = {row["symbol"] for row in recent_symbols}

    if len(recent_symbols) < 5:
        logger.warning(f"⚠️ Мало активных символов: {len(recent_symbols)}")
        return False
    else:
        logger.info(f"✅ Активных символов: {len(recent_symbols)}")
        return True


async def fix_data_issues():
    """Исправление найденных проблем с данными"""

    logger.info("\n" + "=" * 60)
    logger.info("🔧 ИСПРАВЛЕНИЕ ПРОБЛЕМ С ДАННЫМИ")
    logger.info("=" * 60)

    fixes_applied = 0

    # 1. Удаляем записи с NaN значениями
    query = """
        DELETE FROM processed_market_data
        WHERE close IS NULL
           OR volume IS NULL
           OR rsi_14 IS NULL
           OR close = 'NaN'::float
           OR volume = 'NaN'::float
    """

    result = await AsyncPGPool.execute(query)
    if "DELETE" in result:
        count = int(result.split()[1])
        if count > 0:
            logger.info(f"✅ Удалено {count} записей с NaN значениями")
            fixes_applied += count

    # 2. Исправляем нулевые объемы
    query = """
        UPDATE processed_market_data
        SET volume = (
            SELECT AVG(volume)
            FROM processed_market_data p2
            WHERE p2.symbol = processed_market_data.symbol
              AND p2.volume > 0
              AND p2.timestamp > EXTRACT(EPOCH FROM NOW() - INTERVAL '1 hour') * 1000
        )
        WHERE volume = 0
          AND timestamp > EXTRACT(EPOCH FROM NOW() - INTERVAL '1 hour') * 1000
    """

    result = await AsyncPGPool.execute(query)
    if "UPDATE" in result:
        count = int(result.split()[1])
        if count > 0:
            logger.info(f"✅ Исправлено {count} записей с нулевым объемом")
            fixes_applied += count

    # 3. Исправляем RSI вне диапазона
    query = """
        UPDATE processed_market_data
        SET rsi_14 = CASE
            WHEN rsi_14 > 100 THEN 100
            WHEN rsi_14 < 0 THEN 0
            ELSE rsi_14
        END
        WHERE (rsi_14 > 100 OR rsi_14 < 0)
          AND timestamp > EXTRACT(EPOCH FROM NOW() - INTERVAL '1 hour') * 1000
    """

    result = await AsyncPGPool.execute(query)
    if "UPDATE" in result:
        count = int(result.split()[1])
        if count > 0:
            logger.info(f"✅ Исправлено {count} записей с RSI вне диапазона")
            fixes_applied += count

    if fixes_applied > 0:
        logger.info(f"\n✅ Всего исправлено: {fixes_applied} проблем")
    else:
        logger.info("\n✅ Проблем не найдено, исправления не требуются")

    return fixes_applied


async def main():
    """Основная функция проверки"""

    logger.info("\n" + "=" * 80)
    logger.info("🔍 ПРОВЕРКА КАЧЕСТВА ML ДАННЫХ")
    logger.info("=" * 80)

    results = {}

    # 1. Проверяем processed_market_data
    results["processed_data"] = await check_processed_market_data()

    # 2. Проверяем ML предсказания
    results["ml_predictions"] = await check_ml_predictions()

    # 3. Проверяем feature engineering
    results["feature_engineering"] = await check_feature_engineering()

    # 4. Применяем исправления если нужно
    if not all(results.values()):
        fixes = await fix_data_issues()
        if fixes > 0:
            logger.info("\n🔄 Повторная проверка после исправлений...")
            results["processed_data_after"] = await check_processed_market_data()
            results["ml_predictions_after"] = await check_ml_predictions()

    # Итоговый отчет
    logger.info("\n" + "=" * 80)
    logger.info("📊 ИТОГОВЫЙ ОТЧЕТ")
    logger.info("=" * 80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for check, status in results.items():
        status_str = "✅ PASSED" if status else "❌ FAILED"
        logger.info(f"  • {check}: {status_str}")

    logger.info(f"\n📈 Результат: {passed}/{total} проверок пройдено")

    if passed == total:
        logger.info("🎉 Все данные в отличном состоянии!")
    elif passed >= total * 0.7:
        logger.info("✅ Данные в хорошем состоянии")
    else:
        logger.warning("⚠️ Требуется внимание к качеству данных")


if __name__ == "__main__":
    asyncio.run(main())
