#!/usr/bin/env python3
"""Проверка статуса ордера на Bybit"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv

from core.logger import setup_logger
from exchanges.bybit.client import BybitClient

logger = setup_logger("check_order")


async def check_order():
    """Проверка ордера"""
    load_dotenv()

    client = BybitClient(
        api_key=os.getenv("BYBIT_API_KEY"),
        api_secret=os.getenv("BYBIT_API_SECRET"),
        sandbox=False,
    )

    try:
        await client.connect()

        # Проверяем конкретный ордер
        order_id = "c78332b4-39a5-4248-b69a-49178d3abcb3"
        logger.info(f"🔍 Проверка ордера {order_id}")

        # Получаем активные ордера
        params = {"category": "linear", "settleCoin": "USDT"}

        response = await client._make_request(
            "GET", "/v5/order/realtime", params, auth=True
        )
        logger.info(f"📦 Активные ордера: {len(response['result']['list'])} шт.")

        for order in response["result"]["list"]:
            logger.info(
                f"  - {order['symbol']}: {order['side']} {order['qty']} @ {order.get('price', 'MARKET')}"
            )
            logger.info(f"    ID: {order['orderId']}, Status: {order['orderStatus']}")

        # Получаем историю ордеров
        params = {"category": "linear", "orderId": order_id}

        try:
            response = await client._make_request(
                "GET", "/v5/order/history", params, auth=True
            )
            if response["result"]["list"]:
                order = response["result"]["list"][0]
                logger.info("\n✅ Найден ордер в истории:")
                logger.info(f"  Symbol: {order['symbol']}")
                logger.info(f"  Side: {order['side']}")
                logger.info(f"  Qty: {order['qty']}")
                logger.info(f"  Status: {order['orderStatus']}")
                logger.info(f"  Created: {order['createdTime']}")
                logger.info(f"  Executed Qty: {order.get('cumExecQty', 0)}")
                logger.info(f"  Avg Price: {order.get('avgPrice', 'N/A')}")
            else:
                logger.warning(f"⚠️ Ордер {order_id} не найден")
        except Exception as e:
            logger.error(f"❌ Ошибка получения истории: {e}")

        # Проверяем позиции
        positions = await client.get_positions()
        logger.info(f"\n📊 Открытые позиции: {len(positions)} шт.")
        for pos in positions:
            logger.info(f"  - {pos.symbol}: {pos.side} {pos.size}")
            logger.info(
                f"    Entry: ${pos.mark_price:.2f}, PnL: ${pos.unrealised_pnl:.2f}"
            )

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        import traceback

        logger.error(traceback.format_exc())
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(check_order())
