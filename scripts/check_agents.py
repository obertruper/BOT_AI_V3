#!/usr/bin/env python3
"""
Скрипт для проверки конфигурации Claude Code агентов
"""

from pathlib import Path
from typing import Dict

import yaml


def check_agent_file(file_path: Path) -> Dict:
    """Проверка файла агента на корректность."""
    errors = []
    warnings = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Проверка наличия YAML frontmatter
        if not content.startswith("---"):
            errors.append("Файл должен начинаться с '---' (YAML frontmatter)")
            return {"valid": False, "errors": errors, "warnings": warnings}

        # Извлечение YAML
        parts = content.split("---", 2)
        if len(parts) < 3:
            errors.append("Неверный формат YAML frontmatter")
            return {"valid": False, "errors": errors, "warnings": warnings}

        try:
            metadata = yaml.safe_load(parts[1])
        except yaml.YAMLError as e:
            errors.append(f"Ошибка парсинга YAML: {e}")
            return {"valid": False, "errors": errors, "warnings": warnings}

        # Проверка обязательных полей
        required_fields = ["name", "description"]
        for field in required_fields:
            if field not in metadata:
                errors.append(f"Отсутствует обязательное поле: {field}")

        # Проверка имени
        if "name" in metadata:
            name = metadata["name"]
            if not isinstance(name, str):
                errors.append("Поле 'name' должно быть строкой")
            elif " " in name:
                errors.append("Поле 'name' не должно содержать пробелы")
            elif name != name.lower():
                warnings.append("Рекомендуется использовать lowercase для 'name'")

        # Проверка описания
        if "description" in metadata:
            desc = metadata["description"]
            if not isinstance(desc, str):
                errors.append("Поле 'description' должно быть строкой")
            elif len(desc) < 10:
                warnings.append("Описание слишком короткое")

        # Проверка tools
        if "tools" in metadata:
            tools = metadata["tools"]
            if tools != "all" and not isinstance(tools, list):
                errors.append("Поле 'tools' должно быть 'all' или списком")

        # Проверка содержимого
        body = parts[2].strip()
        if len(body) < 100:
            warnings.append("Тело агента слишком короткое")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "metadata": metadata if len(errors) == 0 else None,
        }

    except Exception as e:
        return {"valid": False, "errors": [f"Ошибка чтения файла: {e}"], "warnings": []}


def main():
    """Основная функция проверки."""
    agents_dir = Path(".claude/agents")

    if not agents_dir.exists():
        print("❌ Директория .claude/agents не найдена!")
        return

    print("🔍 Проверка Claude Code агентов...\n")

    agent_files = list(agents_dir.glob("*.md"))
    agent_files = [f for f in agent_files if f.name != "README.md"]

    if not agent_files:
        print("❌ Не найдено файлов агентов!")
        return

    print(f"Найдено {len(agent_files)} агентов:\n")

    valid_agents = []
    invalid_agents = []

    for agent_file in sorted(agent_files):
        result = check_agent_file(agent_file)

        if result["valid"]:
            valid_agents.append(agent_file)
            print(f"✅ {agent_file.name}")
            if result["warnings"]:
                for warning in result["warnings"]:
                    print(f"   ⚠️  {warning}")
        else:
            invalid_agents.append(agent_file)
            print(f"❌ {agent_file.name}")
            for error in result["errors"]:
                print(f"   ❗ {error}")

    print("\n📊 Результаты:")
    print(f"   ✅ Валидных агентов: {len(valid_agents)}")
    print(f"   ❌ Невалидных агентов: {len(invalid_agents)}")

    # Проверка глобальных агентов
    global_agents_dir = Path.home() / ".claude" / "agents"
    if global_agents_dir.exists():
        global_count = len(list(global_agents_dir.glob("*.md")))
        print(f"\n📁 Глобальные агенты: {global_count}")
    else:
        print(f"\n📁 Глобальная директория агентов не существует: {global_agents_dir}")
        print("   Для установки глобально выполните:")
        print(f"   cp -r .claude/agents {global_agents_dir}")

    # Информация об использовании
    print("\n💡 Использование агентов:")
    print("   1. В интерактивном режиме Claude Code используйте команду: /agents")
    print("   2. Агенты активируются автоматически для подходящих задач")
    print("   3. Можно явно вызвать через Task tool")

    # Проверка команд
    commands_dir = Path(".claude/commands")
    if commands_dir.exists():
        command_files = list(commands_dir.glob("*.md"))
        print(f"\n🎯 Также найдено {len(command_files)} slash-команд")


if __name__ == "__main__":
    main()
