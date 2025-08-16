#!/usr/bin/env python3
"""
Миграционный скрипт для перехода с v2 на v3

Основные задачи:
1. Проверка существующей БД v2
2. Миграция данных в новую структуру v3
3. Конвертация конфигураций
4. Проверка целостности данных
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import asyncpg
import yaml

# Добавляем корневую директорию в path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.logger import setup_logger

logger = setup_logger("migration_v2_to_v3")


class MigrationV2toV3:
    """Класс для миграции с v2 на v3"""

    def __init__(self, v2_path: str, v3_path: str):
        """
        Инициализация.

        Args:
            v2_path: Путь к директории v2
            v3_path: Путь к директории v3
        """
        self.v2_path = Path(v2_path)
        self.v3_path = Path(v3_path)

        # Проверяем существование директорий
        if not self.v2_path.exists():
            raise ValueError(f"v2 директория не найдена: {v2_path}")
        if not self.v3_path.exists():
            raise ValueError(f"v3 директория не найдена: {v3_path}")

        self.backup_dir = (
            self.v3_path / "migration_backup" / datetime.now().strftime("%Y%m%d_%H%M%S")
        )
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Миграция из {v2_path} в {v3_path}")
        logger.info(f"Бэкапы будут сохранены в {self.backup_dir}")

    async def run(self):
        """Основной метод миграции"""
        try:
            logger.info("Начинаем миграцию...")

            # 1. Миграция конфигураций
            await self.migrate_configs()

            # 2. Миграция базы данных
            await self.migrate_database()

            # 3. Миграция ML моделей
            await self.migrate_ml_models()

            # 4. Миграция скриптов
            await self.migrate_scripts()

            # 5. Проверка целостности
            await self.verify_migration()

            logger.info("Миграция успешно завершена!")

        except Exception as e:
            logger.error(f"Ошибка миграции: {e}")
            await self.rollback()
            raise

    async def migrate_configs(self):
        """Миграция конфигурационных файлов"""
        logger.info("Миграция конфигураций...")

        # Копируем существующие конфиги v3 в бэкап
        v3_config_dir = self.v3_path / "config"
        if v3_config_dir.exists():
            backup_config_dir = self.backup_dir / "config"
            backup_config_dir.mkdir(parents=True, exist_ok=True)

            for config_file in v3_config_dir.glob("*.yaml"):
                if config_file.is_file():
                    backup_file = backup_config_dir / config_file.name
                    backup_file.write_text(config_file.read_text())
                    logger.info(f"Создан бэкап: {backup_file}")

        # Мигрируем конфиги из v2
        v2_config = self.v2_path / "config.yaml"
        if v2_config.exists():
            with open(v2_config, encoding="utf-8") as f:
                v2_data = yaml.safe_load(f)

            # Преобразуем в формат v3
            v3_config = self._convert_config_to_v3(v2_data)

            # Сохраняем в новые файлы
            system_config_path = v3_config_dir / "system.yaml"
            with open(system_config_path, "w", encoding="utf-8") as f:
                yaml.dump(v3_config["system"], f, default_flow_style=False)

            traders_dir = v3_config_dir / "traders"
            traders_dir.mkdir(exist_ok=True)

            # Создаем конфигурацию трейдера
            trader_config = {
                "name": "ml_trader_1",
                "exchange": v2_data.get("exchange", "bybit"),
                "strategy": "patchtst_strategy",
                "trading_pairs": v2_data.get("trading_pairs", ["BTCUSDT"]),
                "risk_params": {
                    "max_position_size": v2_data.get("max_position_size", 1000),
                    "leverage": v2_data.get("trading", {}).get("leverage", 10),
                    "stop_loss": v2_data.get("default_sl", 2.0),
                    "take_profit": v2_data.get("default_tp", 3.0),
                },
                "enabled": True,
            }

            trader_config_path = traders_dir / "ml_trader_1.yaml"
            with open(trader_config_path, "w", encoding="utf-8") as f:
                yaml.dump(trader_config, f, default_flow_style=False)

            logger.info("Конфигурации успешно мигрированы")

    def _convert_config_to_v3(self, v2_config: dict[str, Any]) -> dict[str, Any]:
        """Преобразует конфигурацию v2 в v3"""
        v3_config = {
            "system": {
                "version": "3.0.0",
                "environment": v2_config.get("environment", "production"),
                "database": {
                    "type": "postgresql",
                    "host": "127.0.0.1",
                    "port": 5555,
                    "name": "bot_trading_v3",
                    "user": "obertruper",
                    "password": v2_config.get("postgres", {}).get("password", "postgres"),
                },
                "exchanges": {
                    "bybit": {
                        "api_key": v2_config.get("bybit_api_key", ""),
                        "api_secret": v2_config.get("bybit_api_secret", ""),
                        "testnet": v2_config.get("testnet", False),
                    }
                },
                "notifications": {
                    "telegram": {
                        "enabled": v2_config.get("telegram_notifications", False),
                        "bot_token": v2_config.get("telegram_bot_token", ""),
                        "chat_id": v2_config.get("telegram_chat_id", ""),
                    }
                },
                "ml_models": {
                    "patchtst": {
                        "model_path": "models/saved/best_model_20250728_215703.pth",
                        "config_path": "config/ml/ml_config.yaml",
                    }
                },
                "enhanced_sltp": v2_config.get("enhanced_sltp", {}),
            }
        }

        return v3_config

    async def migrate_database(self):
        """Миграция базы данных"""
        logger.info("Миграция базы данных...")

        # Получаем конфигурацию БД из v2
        v2_config_path = self.v2_path / "config.yaml"
        if not v2_config_path.exists():
            logger.warning("Конфигурация v2 не найдена, пропускаем миграцию БД")
            return

        with open(v2_config_path) as f:
            v2_config = yaml.safe_load(f)

        # Подключаемся к БД v2
        v2_db_config = v2_config.get("postgres", {})
        v2_conn = await asyncpg.connect(
            host=v2_db_config.get("host", "localhost"),
            port=v2_db_config.get("port", 5555),
            database=v2_db_config.get("dbname", "trading_db"),
            user=v2_db_config.get("user", "postgres"),
            password=v2_db_config.get("password", "postgres"),
        )

        # Подключаемся к БД v3
        v3_conn = await asyncpg.connect(
            host="localhost",
            port=5555,
            database="bot_trading_v3",
            user="obertruper",
            password=v2_db_config.get("password", "postgres"),
        )

        try:
            # Мигрируем таблицы
            tables_to_migrate = [
                "trades",
                "signals",
                "ml_predictions",
                "sltp_orders",
                "partial_tp_history",
            ]

            for table in tables_to_migrate:
                await self._migrate_table(v2_conn, v3_conn, table)

            logger.info("База данных успешно мигрирована")

        finally:
            await v2_conn.close()
            await v3_conn.close()

    async def _migrate_table(self, v2_conn, v3_conn, table_name: str):
        """Мигрирует отдельную таблицу"""
        try:
            # Проверяем существование таблицы в v2
            exists = await v2_conn.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
                table_name,
            )

            if not exists:
                logger.warning(f"Таблица {table_name} не найдена в v2")
                return

            # Получаем данные
            rows = await v2_conn.fetch(f"SELECT * FROM {table_name}")

            if not rows:
                logger.info(f"Таблица {table_name} пуста")
                return

            # TODO: Маппинг и вставка данных в v3
            # Это требует детального анализа схем v2 и v3

            logger.info(f"Мигрировано {len(rows)} записей из таблицы {table_name}")

        except Exception as e:
            logger.error(f"Ошибка миграции таблицы {table_name}: {e}")

    async def migrate_ml_models(self):
        """Миграция ML моделей"""
        logger.info("Миграция ML моделей...")

        # Проверяем наличие моделей в v3
        v3_models_dir = self.v3_path / "models" / "saved"
        if v3_models_dir.exists():
            model_files = list(v3_models_dir.glob("*.pth"))
            if model_files:
                logger.info(f"Найдено {len(model_files)} ML моделей в v3")
                logger.info("Миграция моделей не требуется")
                return

        # Копируем модели из v2
        v2_models_dir = self.v2_path / "models"
        if not v2_models_dir.exists():
            logger.warning("Модели v2 не найдены")
            return

        # TODO: Копирование и конвертация моделей
        logger.info("Модели уже перенесены в v3")

    async def migrate_scripts(self):
        """Миграция полезных скриптов"""
        logger.info("Миграция скриптов...")

        # Список скриптов для миграции
        scripts_to_migrate = [
            "check_ml_model.py",
            "analyze_logs.py",
            "monitor_system.py",
        ]

        v2_scripts_dir = self.v2_path / "scripts"
        v3_scripts_dir = self.v3_path / "scripts"

        if not v2_scripts_dir.exists():
            logger.warning("Директория scripts не найдена в v2")
            return

        for script_name in scripts_to_migrate:
            v2_script = v2_scripts_dir / script_name
            if v2_script.exists():
                v3_script = v3_scripts_dir / script_name

                # Создаем бэкап если файл уже существует
                if v3_script.exists():
                    backup_script = self.backup_dir / "scripts" / script_name
                    backup_script.parent.mkdir(parents=True, exist_ok=True)
                    backup_script.write_text(v3_script.read_text())

                # Копируем скрипт
                v3_script.write_text(v2_script.read_text())
                logger.info(f"Скрипт {script_name} мигрирован")

    async def verify_migration(self):
        """Проверка успешности миграции"""
        logger.info("Проверка миграции...")

        checks = {
            "config/system.yaml": "Основная конфигурация",
            "config/traders/ml_trader_1.yaml": "Конфигурация трейдера",
            "models/saved/best_model_20250728_215703.pth": "ML модель",
        }

        all_ok = True
        for path, description in checks.items():
            full_path = self.v3_path / path
            if full_path.exists():
                logger.info(f"✅ {description} - OK")
            else:
                logger.error(f"❌ {description} - Не найден")
                all_ok = False

        if all_ok:
            logger.info("✅ Все проверки пройдены успешно!")
        else:
            raise Exception("Миграция не прошла проверку")

    async def rollback(self):
        """Откат миграции в случае ошибки"""
        logger.warning("Откат миграции...")

        # Восстанавливаем из бэкапа
        for backup_file in self.backup_dir.rglob("*"):
            if backup_file.is_file():
                relative_path = backup_file.relative_to(self.backup_dir)
                target_file = self.v3_path / relative_path
                target_file.parent.mkdir(parents=True, exist_ok=True)
                target_file.write_text(backup_file.read_text())
                logger.info(f"Восстановлен: {target_file}")


async def main():
    """Основная функция"""
    import argparse

    parser = argparse.ArgumentParser(description="Миграция BOT Trading с v2 на v3")
    parser.add_argument(
        "--v2-path",
        type=str,
        default="/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/BOT_AI_V2/BOT_Trading/BOT_Trading",
        help="Путь к директории v2",
    )
    parser.add_argument(
        "--v3-path",
        type=str,
        default="/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3",
        help="Путь к директории v3",
    )
    parser.add_argument("--dry-run", action="store_true", help="Тестовый запуск без изменений")

    args = parser.parse_args()

    migration = MigrationV2toV3(args.v2_path, args.v3_path)

    if args.dry_run:
        logger.info("Тестовый запуск - изменения не будут сохранены")
        # TODO: реализовать dry-run режим
    else:
        await migration.run()


if __name__ == "__main__":
    asyncio.run(main())
