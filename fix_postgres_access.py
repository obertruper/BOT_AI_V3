#!/usr/bin/env python3
"""
Скрипт для настройки доступа PostgreSQL для Docker контейнеров
"""

import os
import subprocess


def run_command(cmd, check=True):
    """Запуск команды с обработкой ошибок"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка команды: {cmd}")
        print(f"   Stderr: {e.stderr}")
        return None, e.stderr


def find_postgres_config():
    """Поиск файлов конфигурации PostgreSQL"""
    possible_paths = [
        "/etc/postgresql/*/main/pg_hba.conf",
        "/var/lib/postgresql/*/data/pg_hba.conf",
        "/usr/local/pgsql/data/pg_hba.conf",
        f"/home/{os.getenv('USER')}/postgres/data/pg_hba.conf",
        "/opt/homebrew/var/postgres/pg_hba.conf",  # macOS Homebrew
    ]

    for pattern in possible_paths:
        stdout, _ = run_command(f"ls {pattern}", check=False)
        if stdout:
            print(f"✅ Найден pg_hba.conf: {stdout}")
            return stdout.split("\n")[0]

    # Попробуем через PostgreSQL команды
    print("🔍 Поиск через PostgreSQL...")
    stdout, stderr = run_command(
        'psql -p 5555 -U obertruper -d bot_trading_v3 -c "SHOW config_file;" -t', check=False
    )
    if stdout:
        config_dir = os.path.dirname(stdout.strip())
        hba_file = os.path.join(config_dir, "pg_hba.conf")
        if os.path.exists(hba_file):
            return hba_file

    return None


def check_postgres_running():
    """Проверка что PostgreSQL запущен"""
    stdout, _ = run_command("ps aux | grep postgres | grep 5555", check=False)
    if "postgres" in stdout:
        print("✅ PostgreSQL работает на порту 5555")
        return True

    # Проверим через netstat/ss
    stdout, _ = run_command("ss -tlnp | grep :5555", check=False)
    if ":5555" in stdout:
        print("✅ Порт 5555 прослушивается")
        return True

    print("❌ PostgreSQL не найден на порту 5555")
    return False


def get_docker_networks():
    """Получение IP диапазонов Docker сетей"""
    networks = []

    # Стандартная Docker bridge сеть
    stdout, _ = run_command(
        "docker network inspect bridge --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'",
        check=False,
    )
    if stdout:
        networks.append(stdout.strip())

    # Наша кастомная сеть
    stdout, _ = run_command(
        "docker network inspect bot_ai_v3_bot_network --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'",
        check=False,
    )
    if stdout:
        networks.append(stdout.strip())

    return networks


def create_temp_hba_conf():
    """Создание временного файла pg_hba.conf с правильными настройками"""
    networks = get_docker_networks()

    hba_content = """# PostgreSQL Client Authentication Configuration File
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# "local" is for Unix domain socket connections only
local   all             all                                     trust
# IPv4 local connections:
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust

# Docker networks
"""

    for network in networks:
        hba_content += f"host    all             all             {network}               md5\n"

    # Добавляем конкретные IP для нашего случая
    hba_content += """
# Metabase container access
host    all             obertruper      172.21.0.0/16           trust
host    all             obertruper      172.17.0.0/16           trust
host    all             obertruper      172.18.0.0/16           trust
host    all             obertruper      172.19.0.0/16           trust
host    all             obertruper      172.20.0.0/16           trust
"""

    with open("temp_pg_hba.conf", "w") as f:
        f.write(hba_content)

    return "temp_pg_hba.conf"


def apply_postgres_settings():
    """Применение настроек PostgreSQL через SQL"""
    print("🔧 Попытка настроить PostgreSQL через SQL команды...")

    # Попробуем изменить listen_addresses
    commands = ["ALTER SYSTEM SET listen_addresses = '*';", "SELECT pg_reload_conf();"]

    for cmd in commands:
        stdout, stderr = run_command(
            f'psql -p 5555 -U obertruper -d bot_trading_v3 -c "{cmd}"', check=False
        )
        if stderr and "permission denied" not in stderr.lower():
            print(f"✅ Выполнено: {cmd}")
        else:
            print(f"⚠️ Не удалось: {cmd}")


def main():
    print("=" * 60)
    print("   НАСТРОЙКА ДОСТУПА POSTGRESQL ДЛЯ DOCKER")
    print("=" * 60)

    # 1. Проверяем что PostgreSQL работает
    if not check_postgres_running():
        print("❌ PostgreSQL не работает. Запустите сначала PostgreSQL")
        return False

    # 2. Получаем Docker сети
    networks = get_docker_networks()
    print(f"🌐 Docker сети: {networks}")

    # 3. Ищем файл pg_hba.conf
    hba_file = find_postgres_config()
    if not hba_file:
        print("❌ Файл pg_hba.conf не найден")
        print("💡 Попробуем другой подход...")
        apply_postgres_settings()
        return False

    print(f"📝 Найден файл: {hba_file}")

    # 4. Создаем временный файл
    temp_file = create_temp_hba_conf()
    print(f"📄 Создан временный файл: {temp_file}")

    # 5. Инструкции для пользователя
    print("\n" + "=" * 60)
    print("   ИНСТРУКЦИИ ДЛЯ НАСТРОЙКИ")
    print("=" * 60)
    print(
        f"""
1. Скопируйте временный файл:
   sudo cp {temp_file} {hba_file}

2. Перезапустите PostgreSQL:
   sudo systemctl reload postgresql
   # или
   sudo service postgresql reload

3. Проверьте подключение:
   docker exec bot_metabase psql -h 172.21.0.1 -p 5555 -U obertruper -d bot_trading_v3 -c "SELECT 1"
"""
    )

    return True


if __name__ == "__main__":
    success = main()
    if success:
        print("✅ Скрипт завершен успешно")
    else:
        print("❌ Требуются дополнительные действия")
