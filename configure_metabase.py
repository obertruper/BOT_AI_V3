#!/usr/bin/env python3
"""
Автоматическая настройка Metabase для BOT_AI_V3
"""

import sys
import time

import requests

METABASE_URL = "http://localhost:3000"
DB_PASSWORD = "ilpnqw1234"  # Пароль указанный пользователем


def wait_for_metabase():
    """Ожидание запуска Metabase"""
    print("⏳ Ожидание запуска Metabase...")
    for i in range(60):
        try:
            r = requests.get(f"{METABASE_URL}/api/health")
            if r.status_code == 200:
                print("✅ Metabase запущен")
                return True
        except:
            pass
        time.sleep(2)
    return False


def setup_initial_user():
    """Создание первого администратора"""
    print("\n📤 Настройка первого пользователя...")

    # Проверяем, требуется ли начальная настройка
    try:
        r = requests.get(f"{METABASE_URL}/api/session/properties")
        props = r.json()

        if props.get("has-user-setup"):
            print("ℹ️ Пользователь уже настроен")
            return True

    except Exception as e:
        print(f"⚠️ Ошибка проверки: {e}")

    # Настройка пользователя
    setup_data = {
        "user": {
            "first_name": "Admin",
            "last_name": "BOT_AI_V3",
            "email": "admin@botai.local",
            "password": "Admin123!@#",
        },
        "prefs": {"site_name": "BOT_AI_V3 Analytics", "site_locale": "ru"},
    }

    try:
        r = requests.post(f"{METABASE_URL}/api/setup", json=setup_data)
        if r.status_code == 200:
            print("✅ Администратор создан")
            print("   Email: admin@botai.local")
            print("   Password: Admin123!@#")
            return r.json().get("id")
    except Exception as e:
        print(f"❌ Ошибка создания пользователя: {e}")
        return None


def add_database_connection(session_token=None):
    """Добавление подключения к БД"""
    print("\n🔗 Настройка подключения к PostgreSQL...")

    db_config = {
        "engine": "postgres",
        "name": "BOT_AI_V3 Trading Database",
        "details": {
            "host": "host.docker.internal",
            "port": 5555,
            "dbname": "bot_trading_v3",
            "user": "obertruper",
            "password": DB_PASSWORD,
            "ssl": False,
            "tunnel-enabled": False,
        },
        "auto_run_queries": True,
        "is_full_sync": True,
        "schedules": {
            "cache_field_values": {"schedule_type": "daily", "schedule_hour": 3},
            "metadata_sync": {"schedule_type": "hourly"},
        },
    }

    headers = {}
    if session_token:
        headers["X-Metabase-Session"] = session_token

    try:
        # Пытаемся добавить БД
        r = requests.post(f"{METABASE_URL}/api/database", json=db_config, headers=headers)

        if r.status_code in [200, 201]:
            print("✅ База данных подключена")
            return r.json().get("id")
        else:
            print(f"⚠️ Ответ сервера: {r.status_code}")
            print(f"   {r.text}")
    except Exception as e:
        print(f"❌ Ошибка подключения БД: {e}")

    return None


def create_dashboard_examples():
    """Создание примеров дашбордов"""
    print("\n📊 Информация о дашбордах...")

    dashboards = [
        {
            "name": "ML Predictions Monitor",
            "description": "Мониторинг ML предсказаний в реальном времени",
        },
        {"name": "Trading Performance", "description": "Анализ торговой производительности"},
        {"name": "Signal Quality", "description": "Качество торговых сигналов"},
        {"name": "Risk Analysis", "description": "Анализ рисков и SL/TP эффективность"},
    ]

    print("\n📋 Рекомендуемые дашборды для создания:")
    for dash in dashboards:
        print(f"   • {dash['name']}: {dash['description']}")

    print("\n💡 Для создания дашбордов:")
    print("   1. Откройте http://localhost:3000")
    print("   2. Войдите с учетными данными выше")
    print("   3. Перейдите в SQL Editor")
    print("   4. Используйте запросы из metabase_dashboards.sql")


def main():
    print("=" * 50)
    print("   НАСТРОЙКА METABASE ДЛЯ BOT_AI_V3")
    print("=" * 50)

    if not wait_for_metabase():
        print("❌ Metabase не запустился")
        sys.exit(1)

    # Настройка администратора
    session_token = setup_initial_user()

    # Подключение БД
    db_id = add_database_connection(session_token)

    print("\n" + "=" * 50)
    print("   НАСТРОЙКА ЗАВЕРШЕНА")
    print("=" * 50)

    print("\n🎯 Следующие шаги:")
    print("1. Откройте браузер: http://localhost:3000")
    print("2. Войдите в систему с указанными данными")
    print("3. Проверьте подключение к БД в Admin → Databases")
    print("4. Создайте дашборды используя SQL из metabase_dashboards.sql")

    print("\n📊 Полезные SQL запросы сохранены в:")
    print("   • metabase_dashboards.sql - готовые views")
    print("   • docs/METABASE_SETUP.md - документация")


if __name__ == "__main__":
    main()
