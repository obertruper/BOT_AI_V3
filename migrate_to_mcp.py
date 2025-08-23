#!/usr/bin/env python3
"""
Скрипт миграции кода с прямых вызовов AsyncPGPool на MCP postgres tools
Автоматически находит и предлагает замены
"""

import os
import re
from datetime import datetime


def find_asyncpgpool_usage() -> list[tuple[str, int, str]]:
    """Найти все использования AsyncPGPool в проекте"""

    usage_list = []
    patterns = [
        r"AsyncPGPool\.(fetch|fetchrow|fetchval|execute)",
        r"from database\.connections\.postgres import AsyncPGPool",
        r"import AsyncPGPool",
    ]

    # Исключаем некоторые директории
    exclude_dirs = {".git", "venv", "__pycache__", "node_modules", ".idea"}

    for root, dirs, files in os.walk("."):
        # Убираем исключенные директории
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, encoding="utf-8") as f:
                        content = f.read()
                        lines = content.split("\n")

                        for i, line in enumerate(lines, 1):
                            for pattern in patterns:
                                if re.search(pattern, line):
                                    usage_list.append((filepath, i, line.strip()))
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")

    return usage_list


def generate_mcp_wrapper():
    """Генерация wrapper файла для MCP"""

    wrapper_code = '''#!/usr/bin/env python3
"""
MCP Database Wrapper - замена AsyncPGPool на MCP postgres tools
Автоматически сгенерировано migrate_to_mcp.py
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio

# Эмуляция MCP tools для демонстрации
# В production здесь будут реальные MCP вызовы через Claude Code API

class MCPDatabaseWrapper:
    """
    Wrapper для MCP postgres tools с интерфейсом AsyncPGPool
    """

    def __init__(self):
        self.host = "localhost"
        self.port = 5555
        self.database = "bot_trading_v3"
        self.user = "obertruper"
        # Password должен быть в переменных окружения
        self.password = os.getenv("PGPASSWORD", "your-password-here")  # Заменено для безопасности

    async def connect(self):
        """Подключение через MCP (вызывается автоматически)"""
        # mcp__postgres__connect_db(
        #     host=self.host,
        #     port=self.port,
        #     database=self.database,
        #     user=self.user,
        #     password=self.password
        # )
        pass

    async def fetch(self, query: str, *params) -> List[Dict[str, Any]]:
        """
        SELECT запрос через MCP
        Заменяет: AsyncPGPool.fetch()
        """
        # В production:
        # result = await mcp__postgres__query(sql=query, params=list(params))
        # return result

        # Временная заглушка - используем оригинальный AsyncPGPool
        from database.connections.postgres import AsyncPGPool as OriginalPool
        return await OriginalPool.fetch(query, *params)

    async def fetchrow(self, query: str, *params) -> Optional[Dict[str, Any]]:
        """
        SELECT одной строки через MCP
        Заменяет: AsyncPGPool.fetchrow()
        """
        rows = await self.fetch(query, *params)
        return rows[0] if rows else None

    async def fetchval(self, query: str, *params) -> Any:
        """
        SELECT одного значения через MCP
        Заменяет: AsyncPGPool.fetchval()
        """
        row = await self.fetchrow(query, *params)
        if row:
            return list(row.values())[0]
        return None

    async def execute(self, query: str, *params) -> str:
        """
        INSERT/UPDATE/DELETE через MCP
        Заменяет: AsyncPGPool.execute()
        """
        # В production:
        # result = await mcp__postgres__execute(sql=query, params=list(params))
        # return result

        # Временная заглушка
        from database.connections.postgres import AsyncPGPool as OriginalPool
        return await OriginalPool.execute(query, *params)

    async def executemany(self, query: str, params_list: List[tuple]) -> str:
        """
        Множественное выполнение через MCP
        Заменяет: AsyncPGPool.executemany()
        """
        # Выполняем батчами через MCP
        for params in params_list:
            await self.execute(query, *params)
        return f"EXECUTED {len(params_list)} queries"

    # Дополнительные MCP-специфичные методы

    async def list_tables(self, schema: str = "public") -> List[str]:
        """Получить список таблиц через MCP"""
        # return await mcp__postgres__list_tables(schema=schema)
        query = """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = $1
        """
        rows = await self.fetch(query, schema)
        return [row['tablename'] for row in rows]

    async def describe_table(self, table: str, schema: str = "public") -> Dict:
        """Получить структуру таблицы через MCP"""
        # return await mcp__postgres__describe_table(table=table, schema=schema)
        query = """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = $1 AND table_name = $2
            ORDER BY ordinal_position
        """
        rows = await self.fetch(query, schema, table)
        return {"columns": rows}

# Создаем глобальный экземпляр
_mcp_wrapper = MCPDatabaseWrapper()

class AsyncPGPool:
    """
    Drop-in замена для оригинального AsyncPGPool
    Все вызовы перенаправляются на MCP wrapper
    """

    @staticmethod
    async def fetch(query: str, *params):
        return await _mcp_wrapper.fetch(query, *params)

    @staticmethod
    async def fetchrow(query: str, *params):
        return await _mcp_wrapper.fetchrow(query, *params)

    @staticmethod
    async def fetchval(query: str, *params):
        return await _mcp_wrapper.fetchval(query, *params)

    @staticmethod
    async def execute(query: str, *params):
        return await _mcp_wrapper.execute(query, *params)

    @staticmethod
    async def executemany(query: str, params_list: List[tuple]):
        return await _mcp_wrapper.executemany(query, params_list)

    # Новые MCP методы
    @staticmethod
    async def list_tables(schema: str = "public"):
        return await _mcp_wrapper.list_tables(schema)

    @staticmethod
    async def describe_table(table: str, schema: str = "public"):
        return await _mcp_wrapper.describe_table(table, schema)

# Экспорт для обратной совместимости
__all__ = ['AsyncPGPool', 'MCPDatabaseWrapper']
'''

    # Создаем директорию если не существует
    os.makedirs("utils/mcp", exist_ok=True)

    # Записываем wrapper
    wrapper_path = "utils/mcp/database_wrapper.py"
    with open(wrapper_path, "w", encoding="utf-8") as f:
        f.write(wrapper_code)

    print(f"✅ Создан MCP wrapper: {wrapper_path}")

    # Создаем __init__.py
    init_path = "utils/mcp/__init__.py"
    with open(init_path, "w", encoding="utf-8") as f:
        f.write(
            'from .database_wrapper import AsyncPGPool, MCPDatabaseWrapper\n\n__all__ = ["AsyncPGPool", "MCPDatabaseWrapper"]\n'
        )

    return wrapper_path


