#!/usr/bin/env python3
"""
Простой запуск торгового бота
"""

import asyncio
import logging
import os
import signal

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("data/logs/simple_bot.log")],
)
logger = logging.getLogger(__name__)

# Убираем лишние логи
logging.getLogger("aiohttp").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)


async def main():
    """Главная функция"""
    logger.info("🚀 Запуск простого торгового бота")

    try:
        # Импортируем после логирования
        from exchanges.bybit.client import BybitClient
        from ml.ml_signal_processor import MLSignalProcessor
        from trading.signals.ai_signal_generator import AISignalGenerator

        # Загружаем конфигурацию
        api_key = os.getenv("BYBIT_API_KEY")
        api_secret = os.getenv("BYBIT_API_SECRET")

        if not api_key or not api_secret:
            logger.error("❌ API ключи не найдены в .env")
            return

        # Создаем клиент биржи
        logger.info("📡 Подключение к Bybit...")
        client = BybitClient(api_key, api_secret, sandbox=False)

        # Проверяем подключение
        if await client.test_connection():
            logger.info("✅ Успешно подключено к Bybit")
        else:
            logger.error("❌ Не удалось подключиться к Bybit")
            return

        # Создаем ML процессор
        logger.info("🧠 Инициализация ML системы...")
        from core.config.config_manager import ConfigManager
        from ml.ml_manager import MLManager

        # Загружаем конфигурацию
        config_manager = ConfigManager()
        ml_config = config_manager.get_ml_config()

        ml_manager = MLManager(config=ml_config)
        ml_processor = MLSignalProcessor(
            ml_manager=ml_manager, config={"symbols": ["BTCUSDT", "ETHUSDT"]}
        )

        # Создаем генератор сигналов
        logger.info("📊 Создание генератора сигналов...")
        # Сначала нужно создать exchange factory и registry
        from exchanges.factory import ExchangeFactory
        from exchanges.registry import ExchangeRegistry

        exchange_registry = ExchangeRegistry()
        exchange_factory = ExchangeFactory(config_manager.config)

        # Регистрируем биржу
        await exchange_registry.register_exchange("bybit", client)

        signal_generator = AISignalGenerator(
            config_manager=config_manager, exchange_name="bybit"
        )
        signal_generator.exchange_registry = exchange_registry

        # Запускаем генерацию сигналов
        logger.info("🚀 Запуск генерации сигналов...")
        await signal_generator.start()

        logger.info("✅ Бот запущен и работает!")
        logger.info("📊 Отслеживаем: BTCUSDT, ETHUSDT")
        logger.info("🛑 Для остановки нажмите Ctrl+C")

        # Ждем сигнал остановки
        stop_event = asyncio.Event()

        def signal_handler(sig, frame):
            logger.info("🛑 Получен сигнал остановки...")
            stop_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Главный цикл
        while not stop_event.is_set():
            await asyncio.sleep(5)

            # Проверяем здоровье системы
            if (
                hasattr(signal_generator, "is_running")
                and not signal_generator.is_running
            ):
                logger.warning("⚠️ Генератор сигналов остановился, перезапускаем...")
                await signal_generator.start()

        # Останавливаем
        logger.info("⏸️ Остановка бота...")
        await signal_generator.stop()

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()
    finally:
        logger.info("👋 Бот остановлен")


if __name__ == "__main__":
    # Загружаем переменные окружения
    from dotenv import load_dotenv

    load_dotenv()

    # Запускаем
    asyncio.run(main())
