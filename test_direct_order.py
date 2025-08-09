#!/usr/bin/env python3
"""Прямой тест API Bybit"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv

from core.logger import setup_logger
from exchanges.bybit.client import BybitClient

logger = setup_logger("test_direct")


async def test_direct_order():
    """Тестирует создание ордера напрямую через API"""
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

        # Проверяем конфигурацию
        logger.info(f"hedge_mode в конфиге: {client.hedge_mode}")
        logger.info(f"trading_category: {client.trading_category}")

        # Напрямую вызываем API
        params = {
            "category": "linear",
            "symbol": "ETHUSDT",
            "side": "Buy",
            "orderType": "Market",
            "qty": "0.01",
            "timeInForce": "IOC",
            # Не указываем positionIdx вообще
        }

        logger.info(f"📝 Отправляем ордер с параметрами: {params}")

        try:
            response = await client._make_request(
                "POST", "/v5/order/create", params, auth=True
            )
            logger.info(f"✅ Ордер создан успешно! Ответ: {response}")
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")

            # Пробуем с positionIdx=0
            params["positionIdx"] = 0
            logger.info(f"📝 Пробуем с positionIdx=0: {params}")

            try:
                response = await client._make_request(
                    "POST", "/v5/order/create", params, auth=True
                )
                logger.info(
                    f"✅ Ордер создан успешно с positionIdx=0! Ответ: {response}"
                )
            except Exception as e2:
                logger.error(f"❌ Снова ошибка: {e2}")

                # Пробуем с positionIdx=1
                params["positionIdx"] = 1
                logger.info(f"📝 Пробуем с positionIdx=1: {params}")

                try:
                    response = await client._make_request(
                        "POST", "/v5/order/create", params, auth=True
                    )
                    logger.info(
                        f"✅ Ордер создан успешно с positionIdx=1! Ответ: {response}"
                    )
                except Exception as e3:
                    logger.error(f"❌ И это не работает: {e3}")

                    # Пробуем с positionIdx=2
                    params["positionIdx"] = 2
                    logger.info(f"📝 Пробуем с positionIdx=2: {params}")

                    try:
                        response = await client._make_request(
                            "POST", "/v5/order/create", params, auth=True
                        )
                        logger.info(
                            f"✅ Ордер создан успешно с positionIdx=2! Ответ: {response}"
                        )
                    except Exception as e4:
                        logger.error(f"❌ Окончательная ошибка: {e4}")

    except Exception as e:
        logger.error(f"❌ Общая ошибка: {e}")
        import traceback

        logger.error(traceback.format_exc())

    finally:
        await client.disconnect()
        logger.info("🔌 Отключен от Bybit")


if __name__ == "__main__":
    asyncio.run(test_direct_order())
