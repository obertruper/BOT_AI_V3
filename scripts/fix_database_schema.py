#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт исправления схемы базы данных
Добавляет недостающие колонки и исправляет проблемы совместимости
"""

import asyncio
import os
import sys
from datetime import datetime

# Добавляем корень проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connections.postgres import AsyncPGPool


class DatabaseSchemaFixer:
    """Исправление схемы базы данных"""

    def __init__(self):
        self.fixes_applied = []
        self.errors_found = []

    async def fix_signals_table(self):
        """Исправление таблицы signals"""
        print("\n📊 Исправление таблицы signals...")

        try:
            # Проверяем существование колонки side
            result = await AsyncPGPool.fetch(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'signals' AND column_name = 'side'
            """
            )

            if not result:
                print("   🔧 Добавление колонки 'side' в таблицу signals...")

                # Добавляем колонку side
                await AsyncPGPool.execute(
                    """
                    ALTER TABLE signals
                    ADD COLUMN side VARCHAR(10)
                """
                )

                # Обновляем существующие записи на основе signal_type
                await AsyncPGPool.execute(
                    """
                    UPDATE signals
                    SET side = CASE
                        WHEN signal_type = 'LONG' THEN 'buy'
                        WHEN signal_type = 'SHORT' THEN 'sell'
                        WHEN signal_type = 'CLOSE_LONG' THEN 'sell'
                        WHEN signal_type = 'CLOSE_SHORT' THEN 'buy'
                        ELSE 'neutral'
                    END
                """
                )

                print("   ✅ Колонка 'side' добавлена и заполнена")
                self.fixes_applied.append("Added 'side' column to signals table")
            else:
                print("   ✅ Колонка 'side' уже существует")

            # Проверяем и добавляем другие недостающие колонки
            await self._add_missing_columns()

        except Exception as e:
            print(f"   ❌ Ошибка исправления таблицы signals: {e}")
            self.errors_found.append(f"Signals table fix error: {e}")

    async def _add_missing_columns(self):
        """Добавление недостающих колонок"""
        print("   🔧 Проверка недостающих колонок...")

        # Список колонок для проверки
        columns_to_check = [
            ("updated_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
            ("metadata", "JSONB"),
        ]

        for column_name, column_definition in columns_to_check:
            try:
                result = await AsyncPGPool.fetch(
                    f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'signals' AND column_name = '{column_name}'
                """
                )

                if not result:
                    print(f"      🔧 Добавление колонки '{column_name}'...")
                    await AsyncPGPool.execute(
                        f"""
                        ALTER TABLE signals
                        ADD COLUMN {column_name} {column_definition}
                    """
                    )
                    print(f"      ✅ Колонка '{column_name}' добавлена")
                    self.fixes_applied.append(
                        f"Added '{column_name}' column to signals table"
                    )
                else:
                    print(f"      ✅ Колонка '{column_name}' уже существует")

            except Exception as e:
                print(f"      ❌ Ошибка добавления колонки '{column_name}': {e}")
                self.errors_found.append(f"Column '{column_name}' add error: {e}")

    async def fix_signal_processing(self):
        """Исправление обработки сигналов"""
        print("\n📡 Исправление обработки сигналов...")

        try:
            # Проверяем и исправляем проблемные записи
            result = await AsyncPGPool.fetch(
                """
                SELECT COUNT(*) as count
                FROM signals
                WHERE side IS NULL OR side = ''
            """
            )

            null_side_count = result[0]["count"] if result else 0

            if null_side_count > 0:
                print(f"   🔧 Исправление {null_side_count} записей с пустым side...")

                await AsyncPGPool.execute(
                    """
                    UPDATE signals
                    SET side = CASE
                        WHEN signal_type = 'LONG' THEN 'buy'
                        WHEN signal_type = 'SHORT' THEN 'sell'
                        WHEN signal_type = 'CLOSE_LONG' THEN 'sell'
                        WHEN signal_type = 'CLOSE_SHORT' THEN 'buy'
                        ELSE 'neutral'
                    END
                    WHERE side IS NULL OR side = ''
                """
                )

                print("   ✅ Записи исправлены")
                self.fixes_applied.append(
                    f"Fixed {null_side_count} signals with null side"
                )
            else:
                print("   ✅ Все записи имеют корректный side")

        except Exception as e:
            print(f"   ❌ Ошибка исправления обработки сигналов: {e}")
            self.errors_found.append(f"Signal processing fix error: {e}")

    async def create_indexes(self):
        """Создание индексов для оптимизации"""
        print("\n📈 Создание индексов...")

        try:
            # Список индексов для создания
            indexes = [
                ("ix_signals_symbol_side", "signals", "symbol, side"),
                ("ix_signals_created_at", "signals", "created_at"),
                ("ix_signals_signal_type", "signals", "signal_type"),
            ]

            for index_name, table_name, columns in indexes:
                try:
                    # Проверяем существование индекса
                    result = await AsyncPGPool.fetch(
                        f"""
                        SELECT indexname
                        FROM pg_indexes
                        WHERE indexname = '{index_name}'
                    """
                    )

                    if not result:
                        print(f"   🔧 Создание индекса '{index_name}'...")
                        await AsyncPGPool.execute(
                            f"""
                            CREATE INDEX {index_name} ON {table_name} ({columns})
                        """
                        )
                        print(f"   ✅ Индекс '{index_name}' создан")
                        self.fixes_applied.append(f"Created index {index_name}")
                    else:
                        print(f"   ✅ Индекс '{index_name}' уже существует")

                except Exception as e:
                    print(f"   ❌ Ошибка создания индекса '{index_name}': {e}")
                    self.errors_found.append(
                        f"Index '{index_name}' creation error: {e}"
                    )

        except Exception as e:
            print(f"   ❌ Ошибка создания индексов: {e}")
            self.errors_found.append(f"Indexes creation error: {e}")

    async def verify_fixes(self):
        """Проверка примененных исправлений"""
        print("\n🔍 Проверка примененных исправлений...")

        try:
            # Проверяем структуру таблицы signals
            result = await AsyncPGPool.fetch(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'signals'
                ORDER BY ordinal_position
            """
            )

            print("   📊 Обновленная структура таблицы signals:")
            for row in result:
                print(
                    f"      {row['column_name']}: {row['data_type']} ({'NULL' if row['is_nullable'] == 'YES' else 'NOT NULL'})"
                )

            # Проверяем количество записей
            result = await AsyncPGPool.fetch("SELECT COUNT(*) as count FROM signals")
            signals_count = result[0]["count"] if result else 0

            result = await AsyncPGPool.fetch(
                "SELECT COUNT(*) as count FROM signals WHERE side IS NOT NULL"
            )
            valid_side_count = result[0]["count"] if result else 0

            print("   📈 Статистика:")
            print(f"      Всего сигналов: {signals_count}")
            print(f"      С корректным side: {valid_side_count}")
            print(
                f"      Процент корректных: {(valid_side_count / signals_count * 100):.1f}%"
                if signals_count > 0
                else "N/A"
            )

            if valid_side_count == signals_count:
                print("   ✅ Все сигналы имеют корректный side")
                self.fixes_applied.append("All signals have valid side values")
            else:
                print(
                    f"   ⚠️ {signals_count - valid_side_count} сигналов требуют исправления"
                )
                self.errors_found.append(
                    f"{signals_count - valid_side_count} signals need side fix"
                )

        except Exception as e:
            print(f"   ❌ Ошибка проверки исправлений: {e}")
            self.errors_found.append(f"Verification error: {e}")

    async def generate_report(self):
        """Генерация отчета"""
        print("\n📊 Отчет об исправлениях схемы БД")
        print("=" * 50)

        report = {
            "timestamp": datetime.now().isoformat(),
            "fixes_applied": self.fixes_applied,
            "errors_found": self.errors_found,
            "fixes_count": len(self.fixes_applied),
            "errors_count": len(self.errors_found),
        }

        # Сохраняем отчет
        report_file = (
            f"logs/schema_fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_file, "w", encoding="utf-8") as f:
            import json

            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        print(f"📄 Отчет сохранен: {report_file}")

        # Выводим статистику
        print("\n📈 Статистика исправлений:")
        print(f"   ✅ Применено исправлений: {report['fixes_count']}")
        print(f"   ❌ Найдено ошибок: {report['errors_count']}")

        if self.fixes_applied:
            print("\n✅ Примененные исправления:")
            for fix in self.fixes_applied:
                print(f"   • {fix}")

        if self.errors_found:
            print("\n❌ Найденные проблемы:")
            for error in self.errors_found:
                print(f"   • {error}")

        # Рекомендации
        if self.errors_found:
            print("\n🔧 РЕКОМЕНДАЦИИ:")
            print("   1. Проверьте логи на наличие ошибок")
            print("   2. Перезапустите систему торговли")
            print(
                "   3. Запустите мониторинг: python scripts/monitor_system_enhanced.py"
            )
        else:
            print("\n🎉 Все проблемы исправлены! Система готова к работе.")

    async def run_all_fixes(self):
        """Запуск всех исправлений"""
        print("🚀 Исправление схемы базы данных")
        print("=" * 50)

        try:
            await self.fix_signals_table()
            await self.fix_signal_processing()
            await self.create_indexes()
            await self.verify_fixes()
            await self.generate_report()

            print("\n✅ Исправление схемы завершено!")

        except Exception as e:
            print(f"\n❌ Критическая ошибка: {e}")
            self.errors_found.append(f"Critical error: {e}")
            await self.generate_report()


async def main():
    """Основная функция"""
    fixer = DatabaseSchemaFixer()
    await fixer.run_all_fixes()


if __name__ == "__main__":
    asyncio.run(main())
