#!/usr/bin/env python3
"""
Тест подключения MCP серверов для BOT_AI_V3
Запускать после перезапуска Claude Code
"""

import json
from pathlib import Path


def check_mcp_config():
    """Проверка конфигурации MCP серверов"""
    config_path = Path("/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/.mcp.json")

    if not config_path.exists():
        print("❌ Файл .mcp.json не найден!")
        return False

    with open(config_path) as f:
        config = json.load(f)

    print("📋 Конфигурация MCP серверов:\n")

    servers = config.get("mcpServers", {})
    for name, server_config in servers.items():
        print(f"• {name}:")
        print(
            f"  Command: {server_config.get('command')} {' '.join(server_config.get('args', []))}"
        )
        if server_config.get("env"):
            print(f"  Environment: {list(server_config['env'].keys())}")
        print()

    return True


def check_npm_packages():
    """Проверка установленных npm пакетов"""
    package_json = Path("/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/package.json")

    if not package_json.exists():
        print("❌ package.json не найден!")
        return False

    with open(package_json) as f:
        package_data = json.load(f)

    print("📦 MCP пакеты в package.json:\n")

    deps = package_data.get("dependencies", {})
    mcp_packages = {k: v for k, v in deps.items() if "modelcontextprotocol" in k or "mcp" in k}

    for package, version in mcp_packages.items():
        print(f"• {package}: {version}")

    print()
    return True


def check_env_vars():
    """Проверка переменных окружения"""
    env_file = Path("/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/.env")

    if not env_file.exists():
        print("⚠️  .env файл не найден!")
        return False

    print("🔑 Переменные окружения для MCP:\n")

    required_vars = ["PGPORT", "PGUSER", "PGPASSWORD", "PGDATABASE", "GITHUB_TOKEN"]

    with open(env_file) as f:
        env_content = f.read()

    for var in required_vars:
        if f"{var}=" in env_content:
            print(f"✅ {var} - найден")
        else:
            print(f"❌ {var} - НЕ найден")

    print()
    return True


def check_directories():
    """Проверка необходимых директорий"""
    print("📁 Проверка директорий:\n")

    dirs_to_check = [
        "/home/obertruper/.claude/memory",
        "/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/node_modules",
        "/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/data/logs",
    ]

    all_exist = True
    for dir_path in dirs_to_check:
        path = Path(dir_path)
        if path.exists():
            print(f"✅ {dir_path}")
        else:
            print(f"❌ {dir_path} - НЕ существует")
            all_exist = False

    print()
    return all_exist


def main():
    """Главная функция тестирования"""
    print("🔧 BOT_AI_V3 - Тест MCP подключений\n")
    print("=" * 50)
    print()

    # Проверки
    config_ok = check_mcp_config()
    packages_ok = check_npm_packages()
    env_ok = check_env_vars()
    dirs_ok = check_directories()

    print("=" * 50)
    print("\n📊 Итоговый статус:\n")

    if all([config_ok, packages_ok, env_ok, dirs_ok]):
        print("✅ Все проверки пройдены успешно!")
        print("\n🚀 Рекомендации:")
        print("1. Перезапустите Claude Code для применения изменений")
        print("2. Проверьте статус через команду: claude-code mcp list")
        print("3. При ошибках проверьте логи в ~/.cache/claude-cli-nodejs/")
    else:
        print("❌ Обнаружены проблемы!")
        print("\n🔧 Необходимые действия:")
        if not packages_ok:
            print("1. Выполните: npm install")
        if not dirs_ok:
            print("2. Создайте недостающие директории")
        if not env_ok:
            print("3. Проверьте .env файл")

    print("\n📝 Документация: /mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/docs/MCP_STATUS.md")


if __name__ == "__main__":
    main()
