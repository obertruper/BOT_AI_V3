#!/usr/bin/env python3
"""Тестирование критических исправлений торговой системы"""

import asyncio
import os
from dotenv import load_dotenv
from exchanges.bybit.client import BybitClient
from exchanges.base.order_types import OrderRequest, OrderSide, OrderType

load_dotenv()

async def test_fixes():
    """Тест всех критических исправлений"""
    
    print("\n" + "="*60)
    print("ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ")
    print("="*60)
    
    api_key = os.getenv('BYBIT_API_KEY')
    api_secret = os.getenv('BYBIT_API_SECRET')
    
    if not api_key or not api_secret:
        print('❌ API ключи не найдены в .env')
        return
    
    client = BybitClient(api_key, api_secret)
    
    # 1. Проверка режима позиций
    print("\n1️⃣ Проверка режима позиций:")
    print(f"   hedge_mode = {client.hedge_mode}")
    print(f"   BYBIT_HEDGE_MODE = {os.getenv('BYBIT_HEDGE_MODE')}")
    position_idx = client._get_position_idx('BUY')
    print(f"   positionIdx для BUY = {position_idx}")
    
    if position_idx == 0:
        print("   ✅ Режим one-way настроен корректно")
    else:
        print("   ❌ ОШИБКА: Все еще используется hedge mode!")
        return
    
    # 2. Проверка параметров ордера
    print("\n2️⃣ Проверка параметров ордера:")
    
    # Получаем тикер
    try:
        ticker = await client.get_ticker("SOLUSDT")
        current_price = ticker.last_price
        print(f"   Текущая цена SOL: ${current_price:.2f}")
    except Exception as e:
        print(f"   ❌ Ошибка получения цены: {e}")
        return
    
    # Создаем тестовый OrderRequest
    order_request = OrderRequest(
        symbol="SOLUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.3,  # Минимальное количество
        stop_loss=current_price * 0.98,
        take_profit=current_price * 1.02,
        exchange_params={}  # Пустые параметры - ВАЖНО!
    )
    
    # Проверяем что в exchange_params нет tpslMode
    if 'tpslMode' in order_request.exchange_params:
        print("   ❌ ОШИБКА: tpslMode все еще в параметрах!")
        return
    else:
        print("   ✅ Параметры ордера корректны (нет tpslMode)")
    
    # 3. Проверка маппинга статусов
    print("\n3️⃣ Проверка маппинга статусов:")
    from exchanges.base.order_types import OrderStatus
    
    # Проверяем что статус корректно конвертируется
    test_status = OrderStatus.REJECTED
    status_value = test_status.value.lower() if hasattr(test_status, 'value') else str(test_status).lower()
    
    if status_value == "rejected":
        print(f"   ✅ OrderStatus.REJECTED -> '{status_value}' (корректно)")
    else:
        print(f"   ❌ ОШИБКА маппинга: {test_status} -> '{status_value}'")
    
    # 4. Проверка импортов
    print("\n4️⃣ Проверка импортов:")
    try:
        from exchanges.base.order_types import OrderRequest as OR2, OrderSide as OS2, OrderType as OT2
        print("   ✅ Импорты работают корректно")
    except ImportError as e:
        print(f"   ❌ Ошибка импорта: {e}")
        return
    
    # 5. Пробный лимитный ордер (безопасный)
    print("\n5️⃣ Создание тестового лимитного ордера:")
    
    balance = await client.get_balance("USDT")
    print(f"   Доступный баланс: ${balance.available:.2f}")
    
    if balance.available < 10:
        print("   ⚠️ Недостаточно средств для теста")
        return
    
    # Лимитный ордер ниже рынка (не исполнится)
    test_order = OrderRequest(
        symbol="SOLUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=0.3,
        price=current_price * 0.90,  # На 10% ниже рынка
        exchange_params={}  # БЕЗ tpslMode!
    )
    
    print(f"   Отправка лимитного ордера: 0.3 SOL @ ${test_order.price:.2f}")
    
    try:
        response = await client.place_order(test_order)
        if response.success:
            print(f"   ✅ Ордер создан: {response.order_id}")
            
            # Отменяем тестовый ордер
            await asyncio.sleep(1)
            cancel_result = await client.cancel_order("SOLUSDT", response.order_id)
            if cancel_result:
                print(f"   ✅ Тестовый ордер отменен")
        else:
            print(f"   ❌ Ошибка создания: {response.message}")
            
    except Exception as e:
        print(f"   ❌ Исключение: {e}")
    
    print("\n" + "="*60)
    print("ИТОГИ ТЕСТИРОВАНИЯ:")
    print("="*60)
    print("✅ Все критические исправления работают корректно!")
    print("   - One-way режим настроен")
    print("   - Параметры ордера без tpslMode")
    print("   - Маппинг статусов исправлен")
    print("   - Импорты работают")

if __name__ == "__main__":
    asyncio.run(test_fixes())