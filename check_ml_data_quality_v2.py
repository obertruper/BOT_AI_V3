#!/usr/bin/env python3
"""
Проверка качества данных ML v2 - работа с JSONB структурой
"""

import asyncio
import json

import numpy as np

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool

logger = setup_logger("ml_data_quality")


async def check_processed_market_data():
    """Проверка данных в таблице processed_market_data с JSONB полями"""

    logger.info("\n" + "=" * 60)
    logger.info("📊 ПРОВЕРКА ТАБЛИЦЫ processed_market_data")
    logger.info("=" * 60)

    # Получаем последние данные
    query = """
        SELECT
            id, symbol, timestamp, datetime,
            open, high, low, close, volume,
            technical_indicators,
            ml_features,
            direction_15m, direction_1h,
            future_return_15m, future_return_1h
        FROM processed_market_data
        WHERE timestamp > EXTRACT(EPOCH FROM NOW() - INTERVAL '1 hour') * 1000
        ORDER BY timestamp DESC
        LIMIT 100
    """

    rows = await AsyncPGPool.fetch(query)

    if not rows:
        logger.warning("⚠️ Нет данных за последний час")
        # Проверяем есть ли вообще данные
        count_query = "SELECT COUNT(*) as cnt FROM processed_market_data"
        count_result = await AsyncPGPool.fetch(count_query)
        total_count = count_result[0]["cnt"]
        logger.info(f"Всего записей в таблице: {total_count}")

        if total_count > 0:
            # Получаем последние данные без фильтра времени
            query = """
                SELECT
                    id, symbol, timestamp, datetime,
                    open, high, low, close, volume,
                    technical_indicators,
                    ml_features
                FROM processed_market_data
                ORDER BY timestamp DESC
                LIMIT 10
            """
            rows = await AsyncPGPool.fetch(query)
        else:
            return False

    logger.info(f"📈 Найдено {len(rows)} записей")

    issues = []

    for row in rows[:5]:  # Проверяем первые 5 записей детально
        symbol = row["symbol"]

        # Проверяем основные числовые поля
        for field in ["open", "high", "low", "close", "volume"]:
            value = float(row[field]) if row[field] else 0
            if value <= 0:
                issues.append(f"❌ {symbol}: {field} = {value}")
            elif field != "volume" and value > 1000000:
                issues.append(f"⚠️ {symbol}: подозрительная цена {field} = {value}")

        # Проверяем technical_indicators JSONB
        if row["technical_indicators"]:
            try:
                indicators = (
                    json.loads(row["technical_indicators"])
                    if isinstance(row["technical_indicators"], str)
                    else row["technical_indicators"]
                )

                # Проверяем ключевые индикаторы
                for key in ["rsi", "macd", "bb_upper", "bb_lower", "ema_short", "ema_long"]:
                    if key in indicators:
                        val = indicators[key]
                        if val is None or (isinstance(val, (int, float)) and np.isnan(val)):
                            issues.append(f"❌ {symbol}: {key} = NaN")
                        elif key == "rsi" and (val < 0 or val > 100):
                            issues.append(f"❌ {symbol}: RSI вне диапазона = {val}")

            except Exception as e:
                issues.append(f"❌ {symbol}: ошибка парсинга technical_indicators: {e}")

        # Проверяем ml_features JSONB
        if row["ml_features"]:
            try:
                features = (
                    json.loads(row["ml_features"])
                    if isinstance(row["ml_features"], str)
                    else row["ml_features"]
                )

                # Проверяем на NaN значения
                nan_features = []
                for key, val in features.items():
                    if val is None or (isinstance(val, (int, float)) and np.isnan(val)):
                        nan_features.append(key)

                if nan_features:
                    issues.append(f"❌ {symbol}: NaN в ML features: {', '.join(nan_features[:5])}")

            except Exception as e:
                issues.append(f"❌ {symbol}: ошибка парсинга ml_features: {e}")

    # Статистика по символам
    symbols = set(row["symbol"] for row in rows)
    logger.info("\n📊 Статистика:")
    logger.info(f"  • Уникальных символов: {len(symbols)}")
    logger.info(f"  • Символы: {', '.join(list(symbols)[:10])}")

    # Проверяем временные интервалы
    if len(rows) > 1:
        timestamps = sorted([row["timestamp"] for row in rows])
        time_diffs = np.diff(timestamps)
        avg_diff = np.mean(time_diffs) / 1000 / 60  # в минутах
        logger.info(f"  • Средний интервал: {avg_diff:.2f} минут")

    # Выводим проблемы
    if issues:
        logger.warning(f"\n⚠️ Найдено {len(issues)} проблем:")
        for issue in issues[:10]:
            logger.warning(f"  {issue}")
        if len(issues) > 10:
            logger.warning(f"  ... и еще {len(issues) - 10} проблем")
        return False
    else:
        logger.info("\n✅ Данные в processed_market_data в норме!")
        return True


