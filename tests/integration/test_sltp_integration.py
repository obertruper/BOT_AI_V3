#!/usr/bin/env python3
"""
Тест интеграции SL/TP с торговой системой
"""

import asyncio
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_sltp_integration():
    """Тест полной интеграции SL/TP"""
    try:
        # 1. Инициализация компонентов
        logger.info("🔧 Инициализация компонентов...")

        from core.config.config_manager import ConfigManager
        from database.models.base_models import Order, OrderSide, OrderStatus, OrderType
        from exchanges.exchange_manager import ExchangeManager
        from trading.orders.order_manager import OrderManager
        from trading.sltp.enhanced_manager import EnhancedSLTPManager

        # Конфигурация
        config_manager = ConfigManager()
        config = config_manager.get_config()

        # Exchange Manager
        exchange_manager = ExchangeManager(config)
        await exchange_manager.initialize()

        # Enhanced SL/TP Manager
        sltp_manager = EnhancedSLTPManager(config_manager=config_manager)

        # Order Manager с SL/TP
        order_manager = OrderManager(exchange_registry=exchange_manager, sltp_manager=sltp_manager)

        logger.info("✅ Компоненты инициализированы")

        # 2. Создание тестового ордера
        logger.info("\n📊 Создание тестового ордера...")

        test_order = Order(
            exchange="bybit",
            symbol="BTCUSDT",
            order_id="test_order_001",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            status=OrderStatus.PENDING,
            price=50000.0,
            quantity=0.001,
            strategy_name="test_strategy",
            trader_id="test_trader",
            created_at=datetime.utcnow(),
            metadata={"stop_loss_pct": 0.02, "take_profit_pct": 0.04},  # 2%  # 4%
        )

        # Добавляем в активные ордера
        order_manager._active_orders[test_order.order_id] = test_order

        logger.info(
            f"✅ Создан ордер: {test_order.symbol} {test_order.side.value} {test_order.quantity}"
        )

        # 3. Симуляция исполнения ордера
        logger.info("\n🎯 Симуляция исполнения ордера...")

        # Создаем mock exchange для тестирования
        class MockExchange:
            async def place_order(self, order_request):
                logger.info(f"Mock: Размещение ордера {order_request}")
                # Возвращаем успешный результат
                from dataclasses import dataclass

                @dataclass
                class MockResponse:
                    success: bool = True
                    order_id: str = "mock_sl_tp_order"
                    error: str = None

                return MockResponse()

            async def set_stop_loss(self, symbol, price, size):
                logger.info(f"Mock: Установка SL для {symbol} на {price}")
                from dataclasses import dataclass

                @dataclass
                class MockResponse:
                    success: bool = True
                    order_id: str = f"mock_sl_{symbol}_{price}"

                return MockResponse()

            async def set_take_profit(self, symbol, price, size):
                logger.info(f"Mock: Установка TP для {symbol} на {price}")
                from dataclasses import dataclass

                @dataclass
                class MockResponse:
                    success: bool = True
                    order_id: str = f"mock_tp_{symbol}_{price}"

                return MockResponse()

        # Регистрируем mock exchange
        exchange_manager.exchanges["bybit"] = MockExchange()

        # Мокаем обновление в БД чтобы избежать дублирования
        async def mock_update_db(order):
            logger.info(f"Mock: Обновление ордера в БД {order.order_id}")

        order_manager._update_order_in_db = mock_update_db

        # Обновляем статус на FILLED
        await order_manager.update_order_status(
            order_id=test_order.order_id,
            new_status=OrderStatus.FILLED,
            filled_quantity=test_order.quantity,
            average_price=50000.0,
        )

        # Проверяем создание SL/TP
        if test_order.metadata and test_order.metadata.get("sltp_created"):
            logger.info("✅ SL/TP ордера созданы успешно!")
            logger.info(f"   - SL Order ID: {test_order.metadata.get('sl_order_id')}")
            logger.info(f"   - TP Order IDs: {test_order.metadata.get('tp_order_ids')}")
        else:
            logger.warning("⚠️ SL/TP ордера не были созданы")

        # 4. Тест обновления трейлинг стопа
        logger.info("\n📈 Тест обновления трейлинг стопа...")

        if order_manager.sltp_integration and test_order.metadata.get("position_id"):
            # Симулируем рост цены на 3%
            new_price = 50000.0 * 1.03  # 51500

            updated = await order_manager.sltp_integration.update_position_sltp(
                test_order.metadata["position_id"], new_price
            )

            if updated:
                logger.info(f"✅ Трейлинг стоп обновлен при цене {new_price}")
            else:
                logger.info("ℹ️ Трейлинг стоп не требует обновления")

        # 5. Тест частичного TP
        logger.info("\n💰 Тест частичного Take Profit...")

        if order_manager.sltp_integration and test_order.metadata.get("position_id"):
            # Симулируем достижение первого уровня TP (2%)
            tp_price = 50000.0 * 1.02  # 51000

            partial_executed = await order_manager.sltp_integration.check_partial_tp(
                test_order.metadata["position_id"], tp_price
            )

            if partial_executed:
                logger.info(f"✅ Частичный TP выполнен при цене {tp_price}")
            else:
                logger.info("ℹ️ Условия для частичного TP не выполнены")

        logger.info("\n✨ Тест интеграции завершен!")

    except Exception as e:
        logger.error(f"❌ Ошибка в тесте: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_sltp_integration())
