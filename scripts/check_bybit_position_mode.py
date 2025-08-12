#!/usr/bin/env python3
"""Проверка и настройка режима позиций Bybit"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from core.logger import setup_logger
from exchanges.bybit.client import BybitClient

logger = setup_logger("check_position_mode")


async def check_and_set_position_mode():
    """Проверяет и настраивает режим позиций Bybit"""
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

        # Проверяем текущий режим через API
        response = await client._make_request(
            method="GET",
            endpoint="/v5/position/switch-mode",
            params={"category": "linear"},
            auth=True,
        )

        result = response.get("result", {})
        mode = result.get("mode", 0)

        logger.info(
            f"📊 Текущий режим позиций: {'Hedge' if mode == 3 else 'One-way'} (mode={mode})"
        )

        # Получаем настройку из конфигурации
        config_hedge_mode = client.hedge_mode
        logger.info(f"⚙️ Настройка в конфигурации: hedge_mode={config_hedge_mode}")

        # Проверяем соответствие
        actual_hedge = mode == 3
        if actual_hedge != config_hedge_mode:
            logger.warning(
                f"⚠️ Несоответствие режимов! Аккаунт: {actual_hedge}, Конфиг: {config_hedge_mode}"
            )

            # Пробуем установить режим согласно конфигурации
            logger.info(
                f"🔧 Устанавливаем режим: {'Hedge' if config_hedge_mode else 'One-way'}"
            )

            # Проверяем открытые позиции
            positions = await client.get_positions()
            if positions:
                logger.error("❌ Нельзя изменить режим позиций при открытых позициях!")
                logger.info("Открытые позиции:")
                for pos in positions:
                    if pos.size != 0:
                        logger.info(f"  - {pos.symbol}: {pos.side} {pos.size}")
                return

            # Устанавливаем режим для основных символов
            symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]

            for symbol in symbols:
                try:
                    success = await client.set_position_mode(symbol, config_hedge_mode)
                    if success:
                        logger.info(f"✅ {symbol}: режим установлен")
                    else:
                        logger.warning(f"⚠️ {symbol}: не удалось установить режим")
                except Exception as e:
                    logger.error(f"❌ {symbol}: ошибка установки режима: {e}")
        else:
            logger.info("✅ Режимы позиций соответствуют!")

        # Тестовый ордер с правильным positionIdx
        logger.info("\n🧪 Тестируем создание ордера...")

        # Создаем минимальный тестовый ордер
        from exchanges.base.order_types import OrderRequest, OrderSide, OrderType

        test_order = OrderRequest(
            symbol="XRPUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10.0,  # Минимум для XRP
            price=3.30,  # Ниже рынка
            client_order_id=f"test_position_mode_{int(asyncio.get_event_loop().time())}",
        )

        # Получаем positionIdx
        position_idx = client._get_position_idx(test_order.side.value)
        logger.info(f"📍 Position index для {test_order.side.value}: {position_idx}")

        # Создаем ордер
        try:
            response = await client.place_order(test_order)
            if response.success:
                logger.info(f"✅ Тестовый ордер создан: {response.order_id}")

                # Сразу отменяем
                await asyncio.sleep(1)
                cancel_response = await client.cancel_order(
                    "XRPUSDT", response.order_id
                )
                if cancel_response.success:
                    logger.info("✅ Тестовый ордер отменен")
            else:
                logger.error(f"❌ Ошибка создания ордера: {response.error}")
        except Exception as e:
            logger.error(f"❌ Ошибка при тестировании: {e}")

            # Если ошибка position idx - предлагаем решение
            if "position idx not match" in str(e):
                logger.info("\n💡 РЕШЕНИЕ:")
                logger.info("1. Измените hedge_mode в config/system.yaml на false")
                logger.info("2. ИЛИ включите Hedge Mode в настройках Bybit:")
                logger.info("   - Зайдите на bybit.com")
                logger.info("   - Derivatives → Settings → Position Mode")
                logger.info("   - Переключите на 'Hedge Mode'")
                logger.info("3. Перезапустите систему после изменений")

    finally:
        await client.disconnect()
        logger.info("\n🔌 Отключен от Bybit")


if __name__ == "__main__":
    asyncio.run(check_and_set_position_mode())
