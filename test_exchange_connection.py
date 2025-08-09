#!/usr/bin/env python3
"""
Простой тест подключения к Bybit
"""

import asyncio
import logging
import os

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

from exchanges.bybit.client import BybitClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_bybit():
    """Тест подключения к Bybit"""
    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")
    testnet = os.getenv("BYBIT_TESTNET", "false").lower() == "true"

    if not api_key or not api_secret:
        logger.error("❌ API ключи не найдены в .env")
        return

    logger.info(f"🔑 API Key: {api_key[:10]}...")
    logger.info(f"🌐 Testnet: {testnet}")

    try:
        # Создаем клиент
        client = BybitClient(api_key=api_key, api_secret=api_secret, sandbox=testnet)

        # Проверяем подключение
        logger.info("🔄 Проверка подключения...")
        connected = await client.test_connection()

        if connected:
            logger.info("✅ Успешно подключено к Bybit!")

            # Получаем баланс
            try:
                balance = await client.get_balance()
                logger.info(f"💰 Баланс USDT: {balance.get('USDT', {}).get('free', 0)}")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось получить баланс: {e}")

            # Тестируем получение информации о символе
            try:
                symbol_info = await client.get_symbol_info("BTCUSDT")
                if symbol_info:
                    logger.info(
                        f"📊 BTCUSDT - Min qty: {symbol_info.get('min_quantity')}, Step: {symbol_info.get('quantity_step')}"
                    )
                else:
                    logger.warning("⚠️ Не удалось получить информацию о BTCUSDT")
            except Exception as e:
                logger.error(f"❌ Ошибка при получении информации о символе: {e}")
        else:
            logger.error("❌ Не удалось подключиться к Bybit")

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()
    finally:
        pass


if __name__ == "__main__":
    asyncio.run(test_bybit())
