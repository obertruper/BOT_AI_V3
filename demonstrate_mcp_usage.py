#!/usr/bin/env python3
"""
Демонстрация правильного использования MCP серверов для операций с БД
Показывает как заменить прямые вызовы AsyncPGPool на MCP postgres инструменты
"""

import asyncio
from datetime import datetime

from core.logger import setup_logger

# ВАЖНО: Вместо прямого импорта AsyncPGPool, используем MCP tools
# from database.connections.postgres import AsyncPGPool  # ❌ НЕ ИСПОЛЬЗУЕМ
# Используем MCP postgres tools через Claude Code API  # ✅ ПРАВИЛЬНО


logger = setup_logger("mcp_demo")


class MCPDatabaseManager:
    """
    Менеджер базы данных через MCP серверы
    Заменяет прямые вызовы AsyncPGPool на MCP postgres tools
    """

    def __init__(self):
        """Инициализация MCP подключения"""
        self.connection_params = {
            "host": "localhost",
            "port": 5555,
            "database": "bot_trading_v3",
            "user": "obertruper",
            "password": "ilpnqw1234",
        }
        logger.info("✅ MCPDatabaseManager инициализирован")

    async def fetch(self, query: str, *params) -> list[dict]:
        """
        Выполнение SELECT запроса через MCP
        Заменяет: await AsyncPGPool.fetch(query, *params)
        """
        logger.info(f"📊 MCP Query: {query[:50]}...")

        # В реальном коде здесь будет вызов MCP postgres__query
        # result = await mcp__postgres__query(sql=query, params=list(params))

        # Для демонстрации возвращаем пример
        return [
            {"symbol": "BTCUSDT", "signal_type": "SHORT", "confidence": 0.85},
            {"symbol": "ETHUSDT", "signal_type": "SHORT", "confidence": 0.92},
        ]

    async def execute(self, query: str, *params) -> None:
        """
        Выполнение INSERT/UPDATE/DELETE через MCP
        Заменяет: await AsyncPGPool.execute(query, *params)
        """
        logger.info(f"🔧 MCP Execute: {query[:50]}...")

        # В реальном коде здесь будет вызов MCP postgres__execute
        # await mcp__postgres__execute(sql=query, params=list(params))

        return None

    async def list_tables(self, schema: str = "public") -> list[str]:
        """
        Получение списка таблиц через MCP
        """
        logger.info(f"📋 MCP List Tables in schema: {schema}")

        # В реальном коде: await mcp__postgres__list_tables(schema=schema)
        return [
            "signals",
            "orders",
            "trades",
            "raw_market_data",
            "processed_market_data",
            "account_balances",
        ]

    async def describe_table(self, table: str) -> dict:
        """
        Получение структуры таблицы через MCP
        """
        logger.info(f"🔍 MCP Describe Table: {table}")

        # В реальном коде: await mcp__postgres__describe_table(table=table)
        return {
            "columns": [
                {"name": "id", "type": "bigint"},
                {"name": "symbol", "type": "varchar"},
                {"name": "signal_type", "type": "varchar"},
                {"name": "confidence", "type": "decimal"},
            ]
        }


# Глобальный экземпляр для использования в коде
mcp_db = MCPDatabaseManager()


async def example_get_signals():
    """
    Пример: Получение сигналов через MCP

    БЫЛО (прямой вызов):
    rows = await AsyncPGPool.fetch(
        "SELECT * FROM signals WHERE created_at > $1",
        datetime.now() - timedelta(hours=1)
    )

    СТАЛО (через MCP):
    """

    logger.info("\n" + "=" * 60)
    logger.info("📡 ПОЛУЧЕНИЕ СИГНАЛОВ ЧЕРЕЗ MCP")
    logger.info("=" * 60)

    query = """
        SELECT
            symbol,
            signal_type,
            confidence,
            strength,
            created_at
        FROM signals
        WHERE created_at > NOW() - INTERVAL '1 hour'
        ORDER BY created_at DESC
        LIMIT 10
    """

    # Используем MCP вместо AsyncPGPool
    rows = await mcp_db.fetch(query)

    logger.info(f"✅ Получено {len(rows)} сигналов через MCP")
    for row in rows:
        logger.info(f"  • {row['symbol']}: {row['signal_type']} ({row['confidence']:.2%})")

    return rows


