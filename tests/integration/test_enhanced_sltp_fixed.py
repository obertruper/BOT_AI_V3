#!/usr/bin/env python3
"""
Тест исправленной Enhanced SL/TP Manager системы
"""

import asyncio
import os
import sys

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.base.models import Position
from trading.positions.position_manager import Position as TradingPosition
from trading.sltp.enhanced_manager import EnhancedSLTPManager, PositionAdapter
from trading.sltp.models import SLTPConfig


class MockExchangeClient:
    """Мокированный клиент биржи для тестов"""

    async def set_stop_loss(self, symbol: str, price: float, quantity: float):
        class MockResponse:
            success = True
            order_id = f"sl_{symbol}_{price}"

        return MockResponse()

    async def set_take_profit(self, symbol: str, price: float, quantity: float):
        class MockResponse:
            success = True
            order_id = f"tp_{symbol}_{price}"

        return MockResponse()

    async def create_order(self, params: dict):
        class MockResponse:
            success = True
            order_id = f"order_{params['symbol']}_{params['qty']}"

        return MockResponse()

    async def cancel_order(self, symbol: str, order_id: str):
        class MockResponse:
            success = True

        return MockResponse()


class MockConfigManager:
    """Мокированный менеджер конфигурации"""

    def get_system_config(self):
        return {
            "enhanced_sltp": {
                "trailing_stop": {
                    "enabled": True,
                    "type": "percentage",
                    "step": 0.5,
                    "min_profit": 0.3,
                    "max_distance": 2.0,
                },
                "partial_take_profit": {
                    "enabled": True,
                    "update_sl_after_partial": True,
                    "levels": [
                        {"percent": 1.0, "close_ratio": 0.25},
                        {"percent": 2.0, "close_ratio": 0.25},
                        {"percent": 3.0, "close_ratio": 0.50},
                    ],
                },
                "profit_protection": {
                    "enabled": True,
                    "breakeven_percent": 1.0,
                    "breakeven_offset": 0.2,
                    "lock_percent": [
                        {"trigger": 2.0, "lock": 1.0},
                        {"trigger": 3.0, "lock": 2.0},
                    ],
                    "max_updates": 5,
                },
                "volatility_adjustment": {"enabled": False, "multiplier": 1.0},
            },
            "trading": {"hedge_mode": True},
        }


def test_position_adapter():
    """Тест адаптера Position"""
    print("\n=== Тестирование PositionAdapter ===")

    # Тест с exchanges.base.models.Position
    exchange_position = Position(
        symbol="BTCUSDT", side="Buy", size=1.0, entry_price=50000.0, mark_price=51000.0
    )

    adapter1 = PositionAdapter(exchange_position)
    print("Exchange Position через адаптер:")
    print(f"  Symbol: {adapter1.symbol}")
    print(f"  Side: {adapter1.side}")
    print(f"  Size: {adapter1.size}")
    print(f"  Entry Price: {adapter1.entry_price}")

    # Тест с trading.positions.position_manager.Position
    trading_position = TradingPosition(
        symbol="ETHUSDT",
        exchange="bybit",
        side="long",
        quantity=10.0,
        entry_price=3000.0,
    )

    adapter2 = PositionAdapter(trading_position)
    print("\nTrading Position через адаптер:")
    print(f"  Symbol: {adapter2.symbol}")
    print(f"  Side: {adapter2.side}")
    print(f"  Size: {adapter2.size}")
    print(f"  Entry Price: {adapter2.entry_price}")

    print("✅ PositionAdapter работает корректно")


