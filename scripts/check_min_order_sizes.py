#!/usr/bin/env python3
"""Проверка минимальных размеров ордеров для Bybit"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from core.logger import setup_logger
from exchanges.bybit.client import BybitClient

logger = setup_logger("check_min_sizes")


async def check_min_order_sizes():
    """Проверяет минимальные размеры ордеров"""
    load_dotenv()

    # Создаем клиента
    client = BybitClient(
        api_key=os.getenv("BYBIT_API_KEY"),
        api_secret=os.getenv("BYBIT_API_SECRET"),
        sandbox=False,
    )

    try:
        await client.connect()
        logger.info("🔌 Подключен к Bybit")

        # Список символов для проверки
        symbols = [
            "BTCUSDT",
            "ETHUSDT",
            "BNBUSDT",
            "SOLUSDT",
            "XRPUSDT",
            "ADAUSDT",
            "DOGEUSDT",
            "DOTUSDT",
            "LINKUSDT",
        ]

        logger.info("\n📊 МИНИМАЛЬНЫЕ РАЗМЕРЫ ОРДЕРОВ:")
        logger.info("=" * 60)

        for symbol in symbols:
            try:
                # Получаем информацию об инструменте
                instrument = await client.get_instrument_info(symbol)

                logger.info(f"\n{symbol}:")
                logger.info(f"  Мин. количество: {instrument.min_order_qty}")
                logger.info(f"  Макс. количество: {instrument.max_order_qty}")
                logger.info(f"  Шаг количества: {instrument.qty_step}")
                logger.info(f"  Мин. цена: {instrument.min_price}")
                logger.info(f"  Макс. цена: {instrument.max_price}")
                logger.info(f"  Шаг цены: {instrument.price_step}")

                # Получаем текущую цену
                ticker = await client.get_ticker(symbol)
                current_price = float(ticker.last_price)

                # Рассчитываем минимальную стоимость ордера
                min_value = float(instrument.min_order_qty) * current_price
                logger.info(f"  Текущая цена: ${current_price:.2f}")
                logger.info(f"  Мин. стоимость ордера: ${min_value:.2f}")

            except Exception as e:
                logger.error(f"  Ошибка для {symbol}: {e}")

        # Тестовые размеры с учетом баланса 167 USDT
        logger.info("\n💡 РЕКОМЕНДАЦИИ ДЛЯ БАЛАНСА 167 USDT:")
        logger.info("=" * 60)
        logger.info("Используйте 1-2% от баланса на позицию: $1.67 - $3.34")
        logger.info("Это обеспечит возможность открыть несколько позиций")
        logger.info("\nПримеры размеров позиций:")

        # Примеры для популярных монет
        test_positions = {
            "BTCUSDT": 0.00001,  # ~$1 при цене $100k
            "ETHUSDT": 0.0001,  # ~$0.4 при цене $4k
            "XRPUSDT": 10.0,  # ~$33 при цене $3.3
            "DOGEUSDT": 10.0,  # ~$5 при цене $0.5
        }

        for symbol, qty in test_positions.items():
            try:
                ticker = await client.get_ticker(symbol)
                value = qty * float(ticker.last_price)
                logger.info(f"  {symbol}: {qty} ({value:.2f} USDT)")
            except:
                pass

    finally:
        await client.disconnect()
        logger.info("\n🔌 Отключен от Bybit")


if __name__ == "__main__":
    asyncio.run(check_min_order_sizes())