def create_migration_script(usage_list: list[tuple[str, int, str]]):
    """Создание скрипта для автоматической миграции"""

    migration_script = '''#!/usr/bin/env python3
"""
Автоматическая миграция на MCP
Сгенерировано: {timestamp}
"""

import os
import re

def migrate_file(filepath: str):
    """Мигрировать один файл на MCP"""

    with open(filepath, 'r') as f:
        content = f.read()

    # Замена импортов
    content = re.sub(
        r'from database\\.connections\\.postgres import AsyncPGPool',
        'from utils.mcp.database_wrapper import AsyncPGPool',
        content
    )

    # Создаем backup
    backup_path = filepath + '.backup'
    with open(backup_path, 'w') as f:
        f.write(content)

    # Записываем измененный файл
    with open(filepath, 'w') as f:
        f.write(content)

    print(f"✅ Мигрирован: {{filepath}}")
    print(f"   Backup: {{backup_path}}")

# Файлы для миграции
files_to_migrate = {files}

if __name__ == "__main__":
    print("🚀 Начало миграции на MCP...")

    for filepath in files_to_migrate:
        if os.path.exists(filepath):
            migrate_file(filepath)

    print("\\n✅ Миграция завершена!")
    print("⚠️  Не забудьте протестировать изменения!")
'''.format(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        files=list(set(filepath for filepath, _, _ in usage_list)),
    )

    script_path = "run_mcp_migration.py"
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(migration_script)

    os.chmod(script_path, 0o755)
    print(f"✅ Создан скрипт миграции: {script_path}")

    return script_path


def main():
    """Основная функция"""

    print("=" * 60)
    print("🔍 АНАЛИЗ ИСПОЛЬЗОВАНИЯ AsyncPGPool")
    print("=" * 60)

    # 1. Находим все использования
    usage_list = find_asyncpgpool_usage()

    if not usage_list:
        print("✅ AsyncPGPool не найден в коде")
        return

    print(f"\n📊 Найдено {len(usage_list)} использований AsyncPGPool:\n")

    # Группируем по файлам
    files_dict = {}
    for filepath, line_num, line in usage_list:
        if filepath not in files_dict:
            files_dict[filepath] = []
        files_dict[filepath].append((line_num, line))

    # Показываем результаты
    for filepath, occurrences in list(files_dict.items())[:10]:
        print(f"\n📄 {filepath}:")
        for line_num, line in occurrences[:3]:
            print(f"  L{line_num}: {line[:80]}...")

    if len(files_dict) > 10:
        print(f"\n... и еще {len(files_dict) - 10} файлов")

    # 2. Генерируем wrapper
    print("\n" + "=" * 60)
    print("🔧 СОЗДАНИЕ MCP WRAPPER")
    print("=" * 60)

    wrapper_path = generate_mcp_wrapper()

    # 3. Создаем скрипт миграции
    print("\n" + "=" * 60)
    print("📝 СОЗДАНИЕ СКРИПТА МИГРАЦИИ")
    print("=" * 60)

    script_path = create_migration_script(usage_list)

    # 4. Инструкции
    print("\n" + "=" * 60)
    print("📋 ИНСТРУКЦИИ ПО МИГРАЦИИ")
    print("=" * 60)

    print(
        """
Шаги для завершения миграции:

1. ✅ Проверьте созданный wrapper:
   cat utils/mcp/database_wrapper.py

2. 🧪 Протестируйте на одном файле:
   - Откройте любой файл из списка выше
   - Замените импорт:
     from database.connections.postgres import AsyncPGPool
     на:
     from utils.mcp.database_wrapper import AsyncPGPool
   - Запустите тесты

3. 🚀 Запустите автоматическую миграцию:
   python3 run_mcp_migration.py

4. 🔍 Проверьте результаты:
   - Запустите систему: python3 unified_launcher.py
   - Проверьте логи на ошибки
   - Убедитесь что MCP работает

5. 🎯 После успешной миграции:
   - Удалите backup файлы: rm **/*.backup
   - Закоммитьте изменения: git add -A && git commit -m "Migrate to MCP postgres"

⚠️  ВАЖНО: Сделайте backup перед миграцией!
   tar -czf backup_before_mcp.tar.gz *.py **/*.py
"""
    )

    # 5. Статистика
    print("\n" + "=" * 60)
    print("📊 СТАТИСТИКА")
    print("=" * 60)

    print(
        f"""
• Файлов для миграции: {len(files_dict)}
• Строк кода: {len(usage_list)}
• Wrapper создан: {wrapper_path}
• Скрипт миграции: {script_path}

Основные файлы:
"""
    )

    # Топ файлов по использованию
    sorted_files = sorted(files_dict.items(), key=lambda x: len(x[1]), reverse=True)
    for filepath, occurrences in sorted_files[:5]:
        print(f"  • {filepath}: {len(occurrences)} использований")


if __name__ == "__main__":
    main()
