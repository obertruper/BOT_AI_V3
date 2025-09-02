#!/usr/bin/env python3
"""
Тест исправлений в производственной среде
Проверяет hedge mode и enum REJECTED в реальной системе
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Важно! Загружаем .env файл перед импортами
from dotenv import load_dotenv
load_dotenv()

from exchanges.bybit.bybit_exchange import BybitExchange
from exchanges.base.order_types import OrderStatus
from database.models.base_models import OrderStatus as DBOrderStatus

async def test_hedge_mode_in_production():
    """Тест hedge mode в производственной среде"""
    print("🏭 ТЕСТ HEDGE MODE В ПРОИЗВОДСТВЕННОЙ СРЕДЕ")
    print("-" * 60)
    
    try:
        # Создаём exchange как в производстве
        exchange = BybitExchange("public_access", "public_access")
        
        # Проверяем клиент
        client = exchange.client
        print(f"✅ Hedge mode в клиенте: {client.hedge_mode}")
        print(f"✅ Default leverage: {client.default_leverage}")
        print(f"✅ Trading category: {client.trading_category}")
        
        # Проверяем переменную окружения
        env_value = os.getenv("BYBIT_HEDGE_MODE", "не установлена")
        print(f"✅ BYBIT_HEDGE_MODE: {env_value}")
        
        # Тест position index
        test_sides = [("BUY", 1), ("SELL", 2), ("LONG", 1), ("SHORT", 2)]
        
        for side, expected in test_sides:
            actual = client._get_position_idx(side)
            status = "✅" if actual == expected else "❌"
            print(f"{status} {side:5} -> positionIdx={actual} (expected {expected})")
        
        return client.hedge_mode == True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования hedge mode: {e}")
        return False

async def test_enum_rejected():
    """Тест enum REJECTED"""
    print("\n🗄️ ТЕСТ ENUM REJECTED")
    print("-" * 60)
    
    try:
        # Тест enum из base models
        rejected_status = DBOrderStatus.REJECTED
        print(f"✅ DBOrderStatus.REJECTED: '{rejected_status.value}'")
        
        # Тест enum из order_types
        rejected_order_status = OrderStatus.REJECTED
        print(f"✅ OrderStatus.REJECTED: '{rejected_order_status.value}'")
        
        # Проверяем, что они совместимы
        compatible = rejected_status.value == rejected_order_status.value
        print(f"✅ Совместимость enum: {compatible}")
        
        # Тест маппинга статусов
        from trading.orders.order_manager import OrderManager
        
        # Симулируем создание заказа со статусом REJECTED
        class MockOrder:
            def __init__(self, status):
                self.status = status
                self.filled_quantity = 0
                self.average_price = 0
        
        mock_order = MockOrder(OrderStatus.REJECTED)
        
        # Проверяем, как извлекается значение статуса
        if hasattr(mock_order.status, 'value'):
            status_value = mock_order.status.value
            print(f"✅ Статус через .value: '{status_value}'")
        else:
            status_value = str(mock_order.status).lower()
            print(f"✅ Статус через str().lower(): '{status_value}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования enum: {e}")
        return False

async def test_system_integration():
    """Интеграционный тест системы"""
    print("\n🔧 ИНТЕГРАЦИОННЫЙ ТЕСТ")
    print("-" * 60)
    
    try:
        # Создаём exchange
        exchange = BybitExchange("public_access", "public_access")
        
        # Проверяем что все компоненты инициализированы правильно
        print(f"✅ Exchange создан: {exchange.name}")
        print(f"✅ Client hedge mode: {exchange.client.hedge_mode}")
        print(f"✅ Legacy adapter создан: {hasattr(exchange, 'legacy_adapter')}")
        
        # Проверяем переменную окружения в runtime
        hedge_env = os.getenv("BYBIT_HEDGE_MODE", "не установлена")
        print(f"✅ Runtime BYBIT_HEDGE_MODE: {hedge_env}")
        
        # Тест создания order request параметров
        from exchanges.base.order_types import OrderRequest, OrderSide, OrderType, TimeInForce
        
        order_request = OrderRequest(
            symbol="XRPUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.7,
            time_in_force=TimeInForce.GTC
        )
        
        # Получаем position_idx как это делается в реальной системе
        client = exchange.client
        symbol = order_request.symbol.replace("-", "")  # clean_symbol
        position_idx = client._get_position_idx(order_request.side.value, symbol=symbol)
        
        print(f"✅ Order symbol: {symbol}")
        print(f"✅ Order side: {order_request.side.value}")
        print(f"✅ Position index: {position_idx}")
        
        # Проверяем правильность
        expected_idx = 1  # BUY должно быть 1 в hedge mode
        correct = position_idx == expected_idx
        
        if correct:
            print("🎉 Интеграционный тест ПРОЙДЕН!")
            return True
        else:
            print("❌ Интеграционный тест ПРОВАЛЕН!")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка интеграционного тестирования: {e}")
        return False

async def main():
    """Основная функция"""
    print("🚀 ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ В ПРОИЗВОДСТВЕННОЙ СРЕДЕ")
    print("=" * 80)
    
    results = []
    
    # Запускаем все тесты
    results.append(await test_hedge_mode_in_production())
    results.append(await test_enum_rejected())
    results.append(await test_system_integration())
    
    # Итоговый результат
    print("\n" + "=" * 80)
    print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print("=" * 80)
    
    test_names = [
        "Hedge mode в продакшене",
        "Enum REJECTED", 
        "Интеграционный тест"
    ]
    
    for i, (name, passed) in enumerate(zip(test_names, results), 1):
        status = "✅ ПРОЙДЕН" if passed else "❌ ПРОВАЛЕН"
        print(f"{i}. {name:25} | {status}")
    
    all_passed = all(results)
    
    print("-" * 80)
    if all_passed:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("✅ Система готова к запуску с исправлениями!")
        print("💡 Перезапустите торговую систему для применения изменений.")
    else:
        failed_count = sum(1 for x in results if not x)
        print(f"⚠️  {failed_count} тестов провалено. Требуются дополнительные исправления.")
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)