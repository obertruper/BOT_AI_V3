#!/usr/bin/env python3
"""
Тест локального подключения к PostgreSQL без TCP/IP
Работает через Unix socket для /mnt/SSD проекта
"""

import os

import psycopg2


def test_local_connection():
    """Тестирование локального подключения через Unix socket"""

    print("🔍 Тестирование ЛОКАЛЬНОГО подключения к PostgreSQL...")
    print(f"📁 Рабочая директория: {os.getcwd()}")
    print("📂 Проект на: /mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3")
    print("-" * 50)

    # Параметры для локального подключения (БЕЗ host!)
    db_params = {
        "dbname": "bot_trading_v3",
        "user": "obertruper",
        "port": "5555",  # PostgreSQL работает на порту 5555!
        # НЕ указываем host для Unix socket подключения!
    }

    try:
        print("🔌 Подключаемся через Unix socket (локально)...")
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()

        # Проверяем версию
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print("✅ Локальное подключение успешно!")
        print(f"📊 PostgreSQL: {version.split(',')[0]}")

        # Проверяем текущую БД
        cursor.execute("SELECT current_database(), current_user")
        db_info = cursor.fetchone()
        print(f"📁 База данных: {db_info[0]}")
        print(f"👤 Пользователь: {db_info[1]}")

        # Unix socket находится в /var/run/postgresql/
        print("🔌 Unix socket: /var/run/postgresql/ (порт 5555)")

        # Список таблиц
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public';
        """
        )
        table_count = cursor.fetchone()[0]
        print(f"📋 Таблиц в БД: {table_count}")

        cursor.close()
        conn.close()

        print("\n✅ УСПЕХ! Локальное подключение работает!")
        print("\n💡 Для подключения в коде используйте:")
        print("   psycopg2: dbname='bot_trading_v3' user='obertruper'")
        print("   SQLAlchemy: postgresql://obertruper@/bot_trading_v3")
        print("   Asyncpg: postgresql://obertruper@/bot_trading_v3")

        return True

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print("\n🔧 Возможные решения:")
        print("1. Убедитесь что PostgreSQL запущен")
        print("2. Проверьте что пользователь 'obertruper' существует")
        print("3. Проверьте права доступа к Unix socket")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("  ТЕСТ ЛОКАЛЬНОГО ПОДКЛЮЧЕНИЯ К PostgreSQL")
    print("=" * 60)
    test_local_connection()
    print("=" * 60)
