#!/usr/bin/env python3
"""
Скрипт для проверки конфигурации BOT_AI_V3

Использование:
    python scripts/check_config.py                    # Проверить всю конфигурацию
    python scripts/check_config.py --trader ml_01     # Проверить конкретного трейдера
    python scripts/check_config.py --validate         # Валидация без загрузки
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict

import yaml
from colorama import Fore, Style, init
from tabulate import tabulate

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config.config_manager import ConfigManager
from core.config.validation import ConfigValidator, ValidationLevel

init(autoreset=True)


class ConfigChecker:
    """Утилита для проверки конфигурации"""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.validator = ConfigValidator()

    async def check_all(self):
        """Проверка всей конфигурации"""
        print(
            f"\n{Fore.CYAN}=== Проверка конфигурации BOT_AI_V3 ==={Style.RESET_ALL}\n"
        )

        # Инициализация конфигурации
        try:
            await self.config_manager.initialize()
            print(f"{Fore.GREEN}✅ Конфигурация успешно загружена{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}❌ Ошибка загрузки конфигурации: {e}{Style.RESET_ALL}")
            return

        # Информация о конфигурации
        config_info = self.config_manager.get_config_info()
        if config_info:
            print(f"\n📁 Путь конфигурации: {config_info.path}")
            print(
                f"📅 Загружена: {config_info.loaded_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )

        # Системная конфигурация
        self._check_system_config()

        # База данных
        self._check_database_config()

        # Трейдеры
        await self._check_traders_config()

        # Валидация
        self._run_validation()

    def _check_system_config(self):
        """Проверка системной конфигурации"""
        print(f"\n{Fore.YELLOW}📋 Системная конфигурация:{Style.RESET_ALL}")

        system_config = self.config_manager.get_system_config()

        table_data = []
        table_data.append(["Название", system_config.get("name", "N/A")])
        table_data.append(["Версия", system_config.get("version", "N/A")])
        table_data.append(["Окружение", system_config.get("environment", "N/A")])

        limits = system_config.get("limits", {})
        table_data.append(["Макс. трейдеров", limits.get("max_traders", "N/A")])
        table_data.append(["Макс. сделок", limits.get("max_concurrent_trades", "N/A")])

        print(tabulate(table_data, tablefmt="grid"))

    def _check_database_config(self):
        """Проверка конфигурации БД"""
        print(f"\n{Fore.YELLOW}💾 Конфигурация базы данных:{Style.RESET_ALL}")

        db_config = self.config_manager.get_database_config()

        table_data = []
        table_data.append(["Тип", db_config.get("type", "N/A")])
        table_data.append(["Хост", db_config.get("host", "N/A")])
        table_data.append(["Порт", db_config.get("port", "N/A")])
        table_data.append(["База", db_config.get("name", "N/A")])
        table_data.append(["Пользователь", db_config.get("user", "N/A")])

        # Проверка переменных окружения
        env_status = "✅" if os.getenv("PGPASSWORD") else "❌"
        table_data.append(["Пароль (env)", f"{env_status} PGPASSWORD"])

        print(tabulate(table_data, tablefmt="grid"))

    async def _check_traders_config(self):
        """Проверка конфигураций трейдеров"""
        print(f"\n{Fore.YELLOW}👥 Конфигурации трейдеров:{Style.RESET_ALL}")

        trader_ids = self.config_manager.get_all_trader_ids()

        if not trader_ids:
            print(f"{Fore.RED}Трейдеры не найдены{Style.RESET_ALL}")
            return

        table_data = []
        headers = ["ID", "Имя", "Статус", "Биржа", "Пара", "Стратегия"]

        for trader_id in trader_ids:
            config = self.config_manager.get_trader_config(trader_id)

            status_icon = "✅" if config.get("enabled", False) else "⏸️"

            table_data.append(
                [
                    trader_id,
                    config.get("name", "N/A"),
                    status_icon,
                    config.get("exchange", "N/A"),
                    config.get("symbol", "N/A"),
                    config.get("strategy", "N/A"),
                ]
            )

        print(tabulate(table_data, headers=headers, tablefmt="grid"))

    def _run_validation(self):
        """Запуск валидации конфигурации"""
        print(f"\n{Fore.YELLOW}🔍 Валидация конфигурации:{Style.RESET_ALL}")

        config = self.config_manager.get_config()
        results = self.validator.validate_config(config)

        if not results:
            print(f"{Fore.GREEN}✅ Валидация пройдена успешно{Style.RESET_ALL}")
            return

        # Группировка по уровням
        errors = [r for r in results if r.level == ValidationLevel.ERROR]
        warnings = [r for r in results if r.level == ValidationLevel.WARNING]
        info = [r for r in results if r.level == ValidationLevel.INFO]

        # Вывод ошибок
        if errors:
            print(f"\n{Fore.RED}❌ Ошибки ({len(errors)}):{Style.RESET_ALL}")
            for result in errors:
                print(f"  - [{result.field}] {result.message}")
                if result.suggestion:
                    print(f"    💡 {result.suggestion}")

        # Вывод предупреждений
        if warnings:
            print(
                f"\n{Fore.YELLOW}⚠️ Предупреждения ({len(warnings)}):{Style.RESET_ALL}"
            )
            for result in warnings:
                print(f"  - [{result.field}] {result.message}")
                if result.suggestion:
                    print(f"    💡 {result.suggestion}")

        # Вывод информации
        if info:
            print(f"\n{Fore.BLUE}ℹ️ Информация ({len(info)}):{Style.RESET_ALL}")
            for result in info:
                print(f"  - [{result.field}] {result.message}")

    async def check_trader(self, trader_id: str):
        """Проверка конкретного трейдера"""
        print(f"\n{Fore.CYAN}=== Проверка трейдера: {trader_id} ==={Style.RESET_ALL}\n")

        # Инициализация
        await self.config_manager.initialize()

        # Получение конфигурации
        config = self.config_manager.get_trader_config(trader_id)

        if not config:
            print(f"{Fore.RED}❌ Трейдер '{trader_id}' не найден{Style.RESET_ALL}")
            return

        # Вывод конфигурации
        print(f"{Fore.YELLOW}📋 Конфигурация:{Style.RESET_ALL}")
        self._print_config(config)

        # Валидация
        print(f"\n{Fore.YELLOW}🔍 Валидация:{Style.RESET_ALL}")
        results = self.validator.validate_trader_config(trader_id, config)

        if not results:
            print(f"{Fore.GREEN}✅ Валидация пройдена успешно{Style.RESET_ALL}")
        else:
            for result in results:
                level_color = {
                    ValidationLevel.ERROR: Fore.RED,
                    ValidationLevel.WARNING: Fore.YELLOW,
                    ValidationLevel.INFO: Fore.BLUE,
                }.get(result.level, Fore.WHITE)

                print(
                    f"{level_color}[{result.level.value}] {result.field}: {result.message}{Style.RESET_ALL}"
                )
                if result.suggestion:
                    print(f"  💡 {result.suggestion}")

    def _print_config(self, config: Dict[str, Any], indent: int = 0):
        """Рекурсивный вывод конфигурации"""
        for key, value in config.items():
            prefix = "  " * indent
            if isinstance(value, dict):
                print(f"{prefix}{key}:")
                self._print_config(value, indent + 1)
            elif isinstance(value, list):
                print(f"{prefix}{key}:")
                for item in value:
                    if isinstance(item, dict):
                        self._print_config(item, indent + 1)
                    else:
                        print(f"{prefix}  - {item}")
            else:
                print(f"{prefix}{key}: {value}")

    async def validate_file(self, file_path: str):
        """Валидация отдельного файла конфигурации"""
        print(f"\n{Fore.CYAN}=== Валидация файла: {file_path} ==={Style.RESET_ALL}\n")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            print(f"{Fore.GREEN}✅ YAML синтаксис корректен{Style.RESET_ALL}")

            # Определяем тип конфигурации
            if "strategy" in config and "exchange" in config:
                # Это конфигурация трейдера
                trader_id = config.get("id", "unknown")
                results = self.validator.validate_trader_config(trader_id, config)
            else:
                # Общая конфигурация
                results = self.validator.validate_config(config)

            if not results:
                print(f"{Fore.GREEN}✅ Валидация пройдена успешно{Style.RESET_ALL}")
            else:
                for result in results:
                    level_color = {
                        ValidationLevel.ERROR: Fore.RED,
                        ValidationLevel.WARNING: Fore.YELLOW,
                        ValidationLevel.INFO: Fore.BLUE,
                    }.get(result.level, Fore.WHITE)

                    print(
                        f"{level_color}[{result.level.value}] {result.field}: {result.message}{Style.RESET_ALL}"
                    )
                    if result.suggestion:
                        print(f"  💡 {result.suggestion}")

        except yaml.YAMLError as e:
            print(f"{Fore.RED}❌ Ошибка синтаксиса YAML: {e}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}❌ Ошибка: {e}{Style.RESET_ALL}")


async def main():
    parser = argparse.ArgumentParser(description="Проверка конфигурации BOT_AI_V3")
    parser.add_argument("--trader", help="Проверить конкретного трейдера")
    parser.add_argument("--validate", help="Валидировать файл конфигурации")
    parser.add_argument(
        "--all", action="store_true", help="Проверить всю конфигурацию (по умолчанию)"
    )

    args = parser.parse_args()

    checker = ConfigChecker()

    if args.trader:
        await checker.check_trader(args.trader)
    elif args.validate:
        await checker.validate_file(args.validate)
    else:
        await checker.check_all()


if __name__ == "__main__":
    asyncio.run(main())
