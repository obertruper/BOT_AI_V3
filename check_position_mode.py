#!/usr/bin/env python3
"""Проверка position mode на Bybit"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv

from core.logger import setup_logger
from exchanges.bybit.client import BybitClient

logger = setup_logger("check_mode")


async def check_position_mode():
    """Проверяет текущий position mode"""
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

        # Получаем текущий position mode
        response = await client._make_request(
            "GET", "/v5/position/switch-mode", {"category": "linear"}
        )
        result = response.get("result", {})

        logger.info("📊 Position mode настройки:")
        logger.info(f"  - Position mode: {result}")

        # Проверяем для конкретного символа
        positions = await client.get_positions()
        logger.info(f"\n💼 Текущие позиции: {len(positions)}")

        # Попробуем переключить режим
        logger.info("\n🔄 Пытаемся установить one-way mode...")
        try:
            switch_response = await client._make_request(
                "POST",
                "/v5/position/switch-mode",
                {
                    "category": "linear",
                    "symbol": "ETHUSDT",
                    "coin": "USDT",
                    "mode": 0,  # 0 = one-way, 3 = hedge
                },
            )
            logger.info(f"✅ Результат: {switch_response}")
        except Exception as e:
            logger.error(f"❌ Ошибка переключения: {e}")

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        import traceback

        logger.error(traceback.format_exc())

    finally:
        await client.disconnect()
        logger.info("🔌 Отключен от Bybit")


if __name__ == "__main__":
    asyncio.run(check_position_mode())