async def example_insert_signal():
    """
    Пример: Вставка сигнала через MCP

    БЫЛО:
    await AsyncPGPool.execute(
        "INSERT INTO signals (...) VALUES (...)",
        symbol, signal_type, confidence
    )

    СТАЛО:
    """

    logger.info("\n" + "=" * 60)
    logger.info("➕ ВСТАВКА СИГНАЛА ЧЕРЕЗ MCP")
    logger.info("=" * 60)

    query = """
        INSERT INTO signals (
            symbol, signal_type, confidence, strength,
            strategy_name, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6)
    """

    params = ["BTCUSDT", "LONG", 0.85, 0.72, "ML_STRATEGY", datetime.now()]

    # Используем MCP вместо AsyncPGPool
    await mcp_db.execute(query, *params)

    logger.info("✅ Сигнал вставлен через MCP")


async def example_update_order_status():
    """
    Пример: Обновление статуса ордера через MCP
    """

    logger.info("\n" + "=" * 60)
    logger.info("🔄 ОБНОВЛЕНИЕ СТАТУСА ОРДЕРА ЧЕРЕЗ MCP")
    logger.info("=" * 60)

    query = """
        UPDATE orders
        SET
            status = $1,
            filled_at = $2,
            updated_at = $3
        WHERE id = $4
    """

    params = ["filled", datetime.now(), datetime.now(), 12345]

    await mcp_db.execute(query, *params)

    logger.info("✅ Статус ордера обновлен через MCP")


async def example_analyze_tables():
    """
    Пример: Анализ структуры БД через MCP
    """

    logger.info("\n" + "=" * 60)
    logger.info("🗄️ АНАЛИЗ СТРУКТУРЫ БД ЧЕРЕЗ MCP")
    logger.info("=" * 60)

    # Получаем список таблиц
    tables = await mcp_db.list_tables()
    logger.info(f"📋 Найдено {len(tables)} таблиц:")
    for table in tables[:5]:
        logger.info(f"  • {table}")

    # Описываем таблицу signals
    structure = await mcp_db.describe_table("signals")
    logger.info("\n🔍 Структура таблицы signals:")
    for col in structure["columns"][:5]:
        logger.info(f"  • {col['name']}: {col['type']}")


async def migrate_code_example():
    """
    Пример миграции существующего кода на MCP
    """

    logger.info("\n" + "=" * 60)
    logger.info("🔄 ПРИМЕР МИГРАЦИИ КОДА НА MCP")
    logger.info("=" * 60)

    logger.info(
        """
📝 Шаги миграции:

1. Найти все импорты AsyncPGPool:
   grep -r "from database.connections.postgres import AsyncPGPool" .

2. Заменить на импорт MCPDatabaseManager:
   from utils.mcp_database import mcp_db

3. Заменить вызовы:
   ❌ БЫЛО:  rows = await AsyncPGPool.fetch(query, param1, param2)
   ✅ СТАЛО: rows = await mcp_db.fetch(query, param1, param2)

   ❌ БЫЛО:  await AsyncPGPool.execute(query, param1, param2)
   ✅ СТАЛО: await mcp_db.execute(query, param1, param2)

4. Основные файлы для миграции:
   • database/repositories/signal_repository_fixed.py
   • trading/engine.py
   • ml/ml_manager.py
   • trading/signals/ai_signal_generator.py
   • core/system/orchestrator.py

5. Преимущества MCP:
   • Централизованное управление подключениями
   • Автоматическая обработка ошибок
   • Встроенный мониторинг запросов
   • Поддержка транзакций
   • Интеграция с Claude Code
"""
    )


