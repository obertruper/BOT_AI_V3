#!/usr/bin/env python3
"""
BOT_Trading v3.0 - Главная точка входа в систему

Мульти-трейдер, мульти-биржевая, мульти-стратегийная система
автоматизированной торговли на криптовалютных рынках.

Автор: OberTrading Team
Версия: 3.0
Дата: 2025-01-07
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

# Добавление корневой директории в путь
sys.path.insert(0, str(Path(__file__).parent))

from core.config.config_manager import ConfigManager
from core.exceptions import SystemInitializationError
from core.logging.logger_factory import LoggerFactory
from core.system.orchestrator import SystemOrchestrator
from utils.helpers import print_banner


class BOTTradingApp:
    """
    Главное приложение BOT_Trading v3.0

    Обеспечивает:
    - Инициализацию системы
    - Управление жизненным циклом
    - Обработку сигналов системы
    - Graceful shutdown
    """

    def __init__(self):
        self.orchestrator: Optional[SystemOrchestrator] = None
        self.config_manager: Optional[ConfigManager] = None
        self.logger: Optional[logging.Logger] = None
        self.is_running = False

    async def initialize(self) -> None:
        """Инициализация системы"""
        try:
            # Загрузка конфигурации
            self.config_manager = ConfigManager()
            await self.config_manager.load_system_config()

            # Инициализация логирования
            LoggerFactory.initialize(self.config_manager.get_logging_config())
            self.logger = LoggerFactory.get_logger("main")

            self.logger.info("🚀 Инициализация BOT_Trading v3.0...")

            # Создание оркестратора
            self.orchestrator = SystemOrchestrator(self.config_manager)
            await self.orchestrator.initialize()

            self.logger.info("✅ Система успешно инициализирована")

        except Exception as e:
            error_msg = f"❌ Ошибка инициализации системы: {e}"
            if self.logger:
                self.logger.error(error_msg)
            else:
                print(error_msg)
            raise SystemInitializationError(error_msg) from e

    async def start(self) -> None:
        """Запуск системы"""
        try:
            self.logger.info("🎯 Запуск торговой системы...")

            # Запуск оркестратора
            await self.orchestrator.start()
            self.is_running = True

            self.logger.info("🟢 Система запущена и готова к работе")

            # Основной цикл работы
            await self._main_loop()

        except Exception as e:
            self.logger.error(f"❌ Ошибка при запуске системы: {e}")
            raise

    async def _main_loop(self) -> None:
        """Основной цикл работы системы"""
        try:
            while self.is_running:
                # Проверка здоровья системы
                health_status = await self.orchestrator.health_check()

                if not health_status.is_healthy:
                    self.logger.warning(f"⚠️ Проблемы в системе: {health_status.issues}")

                # Ожидание перед следующей проверкой
                await asyncio.sleep(30)  # Проверка каждые 30 секунд

        except asyncio.CancelledError:
            self.logger.info("📊 Основной цикл прерван")
        except Exception as e:
            self.logger.error(f"❌ Ошибка в основном цикле: {e}")
            raise

    async def shutdown(self) -> None:
        """Graceful shutdown системы"""
        try:
            self.logger.info("🛑 Начинаем остановку системы...")
            self.is_running = False

            if self.orchestrator:
                await self.orchestrator.shutdown()

            self.logger.info("✅ Система успешно остановлена")

        except Exception as e:
            self.logger.error(f"❌ Ошибка при остановке системы: {e}")
            raise

    def _setup_signal_handlers(self) -> None:
        """Настройка обработчиков сигналов"""

        def signal_handler(signum, frame):
            self.logger.info(f"📨 Получен сигнал {signum}")
            asyncio.create_task(self.shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Главная функция запуска приложения"""
    app = BOTTradingApp()

    try:
        # Вывод баннера
        print_banner()

        # Инициализация
        await app.initialize()

        # Настройка обработчиков сигналов
        app._setup_signal_handlers()

        # Запуск системы
        await app.start()

    except KeyboardInterrupt:
        print("\n🛑 Получен сигнал прерывания")
    except SystemInitializationError as e:
        print(f"❌ Ошибка инициализации: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)
    finally:
        try:
            await app.shutdown()
        except Exception:
            pass  # Игнорируем ошибки при shutdown, т.к. система уже в нестабильном состоянии


if __name__ == "__main__":
    # Проверка версии Python
    if sys.version_info < (3, 8):
        print("❌ Требуется Python 3.8 или выше")
        sys.exit(1)

    try:
        # Запуск главного приложения
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 До свидания!")
    except Exception as e:
        print(f"❌ Фатальная ошибка: {e}")
        sys.exit(1)