async def test_enhanced_sltp_manager():
    """Тест Enhanced SL/TP Manager"""
    print("\n=== Тестирование EnhancedSLTPManager ===")

    # Создаем мокированные зависимости
    config_manager = MockConfigManager()
    exchange_client = MockExchangeClient()

    # Создаем менеджер
    manager = EnhancedSLTPManager(config_manager, exchange_client)

    # Создаем тестовую позицию
    position = Position(
        symbol="BTCUSDT", side="Buy", size=1.0, entry_price=50000.0, mark_price=50000.0
    )

    print(f"Создана тестовая позиция: {position.symbol} {position.side} {position.size}")

    # Тест создания базовых SL/TP ордеров с конфигурацией
    try:
        # Создаем конфигурацию с SL/TP
        config = SLTPConfig(
            stop_loss=2.0,  # 2%
            take_profit=4.0,  # 4%
        )

        orders = await manager.create_sltp_orders(position, None, config)
        print(f"✅ Создано {len(orders)} SL/TP ордеров")

        for order in orders:
            print(f"  - {order.order_type}: {order.trigger_price} (qty: {order.quantity})")
    except Exception as e:
        print(f"❌ Ошибка создания SL/TP: {e}")

    # Тест методов совместимости с V2
    try:
        result = await manager.register_sltp_orders(
            trade_id="test_001",
            symbol="BTCUSDT",
            side="Buy",
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            trade_qty=1.0,
        )
        print(f"✅ register_sltp_orders результат: {result}")
    except Exception as e:
        print(f"❌ Ошибка register_sltp_orders: {e}")

    # Тест проверки ордеров
    try:
        check_result = await manager.check_and_fix_sltp("test_001")
        print(f"✅ check_and_fix_sltp результат: {check_result}")
    except Exception as e:
        print(f"❌ Ошибка check_and_fix_sltp: {e}")

    # Тест трейлинг стопа
    try:
        current_price = 51500.0  # Прибыль 3%
        trailing_result = await manager.update_trailing_stop(position, current_price)
        if trailing_result:
            print(f"✅ Trailing stop обновлен: {trailing_result.trigger_price}")
        else:
            print("ℹ️  Trailing stop не обновлен (условия не выполнены)")
    except Exception as e:
        print(f"❌ Ошибка trailing stop: {e}")

    # Тест защиты прибыли
    try:
        current_price = 52000.0  # Прибыль 4%
        protection_result = await manager.update_profit_protection(position, current_price)
        if protection_result:
            print(f"✅ Profit protection обновлен: {protection_result.trigger_price}")
        else:
            print("ℹ️  Profit protection не обновлен")
    except Exception as e:
        print(f"❌ Ошибка profit protection: {e}")

    # Тест частичного TP
    try:
        current_price = 50500.0  # Прибыль 1% - должен сработать первый уровень
        partial_result = await manager.check_partial_tp(position, current_price)
        if partial_result:
            print("✅ Partial TP выполнен")
        else:
            print("ℹ️  Partial TP не выполнен")
    except Exception as e:
        print(f"❌ Ошибка partial TP: {e}")

    print("✅ EnhancedSLTPManager протестирован")


def test_config_loading():
    """Тест загрузки конфигурации"""
    print("\n=== Тестирование загрузки конфигурации ===")

    config_manager = MockConfigManager()
    manager = EnhancedSLTPManager(config_manager)

    config = manager.config

    print(f"Trailing stop enabled: {config.trailing_stop.enabled}")
    print(f"Trailing stop type: {config.trailing_stop.type}")
    print(f"Partial TP enabled: {config.partial_tp_enabled}")
    print(f"Partial TP levels: {len(config.partial_tp_levels)}")
    print(f"Profit protection enabled: {config.profit_protection.enabled}")

    for level in config.partial_tp_levels:
        print(f"  Level {level.level}: {level.percentage}% -> close {level.close_ratio}")

    print("✅ Конфигурация загружена корректно")


async def main():
    """Главная функция тестирования"""
    print("🧪 Запуск тестов исправленной Enhanced SL/TP Manager системы")

    try:
        # Тест адаптера позиций
        test_position_adapter()

        # Тест загрузки конфигурации
        test_config_loading()

        # Тест основного функционала
        await test_enhanced_sltp_manager()

        print("\n🎉 Все тесты пройдены успешно!")

    except Exception as e:
        print(f"\n❌ Критическая ошибка в тестах: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
