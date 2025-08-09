#!/usr/bin/env python3
"""Простой тест торговли без сложных зависимостей"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv

from core.logger import setup_logger

logger = setup_logger("test_simple")


async def main():
    """Запуск простого теста"""
    load_dotenv()

    try:
        # Простой тест подключения к бирже
        logger.info("🚀 Тест подключения к Bybit...")
        from exchanges.bybit.client import BybitClient

        client = BybitClient(
            api_key=os.getenv("BYBIT_API_KEY"),
            api_secret=os.getenv("BYBIT_API_SECRET"),
            sandbox=False,
        )

        await client.connect()
        logger.info("✅ Подключен к Bybit")

        # Получаем баланс
        balance = await client.get_balance("USDT")
        balance_amount = float(balance.total) if hasattr(balance, "total") else 0
        logger.info(f"💰 Баланс: ${balance_amount:.2f} USDT")

        # Получаем ticker
        ticker = await client.get_ticker("BTCUSDT")
        logger.info(f"📊 BTC/USDT: ${ticker.last_price}")

        # Создаем простой сигнал
        logger.info("📡 Создание ML сигнала...")
        from database.models.base_models import SignalType
        from database.models.signal import Signal

        signal = Signal(
            symbol="BTCUSDT",
            exchange="bybit",
            signal_type=SignalType.LONG,
            strength=0.7,
            confidence=0.65,
            strategy_name="ML_Test",
            suggested_quantity=0.001,
        )

        logger.info(f"✅ Сигнал создан: {signal.symbol} {signal.signal_type}")

        # Создаем ордер
        if balance_amount > 10:
            logger.info("💸 Создание тестового ордера...")
            from exchanges.base.order_types import OrderRequest, OrderSide, OrderType

            # Рассчитаем размер позиции на 1% от баланса
            btc_price = float(ticker.last_price)
            position_size_usd = balance_amount * 0.01  # 1% от баланса
            quantity = position_size_usd / btc_price

            # Округлим до минимального размера
            quantity = max(0.001, round(quantity, 6))

            logger.info(
                f"📏 Размер позиции: {quantity} BTC (${quantity * btc_price:.2f})"
            )

            order_request = OrderRequest(
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=quantity,
                leverage=5,  # Используем плечо как в конфиге
            )

            result = await client.place_order(order_request)
            if result and hasattr(result, "order_id"):
                logger.info(f"✅ Ордер создан! ID: {result.order_id}")
            else:
                logger.info(f"✅ Результат: {result}")
        else:
            logger.warning("⚠️ Недостаточно средств для тестового ордера")

        await client.disconnect()
        logger.info("✅ Тест завершен успешно!")

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        import traceback

        logger.error(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main())
