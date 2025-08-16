#!/usr/bin/env python3
"""
Тестирование Enhanced SL/TP системы в боевом режиме

Этот скрипт проверяет работу:
1. Частичного закрытия позиций (Partial TP)
2. Защиты прибыли (Profit Protection)
3. Трейлинг стопа
4. Интеграции с Trading Engine
"""

import asyncio
import os
import sys

# Добавляем корневую директорию в sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool
from exchanges.factory import ExchangeFactory
from trading.sltp.enhanced_manager import EnhancedSLTPManager
from trading.sltp.models import (
    PartialTPLevel,
    ProfitProtectionConfig,
    SLTPConfig,
    TrailingStopConfig,
)

logger = setup_logger("test_enhanced_sltp")


async def test_enhanced_sltp():
    """Основная функция тестирования"""
    try:
        # Инициализация базы данных
        await AsyncPGPool.init_pool()
        logger.info("База данных подключена")

        # Создание клиента биржи
        exchange_factory = ExchangeFactory()
        exchange_client = await exchange_factory.create_exchange(
            exchange_name="bybit",
            api_key=os.getenv("BYBIT_API_KEY"),
            api_secret=os.getenv("BYBIT_API_SECRET"),
            testnet=False,
        )
        await exchange_client.connect()
        logger.info("Подключение к Bybit установлено")

        # Создание конфигурации Enhanced SL/TP
        sltp_config = SLTPConfig(
            partial_tp_enabled=True,
            partial_tp_levels=[
                PartialTPLevel(
                    level=1,
                    price=0,  # Будет рассчитано
                    quantity=0,  # Будет рассчитано
                    percentage=1.0,  # 1% прибыли
                    close_ratio=0.25,  # Закрыть 25% позиции
                ),
                PartialTPLevel(
                    level=2,
                    price=0,
                    quantity=0,
                    percentage=2.0,  # 2% прибыли
                    close_ratio=0.25,  # Закрыть еще 25%
                ),
                PartialTPLevel(
                    level=3,
                    price=0,
                    quantity=0,
                    percentage=3.0,  # 3% прибыли
                    close_ratio=0.50,  # Закрыть оставшиеся 50%
                ),
            ],
            partial_tp_update_sl=True,
            trailing_stop=TrailingStopConfig(
                enabled=True,
                type="percentage",
                step=0.5,
                min_profit=0.3,
                max_distance=2.0,
            ),
            profit_protection=ProfitProtectionConfig(
                enabled=True,
                breakeven_percent=1.0,
                breakeven_offset=0.2,
                lock_percent=[
                    {"trigger": 2.0, "lock": 1.0},
                    {"trigger": 3.0, "lock": 2.0},
                    {"trigger": 4.0, "lock": 3.0},
                ],
                max_updates=5,
            ),
        )

        # Создание Enhanced SL/TP Manager
        enhanced_manager = EnhancedSLTPManager(exchange_client=exchange_client, config=sltp_config)
        logger.info("Enhanced SL/TP Manager создан")

        # Получение текущих позиций
        positions = await exchange_client.get_positions()
        active_positions = [p for p in positions if p.size != 0]

        if not active_positions:
            logger.warning("Нет активных позиций для тестирования")
            logger.info("Создайте позицию вручную или через основную систему")
            return

        logger.info(f"Найдено {len(active_positions)} активных позиций")

        # Тестирование для каждой позиции
        for position in active_positions:
            logger.info(f"\n{'=' * 50}")
            logger.info(f"Тестирование позиции {position.symbol}")
            logger.info(f"Размер: {position.size}, Цена входа: {position.entry_price}")

            # Получение текущей цены
            ticker = await exchange_client.get_ticker(position.symbol)
            current_price = ticker.last_price
            logger.info(f"Текущая цена: {current_price}")

            # Расчет прибыли
            if position.side == "Buy":
                profit_pct = ((current_price - position.entry_price) / position.entry_price) * 100
            else:
                profit_pct = ((position.entry_price - current_price) / position.entry_price) * 100

            logger.info(f"Текущая прибыль: {profit_pct:.2f}%")

            # 1. Проверка частичного закрытия
            logger.info("\n--- Проверка Partial TP ---")
            partial_tp_executed = await enhanced_manager.check_partial_tp(position)
            if partial_tp_executed:
                logger.success("✅ Частичное закрытие выполнено!")
            else:
                logger.info("Условия для частичного закрытия не выполнены")

            # 2. Проверка защиты прибыли
            logger.info("\n--- Проверка Profit Protection ---")
            profit_protection_updated = await enhanced_manager.update_profit_protection(
                position, current_price
            )
            if profit_protection_updated:
                logger.success("✅ Защита прибыли обновлена!")
            else:
                logger.info("Обновление защиты прибыли не требуется")

            # 3. Проверка трейлинг стопа
            logger.info("\n--- Проверка Trailing Stop ---")
            trailing_updated = await enhanced_manager.update_trailing_stop(position, current_price)
            if trailing_updated:
                logger.success("✅ Трейлинг стоп обновлен!")
            else:
                logger.info("Обновление трейлинг стопа не требуется")

            # Проверка истории partial TP
            logger.info("\n--- История Partial TP ---")
            history = await AsyncPGPool.fetch(
                """
                SELECT * FROM partial_tp_history
                WHERE trade_id = $1
                ORDER BY created_at DESC
                """,
                position.id if hasattr(position, "id") else 0,
            )

            if history:
                for record in history:
                    logger.info(
                        f"Level {record['level']}: "
                        f"{record['percent']}% @ {record['price']} "
                        f"(Status: {record['status']})"
                    )
            else:
                logger.info("История partial TP пуста")

        logger.success("\n✅ Тестирование Enhanced SL/TP завершено!")

    except Exception as e:
        logger.error(f"Ошибка тестирования: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Закрытие соединений
        if "exchange_client" in locals():
            await exchange_client.disconnect()
        await AsyncPGPool.close()


if __name__ == "__main__":
    # Загрузка переменных окружения
    from dotenv import load_dotenv

    load_dotenv()

    # Запуск тестирования
    asyncio.run(test_enhanced_sltp())
