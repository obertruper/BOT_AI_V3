#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт проверки готовности BOT Trading v3 к запуску
"""

import asyncio
import importlib.util
import os
import sys
from pathlib import Path

import asyncpg
import yaml

# Добавляем корневую директорию
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.logger import setup_logger

logger = setup_logger("v3_readiness_check")


class ReadinessChecker:
    """Класс для проверки готовности v3"""

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.checks_passed = 0
        self.checks_failed = 0
        self.warnings = []

    async def run(self) -> bool:
        """
        Запускает все проверки.

        Returns:
            True если система готова к запуску
        """
        logger.info("Начинаем проверку готовности BOT Trading v3...")
        logger.info("=" * 60)

        # 1. Проверка структуры директорий
        self._check_directory_structure()

        # 2. Проверка конфигураций
        await self._check_configurations()

        # 3. Проверка зависимостей
        self._check_dependencies()

        # 4. Проверка базы данных
        await self._check_database()

        # 5. Проверка ML моделей
        self._check_ml_models()

        # 6. Проверка основных компонентов
        await self._check_core_components()

        # 7. Проверка API и WebSocket
        await self._check_api_endpoints()

        # Итоги
        logger.info("=" * 60)
        logger.info(f"Проверок пройдено: {self.checks_passed}")
        logger.info(f"Проверок провалено: {self.checks_failed}")
        logger.info(f"Предупреждений: {len(self.warnings)}")

        if self.warnings:
            logger.warning("Предупреждения:")
            for warning in self.warnings:
                logger.warning(f"  - {warning}")

        if self.checks_failed == 0:
            logger.info("✅ Система готова к запуску!")
            return True
        else:
            logger.error("❌ Система не готова к запуску. Исправьте ошибки.")
            return False

    def _check_directory_structure(self):
        """Проверяет структуру директорий"""
        logger.info("\n📁 Проверка структуры директорий...")

        required_dirs = [
            "config",
            "config/traders",
            "config/exchanges",
            "config/ml",
            "core",
            "core/config",
            "core/system",
            "core/traders",
            "database",
            "database/models",
            "database/connections",
            "exchanges",
            "exchanges/bybit",
            "exchanges/base",
            "ml",
            "ml/logic",
            "strategies",
            "strategies/ml_strategy",
            "trading",
            "trading/sltp",
            "web",
            "web/api",
            "web/frontend",
            "scripts",
            "scripts/migration",
            "models",
            "models/saved",
            "logs",
            "data",
        ]

        for dir_path in required_dirs:
            full_path = self.base_path / dir_path
            if full_path.exists():
                self._check_passed(f"Директория {dir_path}")
            else:
                self._check_failed(f"Директория {dir_path} не найдена")

    async def _check_configurations(self):
        """Проверяет конфигурационные файлы"""
        logger.info("\n⚙️ Проверка конфигураций...")

        # Проверяем system.yaml
        system_config_path = self.base_path / "config" / "system.yaml"
        if system_config_path.exists():
            try:
                with open(system_config_path, "r") as f:
                    config = yaml.safe_load(f)

                # Проверяем основные секции
                required_sections = [
                    "database",
                    "exchanges",
                    "notifications",
                    "ml_models",
                    "risk_management",
                ]

                for section in required_sections:
                    if section in config:
                        self._check_passed(f"Секция {section} в system.yaml")
                    else:
                        self._check_failed(
                            f"Секция {section} отсутствует в system.yaml"
                        )

                # Проверяем порт БД
                db_port = config.get("database", {}).get("port")
                if db_port == 5555:
                    self._check_passed("Порт БД = 5555")
                else:
                    self._check_failed(
                        f"Неверный порт БД: {db_port} (должен быть 5555)"
                    )

            except Exception as e:
                self._check_failed(f"Ошибка чтения system.yaml: {e}")
        else:
            self._check_failed("Файл system.yaml не найден")

        # Проверяем наличие хотя бы одного трейдера
        traders_dir = self.base_path / "config" / "traders"
        if traders_dir.exists():
            trader_configs = list(traders_dir.glob("*.yaml"))
            if trader_configs:
                self._check_passed(
                    f"Найдено {len(trader_configs)} конфигураций трейдеров"
                )
            else:
                self._check_failed("Нет конфигураций трейдеров")

        # Проверяем ML конфигурацию
        ml_config_path = self.base_path / "config" / "ml" / "ml_config.yaml"
        if ml_config_path.exists():
            self._check_passed("ML конфигурация")
        else:
            self._check_failed("ML конфигурация не найдена")

    def _check_dependencies(self):
        """Проверяет Python зависимости"""
        logger.info("\n📦 Проверка зависимостей...")

        required_packages = [
            "asyncio",
            "asyncpg",
            "fastapi",
            "uvicorn",
            "sqlalchemy",
            "alembic",
            "ccxt",
            "pandas",
            "numpy",
            "torch",
            "aiohttp",
            "websockets",
            "pydantic",
            "telegram",  # python-telegram-bot импортируется как telegram
            "structlog",
            "prometheus_client",
        ]

        for package in required_packages:
            spec = importlib.util.find_spec(package)
            if spec is not None:
                self._check_passed(f"Пакет {package}")
            else:
                self._check_failed(f"Пакет {package} не установлен")

    async def _check_database(self):
        """Проверяет подключение к базе данных"""
        logger.info("\n🗄️ Проверка базы данных...")

        try:
            # Читаем конфигурацию
            system_config_path = self.base_path / "config" / "system.yaml"
            if not system_config_path.exists():
                self._check_failed("Не найдена конфигурация БД")
                return

            with open(system_config_path, "r") as f:
                config = yaml.safe_load(f)

            db_config = config.get("database", {})

            # Пытаемся подключиться
            conn = await asyncpg.connect(
                host=db_config.get("host", "127.0.0.1"),
                port=db_config.get("port", 5555),
                database=db_config.get("name", "bot_trading_v3"),
                user=db_config.get("user", "obertruper"),
                password=db_config.get("password", "postgres"),
            )

            # Проверяем версию PostgreSQL
            version = await conn.fetchval("SELECT version()")
            self._check_passed("Подключение к PostgreSQL")
            logger.info(f"  PostgreSQL: {version.split(',')[0]}")

            # Проверяем основные таблицы
            tables = [
                "trades",
                "orders",
                "positions",
                "signals",
                "balances",
                "performance_metrics",
            ]

            for table in tables:
                exists = await conn.fetchval(
                    "SELECT EXISTS (SELECT FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = $1)",
                    table,
                )
                if exists:
                    self._check_passed(f"Таблица {table}")
                else:
                    self._check_failed(f"Таблица {table} не найдена")

            await conn.close()

        except Exception as e:
            self._check_failed(f"Ошибка подключения к БД: {e}")

    def _check_ml_models(self):
        """Проверяет наличие ML моделей"""
        logger.info("\n🤖 Проверка ML моделей...")

        # Проверяем PatchTST модель
        model_path = (
            self.base_path / "models" / "saved" / "best_model_20250728_215703.pth"
        )
        if model_path.exists():
            self._check_passed("PatchTST модель")
            # Проверяем размер файла
            size_mb = model_path.stat().st_size / (1024 * 1024)
            logger.info(f"  Размер модели: {size_mb:.1f} MB")
        else:
            self._check_failed("PatchTST модель не найдена")

        # Проверяем scaler
        scaler_path = self.base_path / "models" / "saved" / "data_scaler.pkl"
        if scaler_path.exists():
            self._check_passed("Data scaler")
        else:
            self._check_failed("Data scaler не найден")

    async def _check_core_components(self):
        """Проверяет основные компоненты"""
        logger.info("\n⚙️ Проверка основных компонентов...")

        # Проверяем наличие ключевых файлов
        core_files = [
            ("main.py", "Главный файл"),
            ("core/system/orchestrator.py", "System Orchestrator"),
            ("core/traders/trader_manager.py", "Trader Manager"),
            ("exchanges/bybit/bybit_exchange.py", "Bybit Exchange"),
            ("ml/ml_manager.py", "ML Manager"),
            ("ml/ml_signal_processor.py", "ML Signal Processor"),
            ("trading/sltp/enhanced_manager.py", "Enhanced SL/TP Manager"),
            ("web/api/main.py", "Web API"),
            ("strategies/ml_strategy/patchtst_strategy.py", "PatchTST Strategy"),
        ]

        for file_path, description in core_files:
            full_path = self.base_path / file_path
            if full_path.exists():
                self._check_passed(description)
            else:
                self._check_failed(f"{description} ({file_path})")

    async def _check_api_endpoints(self):
        """Проверяет API endpoints"""
        logger.info("\n🌐 Проверка API endpoints...")

        # Проверяем наличие endpoint файлов
        endpoint_files = [
            "web/api/endpoints/system.py",
            "web/api/endpoints/traders.py",
            "web/api/endpoints/monitoring.py",
            "web/api/endpoints/strategies.py",
            "web/api/endpoints/exchanges.py",
        ]

        for endpoint_file in endpoint_files:
            full_path = self.base_path / endpoint_file
            if full_path.exists():
                self._check_passed(
                    f"Endpoint: {endpoint_file.split('/')[-1].replace('.py', '')}"
                )
            else:
                self._check_failed(f"Endpoint не найден: {endpoint_file}")

        # Проверяем WebSocket manager
        ws_manager = self.base_path / "web" / "api" / "websocket" / "manager.py"
        if ws_manager.exists():
            self._check_passed("WebSocket Manager")
        else:
            self._check_failed("WebSocket Manager не найден")

    def _check_passed(self, message: str):
        """Отмечает успешную проверку"""
        self.checks_passed += 1
        logger.info(f"  ✅ {message}")

    def _check_failed(self, message: str):
        """Отмечает неудачную проверку"""
        self.checks_failed += 1
        logger.error(f"  ❌ {message}")

    def _add_warning(self, message: str):
        """Добавляет предупреждение"""
        self.warnings.append(message)
        logger.warning(f"  ⚠️ {message}")


async def main():
    """Основная функция"""
    import argparse

    parser = argparse.ArgumentParser(description="Проверка готовности BOT Trading v3")
    parser.add_argument(
        "--path", type=str, default=".", help="Путь к корневой директории v3"
    )

    args = parser.parse_args()

    checker = ReadinessChecker(args.path)
    success = await checker.run()

    # Возвращаем код выхода
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
