#!/usr/bin/env python3
"""
Упрощенный скрипт проверки БД для ML системы
"""

import os
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

# Конфигурация подключения
DB_CONFIG = {
    "host": os.getenv("PGHOST", "localhost"),
    "port": int(os.getenv("PGPORT", "5555")),
    "database": os.getenv("PGDATABASE", "bot_trading_v3"),
    "user": os.getenv("PGUSER", "obertruper"),
    "password": os.getenv("PGPASSWORD", ""),
}


def check_connection():
    """Проверка подключения к БД"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        print("✅ Подключение успешно!")
        print(f"📊 PostgreSQL версия: {version}")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False


def check_tables():
    """Проверка существования таблиц ML системы"""
    required_tables = [
        "raw_market_data",
        "processed_market_data",
        "signals",
        "technical_indicators",
        "market_data_snapshots",
    ]

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        print("\n🔍 Проверка таблиц ML системы:")

        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = ANY(%s)
            ORDER BY table_name;
        """,
            (required_tables,),
        )

        existing_tables = [row[0] for row in cur.fetchall()]

        print(f"✅ Найдено таблиц: {len(existing_tables)}/{len(required_tables)}")

        for table in required_tables:
            if table in existing_tables:
                print(f"  ✓ {table}")
            else:
                print(f"  ❌ {table} - НЕ НАЙДЕНА")

        # Проверяем количество записей в таблицах
        print("\n📊 Статистика таблиц:")
        for table in existing_tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                print(f"  {table:25} | Записей: {count:>10,}")
            except Exception as e:
                print(f"  {table:25} | Ошибка: {e}")

        cur.close()
        conn.close()

        return len(existing_tables) == len(required_tables)

    except Exception as e:
        print(f"❌ Ошибка проверки таблиц: {e}")
        return False


def check_indexes():
    """Проверка индексов"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        print("\n🔍 Проверка индексов:")

        cur.execute(
            """
            SELECT
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND tablename IN ('raw_market_data', 'processed_market_data', 'signals')
            ORDER BY tablename, indexname;
        """
        )

        indexes = cur.fetchall()

        tables = {}
        for idx in indexes:
            table = idx["tablename"]
            if table not in tables:
                tables[table] = []
            tables[table].append(idx["indexname"])

        for table, indexes in tables.items():
            print(f"\n  Таблица {table}:")
            for idx in indexes:
                print(f"    ✓ {idx}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Ошибка проверки индексов: {e}")


def create_scheduler_metrics_table():
    """Создание таблицы scheduler_metrics если её нет"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        print("\n🛠️ Проверка таблицы scheduler_metrics...")

        # Проверяем существование
        cur.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'scheduler_metrics'
            );
        """
        )

        exists = cur.fetchone()[0]

        if not exists:
            print("  ⚠️ Создаем таблицу scheduler_metrics...")

            # Создаем таблицу
            cur.execute(
                """
                CREATE TABLE scheduler_metrics (
                    id BIGSERIAL PRIMARY KEY,
                    cycle_start TIMESTAMP WITH TIME ZONE NOT NULL,
                    cycle_end TIMESTAMP WITH TIME ZONE NOT NULL,
                    duration_seconds FLOAT NOT NULL,
                    symbols_processed INTEGER NOT NULL,
                    signals_generated INTEGER NOT NULL,
                    errors_count INTEGER DEFAULT 0,
                    avg_symbol_processing_time FLOAT,
                    memory_usage_mb FLOAT,
                    cpu_usage_percent FLOAT,
                    status VARCHAR(20) DEFAULT 'completed',
                    error_details JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """
            )

            # Создаем индексы
            cur.execute(
                "CREATE INDEX idx_scheduler_metrics_cycle_start ON scheduler_metrics(cycle_start DESC);"
            )
            cur.execute("CREATE INDEX idx_scheduler_metrics_status ON scheduler_metrics(status);")

            conn.commit()
            print("  ✅ Таблица scheduler_metrics создана")
        else:
            print("  ✅ Таблица scheduler_metrics существует")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Ошибка создания таблицы scheduler_metrics: {e}")


def test_performance():
    """Тест производительности запросов"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        print("\n⚡ Тест производительности:")

        # Тест 1: Выборка последних данных
        import time

        start = time.time()

        cur.execute(
            """
            SELECT symbol, datetime, close, volume
            FROM raw_market_data
            WHERE interval_minutes = 15
            ORDER BY timestamp DESC
            LIMIT 100;
        """
        )

        elapsed = (time.time() - start) * 1000
        print(f"  ✅ Выборка последних 100 записей: {elapsed:.2f} мс")

        # Тест 2: Выборка по символу
        start = time.time()

        cur.execute(
            """
            SELECT COUNT(*)
            FROM raw_market_data
            WHERE symbol = 'BTCUSDT'
            AND interval_minutes = 15;
        """
        )

        count = cur.fetchone()[0]
        elapsed = (time.time() - start) * 1000
        print(f"  ✅ Подсчет записей BTCUSDT: {count} записей за {elapsed:.2f} мс")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Ошибка теста производительности: {e}")


def main():
    """Основная функция"""
    print("🚀 Проверка БД для ML системы BOT_AI_V3")
    print("=" * 60)
    print(f"📅 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔧 База данных: {DB_CONFIG['database']}")
    print(f"👤 Пользователь: {DB_CONFIG['user']}")
    print(f"🔌 Порт: {DB_CONFIG['port']}")
    print("=" * 60)

    if check_connection():
        tables_ok = check_tables()
        check_indexes()
        create_scheduler_metrics_table()
        test_performance()

        print("\n" + "=" * 60)
        if tables_ok:
            print("✅ База данных готова для ML системы!")
        else:
            print("⚠️ Необходимо применить миграции: alembic upgrade head")
    else:
        print("\n❌ Не удалось подключиться к базе данных")
        print("Проверьте настройки подключения и статус PostgreSQL")


if __name__ == "__main__":
    main()
