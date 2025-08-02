#!/usr/bin/env python3
"""
Визуализация структуры базы данных PostgreSQL
"""

from datetime import datetime

import psycopg2


def visualize_database():
    """Показать визуальную структуру БД"""

    # Параметры подключения
    conn_params = {"dbname": "bot_trading_v3", "user": "obertruper", "port": "5555"}

    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()

        print("\n" + "=" * 80)
        print("📊 СТРУКТУРА БАЗЫ ДАННЫХ: bot_trading_v3")
        print(f"🕐 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        # Информация о БД
        cursor.execute(
            """
            SELECT
                pg_database_size(current_database()) as size,
                pg_size_pretty(pg_database_size(current_database())) as size_pretty
        """
        )
        db_info = cursor.fetchone()
        print(f"\n📁 Размер БД: {db_info[1]}")

        # Схемы
        cursor.execute(
            """
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
            ORDER BY schema_name
        """
        )
        schemas = cursor.fetchall()
        print(f"\n📂 Схемы ({len(schemas)}):")
        for schema in schemas:
            print(f"   └─ {schema[0]}")

        # Таблицы
        cursor.execute(
            """
            SELECT
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """
        )
        tables = cursor.fetchall()

        if tables:
            print(f"\n📋 ТАБЛИЦЫ ({len(tables)}):")
            print("-" * 80)

            for schema, table, size in tables:
                print(f"\n🗂️  {table} [{size}]")

                # Колонки таблицы
                cursor.execute(
                    f"""
                    SELECT
                        column_name,
                        data_type,
                        character_maximum_length,
                        is_nullable,
                        column_default
                    FROM information_schema.columns
                    WHERE table_schema = '{schema}'
                    AND table_name = '{table}'
                    ORDER BY ordinal_position
                """
                )
                columns = cursor.fetchall()

                for col_name, col_type, max_len, nullable, default in columns:
                    # Формируем тип
                    type_str = col_type
                    if max_len:
                        type_str += f"({max_len})"

                    # Модификаторы
                    mods = []
                    if nullable == "NO":
                        mods.append("NOT NULL")
                    if default:
                        mods.append(
                            f"DEFAULT {default[:20]}..."
                            if len(str(default)) > 20
                            else f"DEFAULT {default}"
                        )

                    mod_str = " ".join(mods) if mods else ""

                    print(f"   ├─ {col_name:<30} {type_str:<20} {mod_str}")

                # Индексы
                cursor.execute(
                    f"""
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE schemaname = '{schema}'
                    AND tablename = '{table}'
                """
                )
                indexes = cursor.fetchall()

                if indexes:
                    print("   │")
                    print("   └─ 🔍 Индексы:")
                    for idx_name, idx_def in indexes:
                        print(f"      └─ {idx_name}")
        else:
            print("\n📋 База данных пока пустая (нет таблиц)")
            print("\n💡 Подсказка: Запустите миграции Alembic для создания структуры:")
            print("   alembic upgrade head")

        # Статистика
        cursor.execute(
            """
            SELECT
                (SELECT count(*) FROM pg_stat_user_tables) as user_tables,
                (SELECT count(*) FROM pg_stat_user_indexes) as user_indexes,
                (SELECT count(*) FROM pg_views WHERE schemaname = 'public') as views,
                (SELECT count(*) FROM pg_proc WHERE pronamespace = 'public'::regnamespace) as functions
        """
        )
        stats = cursor.fetchone()

        print("\n" + "=" * 80)
        print("📊 СТАТИСТИКА:")
        print(f"   Таблиц: {stats[0]}")
        print(f"   Индексов: {stats[1]}")
        print(f"   Представлений: {stats[2]}")
        print(f"   Функций: {stats[3]}")
        print("=" * 80)

        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        return False


if __name__ == "__main__":
    visualize_database()
