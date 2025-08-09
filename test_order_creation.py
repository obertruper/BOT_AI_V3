#!/usr/bin/env python3
"""Тест создания ордеров с правильными размерами"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv

from core.logger import setup_logger
from exchanges.bybit.client import BybitClient

logger = setup_logger("test_orders")


async def test_order_creation():
    """Тестирует создание ордеров"""
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

        # Получаем баланс
        balance = await client.get_balance("USDT")
        balance_amount = float(balance.total) if hasattr(balance, "total") else 167.0
        logger.info(f"💰 Баланс: {balance_amount} USDT")

        # Получаем информацию об инструменте
        instrument = await client.get_instrument_info("ETHUSDT")
        logger.info(
            f"📊 ETHUSDT: min={instrument.min_order_qty}, step={instrument.qty_step}"
        )

        # Получаем текущую цену
        ticker = await client.get_ticker("ETHUSDT")
        current_price = float(ticker.last_price)
        logger.info(f"💹 Текущая цена: ${current_price}")

        # Рассчитываем размер позиции (1% от баланса)
        position_size_usd = balance_amount * 0.01
        quantity = position_size_usd / current_price

        # Округляем до qty_step
        qty_step = float(instrument.qty_step)
        quantity = round(quantity / qty_step) * qty_step

        # Проверяем минимальный размер
        min_qty = float(instrument.min_order_qty)
        if quantity < min_qty:
            quantity = min_qty

        logger.info(
            f"📏 Размер ордера: {quantity} ETH (${quantity * current_price:.2f})"
        )

        # Создаем тестовый ордер
        logger.info("📝 Создаем тестовый ордер BUY...")

        logger.info(f"Параметры ордера: symbol=ETHUSDT, side=Buy, quantity={quantity}")

        # Размещаем ордер используя OrderRequest
        from exchanges.base.order_types import OrderRequest, OrderSide, OrderType

        order_request = OrderRequest(
            symbol="ETHUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=quantity,
            price=None,  # Market order
            leverage=1,
        )

        result = await client.place_order(order_request)

        if result:
            if hasattr(result, "order_id"):
                logger.info(f"✅ Ордер успешно создан! ID: {result.order_id}")
                logger.info(f"Статус: {result.status}")
            else:
                logger.info(f"✅ Ордер создан! Результат: {result}")
        else:
            logger.error("❌ Не удалось создать ордер")

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        import traceback

        logger.error(traceback.format_exc())

    finally:
        await client.disconnect()
        logger.info("🔌 Отключен от Bybit")


if __name__ == "__main__":
    asyncio.run(test_order_creation())
