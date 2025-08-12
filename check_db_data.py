#!/usr/bin/env python3
"""
Проверка данных в базе данных
"""

import asyncio
import json
from datetime import datetime

import asyncpg
from dotenv import load_dotenv

load_dotenv()


async def check_database():
    """Проверяем что сохранено в БД"""

    # Подключаемся к БД напрямую через asyncpg
    conn = await asyncpg.connect(
        host="localhost",
        port=5555,
        user="obertruper",
        password="ilpnqw1234",
        database="bot_trading_v3",
    )

    print("🔍 ПРОВЕРКА БАЗЫ ДАННЫХ BOT_AI_V3")
    print("=" * 60)

    try:
        # 1. СИГНАЛЫ
        print("\n📊 СИГНАЛЫ (signals):")
        print("-" * 40)

        # Общее количество
        count = await conn.fetchval("SELECT COUNT(*) FROM signals")
        print(f"Всего сигналов: {count}")

        # Последние сигналы
        signals = await conn.fetch(
            """
            SELECT id, symbol, signal_type, strength, confidence,
                   suggested_price, suggested_stop_loss, suggested_take_profit,
                   created_at, metadata, indicators, strategy_name
            FROM signals
            ORDER BY created_at DESC
            LIMIT 5
        """
        )

        if signals:
            print("\nПоследние 5 сигналов:")
            for s in signals:
                print(f"\n  ID: {s['id']}")
                print(f"  Символ: {s['symbol']}")
                print(f"  Тип: {s['signal_type']}")
                print(f"  Стратегия: {s['strategy_name']}")
                print(f"  Сила: {s['strength']:.3f}")
                print(f"  Уверенность: {s['confidence']:.3f}")
                print(f"  Цена: ${s['suggested_price']}")
                print(f"  Stop Loss: ${s['suggested_stop_loss']}")
                print(f"  Take Profit: ${s['suggested_take_profit']}")
                print(f"  Создан: {s['created_at']}")
                if s["indicators"]:
                    print(
                        f"  Индикаторы: {json.dumps(s['indicators'], indent=4)[:200]}..."
                    )
                if s["metadata"]:
                    print(
                        f"  Метаданные: {json.dumps(s['metadata'], indent=4)[:200]}..."
                    )

        # Распределение по типам
        type_dist = await conn.fetch(
            """
            SELECT signal_type, COUNT(*) as count
            FROM signals
            GROUP BY signal_type
        """
        )
        print("\nРаспределение по типам:")
        for t in type_dist:
            print(f"  {t['signal_type']}: {t['count']}")

        # 2. ОРДЕРА
        print("\n📝 ОРДЕРА (orders):")
        print("-" * 40)

        count = await conn.fetchval("SELECT COUNT(*) FROM orders")
        print(f"Всего ордеров: {count}")

        # Статусы ордеров
        status_dist = await conn.fetch(
            """
            SELECT status, COUNT(*) as count
            FROM orders
            GROUP BY status
        """
        )
        print("\nРаспределение по статусам:")
        for s in status_dist:
            print(f"  {s['status']}: {s['count']}")

        # Последние ордера
        orders = await conn.fetch(
            """
            SELECT id, symbol, order_type, side, status,
                   quantity, price, stop_loss, take_profit, created_at
            FROM orders
            ORDER BY created_at DESC
            LIMIT 5
        """
        )

        if orders:
            print("\nПоследние 5 ордеров:")
            for o in orders:
                print(f"\n  ID: {o['id']}")
                print(f"  Символ: {o['symbol']}")
                print(f"  Тип/Сторона: {o['order_type']}/{o['side']}")
                print(f"  Статус: {o['status']}")
                print(f"  Количество: {o['quantity']}")
                print(f"  Цена: ${o['price']}")
                print(f"  SL/TP: ${o['stop_loss']}/{o['take_profit']}")
                print(f"  Создан: {o['created_at']}")

        # 3. СДЕЛКИ
        print("\n💰 СДЕЛКИ (trades):")
        print("-" * 40)

        count = await conn.fetchval("SELECT COUNT(*) FROM trades")
        print(f"Всего сделок: {count}")

        # Последние сделки
        trades = await conn.fetch(
            """
            SELECT id, symbol, side, quantity,
                   price, realized_pnl, commission, executed_at, strategy_name
            FROM trades
            ORDER BY executed_at DESC
            LIMIT 5
        """
        )

        if trades:
            print("\nПоследние 5 сделок:")
            for t in trades:
                print(f"\n  ID: {t['id']}")
                print(f"  Символ: {t['symbol']}")
                print(f"  Сторона: {t['side']}")
                print(f"  Стратегия: {t['strategy_name']}")
                print(f"  Количество: {t['quantity']}")
                print(f"  Цена: ${t['price']}")
                print(f"  PnL: ${t['realized_pnl']}")
                print(f"  Комиссия: ${t['commission']}")
                print(f"  Исполнен: {t['executed_at']}")

        # Общий PnL
        total_pnl = await conn.fetchval("SELECT SUM(realized_pnl) FROM trades")
        print(f"\nОбщий PnL: ${total_pnl or 0:.2f}")

        # 4. РЫНОЧНЫЕ ДАННЫЕ
        print("\n📈 РЫНОЧНЫЕ ДАННЫЕ (raw_market_data):")
        print("-" * 40)

        count = await conn.fetchval("SELECT COUNT(*) FROM raw_market_data")
        print(f"Всего свечей: {count}")

        # Символы с данными
        symbols = await conn.fetch(
            """
            SELECT symbol, COUNT(*) as count,
                   MIN(timestamp) as first_candle,
                   MAX(timestamp) as last_candle
            FROM raw_market_data
            GROUP BY symbol
            ORDER BY count DESC
            LIMIT 5
        """
        )

        if symbols:
            print("\nТоп-5 символов по количеству данных:")
            for s in symbols:
                print(f"  {s['symbol']}: {s['count']} свечей")
                print(f"    Первая: {s['first_candle']}")
                print(f"    Последняя: {s['last_candle']}")

        # 5. ОБРАБОТАННЫЕ ДАННЫЕ (ML features)
        print("\n🤖 ML FEATURES (processed_market_data):")
        print("-" * 40)

        count = await conn.fetchval("SELECT COUNT(*) FROM processed_market_data")
        print(f"Всего записей с features: {count}")

        if count > 0:
            # Последняя запись
            latest = await conn.fetchrow(
                """
                SELECT symbol, technical_indicators, ml_features, datetime,
                       direction_15m, direction_1h, direction_4h, direction_12h
                FROM processed_market_data
                ORDER BY datetime DESC
                LIMIT 1
            """
            )

            if latest:
                print("\nПоследняя запись:")
                print(f"  Символ: {latest['symbol']}")
                print(f"  Время: {latest['datetime']}")
                print(
                    f"  Направления (15m/1h/4h/12h): {latest['direction_15m']}/{latest['direction_1h']}/{latest['direction_4h']}/{latest['direction_12h']}"
                )
                if latest["technical_indicators"]:
                    # Парсим JSON если это строка
                    indicators = latest["technical_indicators"]
                    if isinstance(indicators, str):
                        indicators = json.loads(indicators)
                    print(f"  Количество индикаторов: {len(indicators)}")
                    # Показываем первые несколько индикаторов
                    if isinstance(indicators, dict):
                        indicators_sample = dict(list(indicators.items())[:5])
                        print(
                            f"  Примеры индикаторов: {json.dumps(indicators_sample, indent=4)}"
                        )
                if latest["ml_features"]:
                    ml_features = latest["ml_features"]
                    if isinstance(ml_features, str):
                        ml_features = json.loads(ml_features)
                    print(
                        f"  Количество ML features: {len(ml_features) if ml_features else 0}"
                    )

        # 6. ТЕХНИЧЕСКИЕ ИНДИКАТОРЫ
        print("\n📉 ТЕХНИЧЕСКИЕ ИНДИКАТОРЫ (technical_indicators):")
        print("-" * 40)

        # Проверяем существование таблицы
        table_exists = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'technical_indicators'
            )
        """
        )

        if table_exists:
            count = await conn.fetchval("SELECT COUNT(*) FROM technical_indicators")
            print(f"Всего записей: {count}")

            if count > 0:
                # Последние индикаторы
                indicators = await conn.fetch(
                    """
                    SELECT symbol, indicator_name, value, created_at
                    FROM technical_indicators
                    ORDER BY created_at DESC
                    LIMIT 10
                """
                )

                if indicators:
                    print("\nПоследние 10 индикаторов:")
                    for i in indicators:
                        print(
                            f"  {i['symbol']} - {i['indicator_name']}: {i['value']:.4f} ({i['created_at']})"
                        )
        else:
            print("Таблица не найдена")

        # 7. СТАТИСТИКА ЗА СЕГОДНЯ
        print("\n📅 СТАТИСТИКА ЗА СЕГОДНЯ:")
        print("-" * 40)

        today = datetime.now().date()

        # Сигналы за сегодня
        today_signals = await conn.fetchval(
            """
            SELECT COUNT(*) FROM signals
            WHERE DATE(created_at) = $1
        """,
            today,
        )
        print(f"Сигналов создано: {today_signals}")

        # Ордера за сегодня
        today_orders = await conn.fetchval(
            """
            SELECT COUNT(*) FROM orders
            WHERE DATE(created_at) = $1
        """,
            today,
        )
        print(f"Ордеров создано: {today_orders}")

        # Сделки за сегодня
        today_trades = await conn.fetchval(
            """
            SELECT COUNT(*) FROM trades
            WHERE DATE(executed_at) = $1
        """,
            today,
        )
        print(f"Сделок исполнено: {today_trades}")

        # PnL за сегодня
        today_pnl = await conn.fetchval(
            """
            SELECT SUM(realized_pnl) FROM trades
            WHERE DATE(executed_at) = $1
        """,
            today,
        )
        print(f"PnL за сегодня: ${today_pnl or 0:.2f}")

    finally:
        await conn.close()

    print("\n" + "=" * 60)
    print("✅ Проверка завершена")


if __name__ == "__main__":
    asyncio.run(check_database())
