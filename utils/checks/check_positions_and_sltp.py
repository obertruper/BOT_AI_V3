#!/usr/bin/env python3
"""
Скрипт для проверки активных позиций и их SL/TP на бирже Bybit
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from core.config.config_manager import ConfigManager
from core.logger import setup_logger

logger = setup_logger("check_positions")


async def check_positions():
    """Проверка позиций и их SL/TP"""
    try:
        # Загружаем конфигурацию
        config_manager = ConfigManager()
        await config_manager.initialize()
        config = config_manager.get_config()

        # Создаем подключение к бирже
        exchange_name = "bybit"
        exchange_config = config.get("exchanges", {}).get(exchange_name, {})

        if not exchange_config.get("enabled"):
            logger.error(f"Биржа {exchange_name} не включена в конфигурации")
            return

        # Создаем экземпляр биржи
        from exchanges.factory import get_exchange_factory

        factory = get_exchange_factory()

        # Получаем API ключи из конфигурации
        api_key = exchange_config.get("api_key", "")
        api_secret = exchange_config.get("api_secret", "")
        testnet = exchange_config.get("testnet", False)

        exchange = await factory.create_and_connect(
            exchange_name, api_key=api_key, api_secret=api_secret
        )

        logger.info("🔍 Проверка позиций на Bybit...")

        # Получаем активные позиции
        positions = await exchange.get_positions()

        if not positions:
            logger.info("📊 Нет активных позиций")
            return

        logger.info(f"📊 Найдено {len(positions)} активных позиций:")

        for pos in positions:
            logger.info(f"\n{'=' * 50}")
            logger.info(f"Символ: {pos.symbol}")
            logger.info(f"Сторона: {pos.side}")
            logger.info(f"Количество: {pos.contracts}")
            logger.info(f"Цена входа: {pos.entry_price}")
            logger.info(f"Текущая цена: {pos.mark_price}")
            logger.info(f"Нереализованный PnL: {pos.unrealized_pnl}")

            # Проверяем SL/TP
            if hasattr(pos, "stop_loss") and pos.stop_loss:
                logger.info(f"✅ Stop Loss: {pos.stop_loss}")
            else:
                logger.warning("❌ Stop Loss: НЕ УСТАНОВЛЕН")

            if hasattr(pos, "take_profit") and pos.take_profit:
                logger.info(f"✅ Take Profit: {pos.take_profit}")
            else:
                logger.warning("❌ Take Profit: НЕ УСТАНОВЛЕН")

        # Проверяем открытые ордера
        logger.info("\n\n🔍 Проверка открытых ордеров...")

        try:
            # Получаем все открытые ордера
            open_orders = await exchange.get_open_orders()

            if not open_orders:
                logger.info("📋 Нет открытых ордеров")
            else:
                logger.info(f"📋 Найдено {len(open_orders)} открытых ордеров:")

                sl_tp_orders = 0
                for order in open_orders:
                    # Проверяем, является ли это SL/TP ордером
                    if hasattr(order, "order_type") and order.order_type in [
                        "STOP",
                        "TAKE_PROFIT",
                        "STOP_MARKET",
                        "TAKE_PROFIT_MARKET",
                    ]:
                        sl_tp_orders += 1
                        logger.info("\n  SL/TP Ордер:")
                        logger.info(f"  - ID: {order.order_id}")
                        logger.info(f"  - Тип: {order.order_type}")
                        logger.info(f"  - Символ: {order.symbol}")
                        logger.info(f"  - Сторона: {order.side}")
                        logger.info(f"  - Триггер цена: {getattr(order, 'trigger_price', 'N/A')}")
                        logger.info(f"  - Количество: {order.quantity}")

                logger.info(f"\n📈 Итого SL/TP ордеров: {sl_tp_orders}")

        except Exception as e:
            logger.error(f"Ошибка получения открытых ордеров: {e}")

    except Exception as e:
        logger.error(f"Ошибка проверки позиций: {e}")
        import traceback

        logger.error(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(check_positions())
