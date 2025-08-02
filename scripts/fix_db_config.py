#!/usr/bin/env python3
"""Исправление жестко зашитых параметров БД в проекте."""

import re
from pathlib import Path


def fix_db_config():
    """Исправляет жестко зашитые параметры БД."""

    print("🔧 Исправление конфигурации БД...")

    # 1. Исправляем database/connections/postgres.py
    postgres_file = Path("database/connections/postgres.py")
    if postgres_file.exists():
        content = postgres_file.read_text()

        # Убираем жестко зашитый пароль
        content = re.sub(
            r"DB_PASSWORD = os\.getenv\('PGPASSWORD', '.*?'\)",
            "DB_PASSWORD = os.getenv('PGPASSWORD')",
            content,
        )

        postgres_file.write_text(content)
        print("✅ Исправлен database/connections/postgres.py")

    # 2. Создаем alembic.ini.example без паролей
    alembic_file = Path("alembic.ini")
    alembic_example = Path("alembic.ini.example")

    if alembic_file.exists():
        content = alembic_file.read_text()

        # Заменяем строку подключения на шаблон
        content = re.sub(
            r"sqlalchemy\.url = postgresql://.*",
            "sqlalchemy.url = postgresql://%(DB_USER)s:%(DB_PASSWORD)s@%(DB_HOST)s:%(DB_PORT)s/%(DB_NAME)s",
            content,
        )

        alembic_example.write_text(content)
        print("✅ Создан alembic.ini.example")

        # Обновляем alembic.ini для использования переменных окружения
        alembic_env = """# Конфигурация Alembic с переменными окружения
[alembic]
script_location = database/migrations
prepend_sys_path = .
version_path_separator = os
file_template = %%(rev)s_%%(slug)s

[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -l 120

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S

# Database URL will be loaded from environment in env.py
sqlalchemy.url = driver://user:pass@localhost/dbname
"""
        alembic_file.write_text(alembic_env)
        print("✅ Обновлен alembic.ini")

    # 3. Обновляем database/migrations/env.py для использования переменных окружения
    env_file = Path("database/migrations/env.py")
    if env_file.exists():
        content = env_file.read_text()

        # Проверяем, есть ли уже импорт для получения URL
        if "from database.connections import get_database_url" not in content:
            # Добавляем в начало после импортов
            import_section = """from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Добавляем импорт для получения URL из переменных окружения
import os
from database.connections import get_database_url
"""
            content = content.replace(
                "from logging.config import fileConfig\n\nfrom sqlalchemy import engine_from_config\nfrom sqlalchemy import pool\n\nfrom alembic import context",
                import_section,
            )

            # Заменяем получение URL
            content = re.sub(
                r"config\.set_main_option\(\"sqlalchemy\.url\", get_database_url\(\)\)",
                'config.set_main_option("sqlalchemy.url", get_database_url())',
                content,
            )

            env_file.write_text(content)
            print("✅ Обновлен database/migrations/env.py")

    # 4. Исправляем config/system.yaml
    system_config = Path("config/system.yaml")
    if system_config.exists():
        content = system_config.read_text()

        # Исправляем порт
        content = content.replace("port: 5432", "port: 5555")

        # Исправляем пользователя
        content = content.replace("user: postgres", "user: obertruper")

        # Убираем пароль если есть
        content = re.sub(r"password:.*", "password: ${PGPASSWORD}", content)

        system_config.write_text(content)
        print("✅ Исправлен config/system.yaml")

    # 5. Исправляем скрипты синхронизации
    for script_path in [
        "scripts/sync_to_linux_server.sh",
        "scripts/sync_via_tailscale.sh",
    ]:
        script_file = Path(script_path)
        if script_file.exists():
            content = script_file.read_text()

            # Заменяем жестко зашитый пароль на переменную окружения
            content = re.sub(
                r'PASSWORD=".*?"', 'PASSWORD="${SYNC_PASSWORD:-}"', content
            )

            script_file.write_text(content)
            print(f"✅ Исправлен {script_path}")

    # 6. Исправляем scripts/visualize_db.py
    visualize_file = Path("scripts/visualize_db.py")
    if visualize_file.exists():
        content = visualize_file.read_text()

        # Заменяем жестко зашитые параметры на переменные окружения
        new_conn_params = """conn_params = {
    'dbname': os.getenv('PGDATABASE', 'bot_trading_v3'),
    'user': os.getenv('PGUSER', 'obertruper'),
    'port': os.getenv('PGPORT', '5555'),
    'password': os.getenv('PGPASSWORD'),
    'host': os.getenv('PGHOST', 'localhost')
}"""

        content = re.sub(
            r"conn_params = \{[^}]+\}", new_conn_params, content, flags=re.DOTALL
        )

        # Добавляем импорт os если его нет
        if "import os" not in content:
            content = "import os\n" + content

        visualize_file.write_text(content)
        print("✅ Исправлен scripts/visualize_db.py")

    # 7. Создаем или обновляем .env.example
    env_example = Path(".env.example")
    if not env_example.exists():
        env_content = """# PostgreSQL Configuration
PGHOST=localhost
PGPORT=5555
PGUSER=obertruper
PGPASSWORD=your_secure_password_here
PGDATABASE=bot_trading_v3

# Exchange API Keys
BYBIT_API_KEY=your_bybit_api_key
BYBIT_API_SECRET=your_bybit_api_secret

BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret

OKX_API_KEY=your_okx_api_key
OKX_API_SECRET=your_okx_api_secret
OKX_PASSPHRASE=your_okx_passphrase

BITGET_API_KEY=your_bitget_api_key
BITGET_API_SECRET=your_bitget_api_secret
BITGET_PASSPHRASE=your_bitget_passphrase

GATE_API_KEY=your_gate_api_key
GATE_API_SECRET=your_gate_api_secret

KUCOIN_API_KEY=your_kucoin_api_key
KUCOIN_API_SECRET=your_kucoin_api_secret
KUCOIN_PASSPHRASE=your_kucoin_passphrase

HUOBI_API_KEY=your_huobi_api_key
HUOBI_API_SECRET=your_huobi_api_secret

# AI Services
CLAUDE_API_KEY=your_claude_api_key
OPENAI_API_KEY=your_openai_api_key

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# GitHub
GITHUB_TOKEN=your_github_token

# System Settings
LOG_LEVEL=INFO
ENVIRONMENT=development
DEFAULT_LEVERAGE=1
MAX_POSITION_SIZE=1000
RISK_LIMIT_PERCENTAGE=2

# Redis (optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Sync Password (for scripts)
SYNC_PASSWORD=your_sync_password
"""
        env_example.write_text(env_content)
        print("✅ Создан .env.example")

    print("\n✅ Конфигурация БД исправлена!")
    print("\n📝 Следующие шаги:")
    print("1. Скопируйте .env.example в .env: cp .env.example .env")
    print("2. Заполните реальные значения в .env файле")
    print("3. Запустите миграции: alembic upgrade head")
    print("\n⚠️  ВАЖНО: Никогда не коммитьте .env файл в git!")


if __name__ == "__main__":
    fix_db_config()
