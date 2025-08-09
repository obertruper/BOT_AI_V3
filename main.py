#!/usr/bin/env python3
"""
Главная точка входа для BOT_AI_V3
Запускает SystemOrchestrator который координирует все компоненты системы
"""

import asyncio
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from core.config.config_manager import ConfigManager
from core.exceptions import ConfigurationError, SystemError
from core.logger import setup_logger
from core.shared_context import shared_context
from core.system.orchestrator import SystemOrchestrator

# Настройка логирования
logger = setup_logger("main")


class BotAIV3Application:
    """Основное приложение торгового бота"""

    def __init__(self):
        self.orchestrator: Optional[SystemOrchestrator] = None
        self.config_manager: Optional[ConfigManager] = None
        self.shutdown_event = asyncio.Event()

    async def initialize(self):
        """Инициализация всех компонентов системы"""
        logger.info("=" * 80)
        logger.info("🚀 BOT_AI_V3 - Запуск системы")
        logger.info(f"📅 Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        try:
            # Загружаем конфигурацию
            logger.info("📋 Загрузка конфигурации...")
            self.config_manager = ConfigManager()
            await self.config_manager.initialize()

            # Проверяем критические настройки
            self._validate_critical_settings()

            # Создаем и инициализируем оркестратор
            logger.info("🎯 Инициализация SystemOrchestrator...")
            self.orchestrator = SystemOrchestrator(self.config_manager)
            await self.orchestrator.initialize()

            # Сохраняем orchestrator в shared context для веб API
            shared_context.set_orchestrator(self.orchestrator)
            logger.info("✅ Orchestrator сохранен в shared context")

            logger.info("✅ Система успешно инициализирована")

        except ConfigurationError as e:
            logger.error(f"❌ Ошибка конфигурации: {e}")
            logger.error("💡 Проверьте файл .env и конфигурационные файлы")
            raise
        except Exception as e:
            logger.error(f"❌ Критическая ошибка при инициализации: {e}")
            raise

    def _validate_critical_settings(self):
        """Проверка критических настроек"""
        # Проверка переменных окружения
        required_env = ["PGUSER", "PGPASSWORD", "PGDATABASE", "SECRET_KEY"]

        missing = []
        for var in required_env:
            if not os.getenv(var):
                missing.append(var)

        if missing:
            raise ConfigurationError(
                f"Отсутствуют обязательные переменные окружения: {', '.join(missing)}\n"
                f"Создайте файл .env на основе config/.env.example"
            )

        # Проверка наличия хотя бы одного API ключа биржи
        exchanges = ["BYBIT", "BINANCE", "OKX", "BITGET", "GATEIO", "KUCOIN", "HUOBI"]
        has_exchange = False

        for exchange in exchanges:
            if os.getenv(f"{exchange}_API_KEY"):
                has_exchange = True
                logger.info(f"✅ Обнаружены API ключи для {exchange}")
                break

        if not has_exchange:
            logger.warning(
                "⚠️ Не найдены API ключи бирж. "
                "Добавьте хотя бы один набор ключей в .env для торговли"
            )

    async def start(self):
        """Запуск всех компонентов системы"""
        if not self.orchestrator:
            raise SystemError("Система не инициализирована")

        logger.info("\n🔄 Запуск компонентов системы...")

        try:
            # Запускаем оркестратор
            await self.orchestrator.start()

            # Выводим статус
            await self._print_system_status()

            logger.info("\n✅ Все компоненты запущены успешно")
            logger.info("📊 Система готова к работе")
            logger.info("💼 Core система запущена (торговый движок)")
            logger.info("📡 Для веб-интерфейса используйте: python unified_launcher.py")

            # Ожидаем сигнал остановки
            await self.shutdown_event.wait()

        except Exception as e:
            logger.error(f"❌ Ошибка при запуске системы: {e}")
            raise

    async def _print_system_status(self):
        """Вывод статуса системы"""
        if not self.orchestrator:
            return

        status = await self.orchestrator.get_status()

        logger.info("\n📊 СТАТУС СИСТЕМЫ:")
        logger.info("-" * 50)

        # Компоненты
        logger.info("Активные компоненты:")
        for component, is_active in status.get("components", {}).items():
            icon = "✅" if is_active else "❌"
            logger.info(f"  {icon} {component}")

        # Биржи
        logger.info("\nПодключенные биржи:")
        for exchange in status.get("exchanges", []):
            logger.info(f"  🏦 {exchange}")

        # Стратегии
        logger.info("\nАктивные стратегии:")
        for strategy in status.get("strategies", []):
            logger.info(f"  📈 {strategy}")

        # База данных
        db_status = status.get("database", {})
        if db_status.get("connected"):
            logger.info(
                f"\n💾 База данных: Подключена (PostgreSQL на порту {os.getenv('PGPORT', '5555')})"
            )
        else:
            logger.info("\n💾 База данных: Не подключена")

        logger.info("-" * 50)

    async def stop(self):
        """Остановка всех компонентов системы"""
        logger.info("\n🛑 Получен сигнал остановки системы...")

        if self.orchestrator:
            logger.info("⏸️ Останавливаем компоненты...")
            await self.orchestrator.stop()
            logger.info("✅ Все компоненты остановлены")

        logger.info("👋 BOT_AI_V3 завершил работу")

    def handle_signal(self, sig, frame):
        """Обработчик системных сигналов"""
        logger.info(f"\n📡 Получен сигнал {sig}")
        self.shutdown_event.set()


async def main():
    """Основная функция запуска"""
    app = BotAIV3Application()

    # Настройка обработчиков сигналов
    signal.signal(signal.SIGINT, app.handle_signal)
    signal.signal(signal.SIGTERM, app.handle_signal)

    try:
        # Инициализация
        await app.initialize()

        # Запуск
        await app.start()

    except KeyboardInterrupt:
        logger.info("\n⌨️ Прерывание от пользователя")
    except Exception as e:
        logger.error(f"\n❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Остановка
        await app.stop()


if __name__ == "__main__":
    # Проверка версии Python
    if sys.version_info < (3, 8):
        print("❌ Требуется Python 3.8 или выше")
        sys.exit(1)

    # Запуск приложения
    asyncio.run(main())