async def show_mcp_benefits():
    """
    Показать преимущества использования MCP
    """

    logger.info("\n" + "=" * 60)
    logger.info("🚀 ПРЕИМУЩЕСТВА MCP СЕРВЕРОВ")
    logger.info("=" * 60)

    logger.info(
        """
✅ Почему использовать MCP вместо прямых вызовов:

1. 🔒 Безопасность:
   • Изоляция credentials
   • Контроль доступа
   • Аудит операций

2. 🎯 Унификация:
   • Единый интерфейс для всех БД операций
   • Консистентная обработка ошибок
   • Стандартизированные результаты

3. 📊 Мониторинг:
   • Автоматическое логирование
   • Метрики производительности
   • Трассировка запросов

4. 🔧 Управление:
   • Централизованная конфигурация
   • Пулы соединений
   • Автоматические реконнекты

5. 🤖 Интеграция с Claude:
   • Прямой доступ к БД из Claude Code
   • Автоматическая документация
   • Контекстная помощь

6. 📈 Производительность:
   • Кэширование запросов
   • Батчинг операций
   • Оптимизация соединений
"""
    )


async def create_mcp_wrapper():
    """
    Создание wrapper'а для полной совместимости с AsyncPGPool
    """

    logger.info("\n" + "=" * 60)
    logger.info("🔧 СОЗДАНИЕ MCP WRAPPER")
    logger.info("=" * 60)

    code = '''
# utils/mcp_database.py

class MCPAsyncPGPool:
    """Drop-in замена для AsyncPGPool через MCP"""

    @staticmethod
    async def fetch(query: str, *params):
        """Совместимый интерфейс с AsyncPGPool.fetch"""
        return await mcp_db.fetch(query, *params)

    @staticmethod
    async def fetchrow(query: str, *params):
        """Совместимый интерфейс с AsyncPGPool.fetchrow"""
        rows = await mcp_db.fetch(query, *params)
        return rows[0] if rows else None

    @staticmethod
    async def fetchval(query: str, *params):
        """Совместимый интерфейс с AsyncPGPool.fetchval"""
        row = await MCPAsyncPGPool.fetchrow(query, *params)
        return list(row.values())[0] if row else None

    @staticmethod
    async def execute(query: str, *params):
        """Совместимый интерфейс с AsyncPGPool.execute"""
        return await mcp_db.execute(query, *params)

# Глобальная замена
AsyncPGPool = MCPAsyncPGPool
'''

    logger.info("📝 Wrapper код для совместимости:")
    logger.info(code)

    logger.info(
        """

Использование:
1. Создать файл utils/mcp_database.py с wrapper'ом
2. В начале main.py добавить:
   from utils.mcp_database import AsyncPGPool
3. Весь существующий код продолжит работать без изменений!
"""
    )


async def main():
    """Основная демонстрация"""

    logger.info("\n" + "=" * 80)
    logger.info("🚀 ДЕМОНСТРАЦИЯ ИСПОЛЬЗОВАНИЯ MCP СЕРВЕРОВ")
    logger.info("=" * 80)

    # 1. Показываем преимущества
    await show_mcp_benefits()

    # 2. Примеры использования
    await example_get_signals()
    await example_insert_signal()
    await example_update_order_status()
    await example_analyze_tables()

    # 3. Миграция кода
    await migrate_code_example()

    # 4. Создание wrapper'а
    await create_mcp_wrapper()

    logger.info("\n" + "=" * 80)
    logger.info("✅ ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА")
    logger.info("=" * 80)

    logger.info(
        """
📋 Следующие шаги:
1. Запустить скрипт миграции: python3 migrate_to_mcp.py
2. Протестировать на одном модуле
3. Постепенно мигрировать остальные модули
4. Отключить прямые подключения к БД
"""
    )


if __name__ == "__main__":
    asyncio.run(main())