async def check_ml_predictions():
    """Проверка ML предсказаний в signals и processed_market_data"""

    logger.info("\n" + "=" * 60)
    logger.info("🤖 ПРОВЕРКА ML ПРЕДСКАЗАНИЙ")
    logger.info("=" * 60)

    # Проверяем сигналы
    query = """
        SELECT *
        FROM signals
        WHERE created_at > NOW() - INTERVAL '24 hours'
        ORDER BY created_at DESC
        LIMIT 50
    """

    rows = await AsyncPGPool.fetch(query)

    if not rows:
        logger.warning("⚠️ Нет сигналов за последние 24 часа")
    else:
        logger.info(f"📈 Найдено {len(rows)} сигналов")

        # Анализируем сигналы
        ml_signals = [
            r for r in rows if r.get("strategy_name") and "ml" in r["strategy_name"].lower()
        ]
        logger.info(f"  • ML сигналов: {len(ml_signals)}")

        if ml_signals:
            symbols = set(r["symbol"] for r in ml_signals)
            logger.info(f"  • Символы: {', '.join(symbols)}")

    # Проверяем предсказания в processed_market_data
    query = """
        SELECT
            symbol,
            COUNT(*) as cnt,
            AVG(future_return_15m) as avg_return_15m,
            AVG(future_return_1h) as avg_return_1h,
            SUM(CASE WHEN direction_15m = 1 THEN 1 ELSE 0 END) as buy_signals,
            SUM(CASE WHEN direction_15m = -1 THEN 1 ELSE 0 END) as sell_signals
        FROM processed_market_data
        WHERE timestamp > EXTRACT(EPOCH FROM NOW() - INTERVAL '1 hour') * 1000
        GROUP BY symbol
    """

    pred_rows = await AsyncPGPool.fetch(query)

    if pred_rows:
        logger.info("\n📊 Статистика предсказаний:")
        for row in pred_rows:
            if row["cnt"] > 0:
                buy_pct = (row["buy_signals"] or 0) / row["cnt"] * 100
                sell_pct = (row["sell_signals"] or 0) / row["cnt"] * 100
                logger.info(f"  • {row['symbol']}: BUY {buy_pct:.1f}%, SELL {sell_pct:.1f}%")

                if row["avg_return_15m"]:
                    logger.info(
                        f"    Средний return: 15m={row['avg_return_15m']:.4f}, 1h={row['avg_return_1h']:.4f}"
                    )

    return True


async def check_raw_market_data():
    """Проверка сырых рыночных данных"""

    logger.info("\n" + "=" * 60)
    logger.info("📈 ПРОВЕРКА RAW_MARKET_DATA")
    logger.info("=" * 60)

    query = """
        SELECT
            symbol,
            COUNT(*) as cnt,
            MIN(timestamp) as min_ts,
            MAX(timestamp) as max_ts,
            AVG(close) as avg_close
        FROM raw_market_data
        WHERE timestamp > EXTRACT(EPOCH FROM NOW() - INTERVAL '1 hour') * 1000
        GROUP BY symbol
    """

    rows = await AsyncPGPool.fetch(query)

    if not rows:
        logger.warning("⚠️ Нет сырых данных за последний час")

        # Проверяем общее количество
        count_query = "SELECT COUNT(*) as cnt FROM raw_market_data"
        count_result = await AsyncPGPool.fetch(count_query)
        total = count_result[0]["cnt"]
        logger.info(f"Всего записей: {total}")
        return False

    logger.info("📊 Данные по символам:")
    for row in rows:
        time_range = (row["max_ts"] - row["min_ts"]) / 1000 / 60
        logger.info(
            f"  • {row['symbol']}: {row['cnt']} записей за {time_range:.1f} мин, avg=${row['avg_close']:.2f}"
        )

    return True


async def check_database_integrity():
    """Проверка целостности связей между таблицами"""

    logger.info("\n" + "=" * 60)
    logger.info("🔗 ПРОВЕРКА ЦЕЛОСТНОСТИ ДАННЫХ")
    logger.info("=" * 60)

    # Проверяем связь raw_market_data -> processed_market_data
    query = """
        SELECT
            COUNT(DISTINCT r.id) as raw_count,
            COUNT(DISTINCT p.raw_data_id) as processed_count
        FROM raw_market_data r
        LEFT JOIN processed_market_data p ON r.id = p.raw_data_id
        WHERE r.timestamp > EXTRACT(EPOCH FROM NOW() - INTERVAL '1 hour') * 1000
    """

    result = await AsyncPGPool.fetch(query)
    if result:
        row = result[0]
        if row["raw_count"] and row["processed_count"]:
            coverage = row["processed_count"] / row["raw_count"] * 100
            logger.info(f"📊 Покрытие обработкой: {coverage:.1f}%")
            logger.info(f"  • Сырых данных: {row['raw_count']}")
            logger.info(f"  • Обработанных: {row['processed_count']}")
        else:
            logger.warning("⚠️ Нет данных для проверки связей")

    return True


async def main():
    """Основная функция проверки"""

    logger.info("\n" + "=" * 80)
    logger.info("🔍 ПРОВЕРКА КАЧЕСТВА ML ДАННЫХ V2")
    logger.info("=" * 80)

    results = {}

    # 1. Проверяем сырые данные
    results["raw_data"] = await check_raw_market_data()

    # 2. Проверяем обработанные данные
    results["processed_data"] = await check_processed_market_data()

    # 3. Проверяем ML предсказания
    results["ml_predictions"] = await check_ml_predictions()

    # 4. Проверяем целостность
    results["integrity"] = await check_database_integrity()

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
    elif passed >= total * 0.5:
        logger.info("✅ Система работоспособна")
    else:
        logger.warning("⚠️ Требуется загрузка свежих данных")

    # Рекомендации
    if not results["raw_data"]:
        logger.info("\n💡 Рекомендация: запустите загрузку исторических данных:")
        logger.info("   python scripts/load_historical_data_quick.py")

    if not results["processed_data"]:
        logger.info("\n💡 Рекомендация: проверьте работу ML pipeline:")
        logger.info("   python test_ml_uniqueness.py")


if __name__ == "__main__":
    asyncio.run(main())
