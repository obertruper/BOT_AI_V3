#!/usr/bin/env python3
"""
Интерактивный торговый терминал BOT_AI_V3
Позволяет запускать и контролировать торговую систему в реальном времени
"""

import asyncio
import os
import signal
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from core.system.orchestrator import SystemOrchestrator

logger = setup_logger("interactive_trading")


class InteractiveTradingTerminal:
    def __init__(self):
        self.orchestrator = None
        self.running = False
        self.config_manager = ConfigManager()

    async def check_system_health(self):
        """Проверка состояния системы"""
        logger.info("🔍 Проверка состояния системы...")

        # Проверка конфигурации
        try:
            config = self.config_manager.load_config()
            logger.info("✅ Конфигурация загружена")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки конфигурации: {e}")
            return False

        # Проверка API ключей
        bybit_key = os.getenv("BYBIT_API_KEY")
        bybit_secret = os.getenv("BYBIT_API_SECRET")

        if not bybit_key or not bybit_secret:
            logger.error("❌ Отсутствуют API ключи Bybit")
            return False

        logger.info("✅ API ключи найдены")

        # Проверка базы данных
        pg_user = os.getenv("PGUSER")
        pg_db = os.getenv("PGDATABASE")

        if not pg_user or not pg_db:
            logger.error("❌ Отсутствуют настройки PostgreSQL")
            return False

        logger.info("✅ Настройки PostgreSQL найдены")

        return True

    async def start_trading_system(self):
        """Запуск торговой системы"""
        logger.info("🚀 Запуск торговой системы...")

        try:
            # Создаем оркестратор
            self.orchestrator = SystemOrchestrator()

            # Инициализируем систему
            await self.orchestrator.initialize()
            logger.info("✅ Система инициализирована")

            # Запускаем систему
            await self.orchestrator.start()
            logger.info("✅ Торговая система запущена")

            self.running = True
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка запуска системы: {e}")
            return False

    async def stop_trading_system(self):
        """Остановка торговой системы"""
        if self.orchestrator and self.running:
            logger.info("🛑 Остановка торговой системы...")
            await self.orchestrator.stop()
            self.running = False
            logger.info("✅ Система остановлена")

    async def show_status(self):
        """Показать статус системы"""
        if not self.orchestrator:
            logger.info("⚠️ Система не инициализирована")
            return

        try:
            # Получаем статус основных компонентов
            status = await self.orchestrator.get_system_status()

            logger.info("📊 Статус системы:")
            logger.info(f"   🔗 Подключения: {status.get('connections', 'N/A')}")
            logger.info(f"   🤖 ML модель: {status.get('ml_status', 'N/A')}")
            logger.info(f"   📈 Стратегии: {status.get('strategies', 'N/A')}")
            logger.info(f"   ⚡ Сигналы: {status.get('signals', 'N/A')}")

        except Exception as e:
            logger.error(f"❌ Ошибка получения статуса: {e}")

    async def test_bybit_connection(self):
        """Тестирование подключения к Bybit"""
        logger.info("🔄 Тестирование подключения к Bybit...")

        try:
            from exchanges.factory import ExchangeFactory, ExchangeType

            factory = ExchangeFactory()
            client = factory.create_client(
                exchange_type=ExchangeType.BYBIT,
                api_key=os.getenv("BYBIT_API_KEY"),
                api_secret=os.getenv("BYBIT_API_SECRET"),
                sandbox=False,
            )

            # Тестируем соединение
            connected = await client.connect()
            if connected:
                logger.info("✅ Bybit подключение успешно")

                # Получаем информацию об аккаунте
                try:
                    account_info = await client.get_account_info()
                    logger.info("✅ Информация об аккаунте получена")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось получить информацию об аккаунте: {e}")

                # Получаем тикер BTCUSDT
                try:
                    ticker = await client.get_ticker("BTCUSDT")
                    logger.info(f"✅ BTCUSDT тикер: {ticker.last_price}")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось получить тикер: {e}")

                await client.disconnect()
            else:
                logger.error("❌ Не удалось подключиться к Bybit")

        except Exception as e:
            logger.error(f"❌ Ошибка тестирования Bybit: {e}")

    async def run_interactive_mode(self):
        """Запуск интерактивного режима"""
        logger.info("🎯 BOT_AI_V3 - Интерактивный торговый терминал")
        logger.info("=" * 60)

        # Проверка системы
        if not await self.check_system_health():
            logger.error("❌ Система не готова к работе")
            return

        # Тестирование Bybit
        await self.test_bybit_connection()

        # Меню команд
        while True:
            print("\n" + "=" * 40)
            print("📋 Доступные команды:")
            print("1. start   - Запустить торговую систему")
            print("2. stop    - Остановить торговую систему")
            print("3. status  - Показать статус")
            print("4. test    - Тест Bybit подключения")
            print("5. exit    - Выход")
            print("=" * 40)

            try:
                choice = input("Введите команду (1-5): ").strip()

                if choice == "1" or choice.lower() == "start":
                    if not self.running:
                        await self.start_trading_system()
                    else:
                        logger.info("⚠️ Система уже запущена")

                elif choice == "2" or choice.lower() == "stop":
                    await self.stop_trading_system()

                elif choice == "3" or choice.lower() == "status":
                    await self.show_status()

                elif choice == "4" or choice.lower() == "test":
                    await self.test_bybit_connection()

                elif choice == "5" or choice.lower() == "exit":
                    break

                else:
                    print("❌ Неизвестная команда")

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"❌ Ошибка выполнения команды: {e}")

        # Останавливаем систему при выходе
        await self.stop_trading_system()
        logger.info("👋 Интерактивный терминал завершен")


async def main():
    terminal = InteractiveTradingTerminal()

    # Обработчик сигналов
    def signal_handler(signum, frame):
        logger.info("🛑 Получен сигнал остановки...")
        asyncio.create_task(terminal.stop_trading_system())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    await terminal.run_interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())
