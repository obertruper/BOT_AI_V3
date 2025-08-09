#!/usr/bin/env python3
"""
Тест подключения к биржам
"""

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from core.config.config_loader import ConfigLoader
from exchanges.factory import ExchangeFactory

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_connection():
    """Тест подключения к биржам"""
    try:
        # Загружаем конфигурацию
        config_loader = ConfigLoader()
        config = config_loader.load_all_configs()

        # Создаем фабрику бирж
        factory = ExchangeFactory(config)

        # Проверяем доступные биржи
        logger.info(f"Доступные биржи: {factory.available_exchanges}")

        if not factory.available_exchanges:
            logger.error("❌ Нет доступных бирж! Проверьте API ключи в .env")
            return False

        # Получаем первую доступную биржу
        exchange_name = list(factory.available_exchanges)[0]
        logger.info(f"Тестируем биржу: {exchange_name}")

        # Получаем клиент биржи
        client = await factory.get_exchange(exchange_name)

        if not client:
            logger.error(f"❌ Не удалось получить клиент биржи {exchange_name}")
            return False

        # Проверяем подключение
        logger.info("Проверяем подключение...")
        connected = await client.check_connection()

        if connected:
            logger.info(f"✅ Успешно подключено к {exchange_name}")

            # Получаем баланс
            balance = await client.get_balance()
            logger.info(f"💰 Баланс: {balance}")

            # Получаем информацию о паре
            symbol_info = await client.get_symbol_info("BTCUSDT")
            if symbol_info:
                logger.info(f"📊 Информация о BTCUSDT: {symbol_info}")

            return True
        else:
            logger.error(f"❌ Не удалось подключиться к {exchange_name}")
            return False

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Главная функция"""
    logger.info("🚀 Тестирование подключения к биржам...")

    success = await test_connection()

    if success:
        logger.info("✅ Тест пройден успешно!")
    else:
        logger.error("❌ Тест провален!")


if __name__ == "__main__":
    asyncio.run(main())
