#!/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/venv/bin/python3
"""
Интегрированный запуск BOT Trading v3 с веб-интерфейсом
Запускает Core System и Web API в одном процессе с правильной интеграцией
"""

import asyncio
import os
import signal
import sys
import threading
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn

from core.config.config_manager import ConfigManager
from core.exceptions import ConfigurationError, SystemError
from core.logger import setup_logger
from core.system.orchestrator import SystemOrchestrator
from web.api.main import app, initialize_web_api
from web.integration.web_orchestrator_bridge import initialize_web_bridge

# Настройка логирования
logger = setup_logger("integrated_start")


class IntegratedBotSystem:
    """Интегрированная система с Core и Web API"""

    def __init__(self):
        self.orchestrator: SystemOrchestrator | None = None
        self.config_manager: ConfigManager | None = None
        self.shutdown_event = asyncio.Event()
        self.web_server = None
        self.web_thread = None

    async def initialize(self):
        """Инициализация всех компонентов системы"""
        logger.info("=" * 80)
        logger.info("🚀 BOT_AI_V3 - Интегрированный запуск")
        logger.info(f"📅 Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        try:
            # Загружаем конфигурацию
            logger.info("📋 Загрузка конфигурации...")
            self.config_manager = ConfigManager()

            # Проверяем критические настройки
            self._validate_critical_settings()

            # Создаем и инициализируем оркестратор
            logger.info("🎯 Инициализация SystemOrchestrator...")
            self.orchestrator = SystemOrchestrator(self.config_manager)
            await self.orchestrator.initialize()

            # Инициализируем Web API с компонентами orchestrator
            logger.info("🌐 Инициализация Web API...")
            from core.shared_context import shared_context

            # Сохраняем orchestrator в shared context
            shared_context.set_orchestrator(self.orchestrator)
            logger.info("✅ Orchestrator сохранен в shared context")

            initialize_web_api(
                orchestrator=self.orchestrator,
                trader_manager=getattr(self.orchestrator, "trader_manager", None),
                exchange_factory=getattr(self.orchestrator, "exchange_factory", None),
                config_manager=self.config_manager,
            )

            # Инициализируем web bridge
            global _web_bridge
            _web_bridge = await initialize_web_bridge(self.orchestrator)

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
        required_env = ["PGUSER", "PGPASSWORD", "PGDATABASE", "SECRET_KEY"]

        missing = []
        for var in required_env:
            if not os.getenv(var):
                missing.append(var)

        if missing:
            raise ConfigurationError(
                f"Отсутствуют обязательные переменные окружения: {', '.join(missing)}\n"
                f"Создайте файл .env на основе .env.example"
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

    async def start_core(self):
        """Запуск Core системы"""
        if not self.orchestrator:
            raise SystemError("Система не инициализирована")

        logger.info("\n🔄 Запуск компонентов Core системы...")

        try:
            # Запускаем оркестратор
            await self.orchestrator.start()

            # Выводим статус
            await self._print_system_status()

            logger.info("\n✅ Core система запущена успешно")

        except Exception as e:
            logger.error(f"❌ Ошибка при запуске Core системы: {e}")
            raise

    def start_web_server(self):
        """Запуск веб-сервера в отдельном потоке"""
        logger.info("\n🌐 Запуск Web API...")

        async def run_server():
            config = uvicorn.Config(
                app=app,
                host="0.0.0.0",
                port=8080,
                log_level="info",
                access_log=True,
                loop="asyncio",
            )
            self.web_server = uvicorn.Server(config)
            await self.web_server.serve()

        # Создаем новый event loop для веб-сервера
        def run_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_server())

        self.web_thread = threading.Thread(target=run_in_thread, daemon=True)
        self.web_thread.start()

        # Ждем запуска сервера
        import time

        time.sleep(3)

        logger.info("✅ Web API запущен на http://localhost:8080")
        logger.info("📚 API документация: http://localhost:8080/api/docs")

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

        # База данных
        db_status = status.get("database", {})
        if db_status.get("connected"):
            logger.info(
                f"\n💾 База данных: Подключена (PostgreSQL на порту {os.getenv('PGPORT', '5555')})"
            )
        else:
            logger.info("\n💾 База данных: Не подключена")

        logger.info("-" * 50)

    async def run(self):
        """Основной цикл работы системы"""
        logger.info("\n✅ Все компоненты запущены успешно")
        logger.info("📊 Система готова к работе")
        logger.info("🌐 Веб-интерфейс: http://localhost:5173")
        logger.info("📚 API документация: http://localhost:8080/api/docs")

        # Ожидаем сигнал остановки
        await self.shutdown_event.wait()

    async def stop(self):
        """Остановка всех компонентов системы"""
        logger.info("\n🛑 Получен сигнал остановки системы...")

        # Останавливаем веб-сервер
        if self.web_server:
            logger.info("⏸️ Останавливаем Web API...")
            self.web_server.should_exit = True

        # Останавливаем Core систему
        if self.orchestrator:
            logger.info("⏸️ Останавливаем Core систему...")
            await self.orchestrator.stop()

        logger.info("✅ Все компоненты остановлены")
        logger.info("👋 BOT_AI_V3 завершил работу")

    def handle_signal(self, sig, frame):
        """Обработчик системных сигналов"""
        logger.info(f"\n📡 Получен сигнал {sig}")
        self.shutdown_event.set()


async def main():
    """Основная функция запуска"""
    system = IntegratedBotSystem()

    # Настройка обработчиков сигналов
    signal.signal(signal.SIGINT, system.handle_signal)
    signal.signal(signal.SIGTERM, system.handle_signal)

    try:
        # Инициализация
        await system.initialize()

        # Запуск Core системы
        await system.start_core()

        # Запуск Web API в отдельном потоке
        system.start_web_server()

        # Основной цикл
        await system.run()

    except KeyboardInterrupt:
        logger.info("\n⌨️ Прерывание от пользователя")
    except Exception as e:
        logger.error(f"\n❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Остановка
        await system.stop()


if __name__ == "__main__":
    # Проверка версии Python
    if sys.version_info < (3, 8):
        print("❌ Требуется Python 3.8 или выше")
        sys.exit(1)

    # Запуск приложения
    asyncio.run(main())
