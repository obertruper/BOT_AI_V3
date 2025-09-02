#!/usr/bin/env python3
"""Тестирование исправления positionIdx и создания ордеров"""

import asyncio
import os
from dotenv import load_dotenv
from exchanges.bybit.client import BybitClient
from exchanges.base.order_types import OrderRequest, OrderSide, OrderType, TimeInForce

# Загружаем переменные окружения
load_dotenv()

async def test_order_creation():
    """Тест создания минимального ордера с правильным positionIdx"""
    
    api_key = os.getenv('BYBIT_API_KEY')
    api_secret = os.getenv('BYBIT_API_SECRET')
    
    if not api_key or not api_secret:
        print('❌ API ключи не найдены в .env')
        return
    
    client = BybitClient(api_key, api_secret)
    
    # 1. Проверяем конфигурацию
    print("\n=== Проверка конфигурации ===")
    print(f"Hedge mode из конфига: {client.hedge_mode}")
    print(f"BYBIT_HEDGE_MODE из env: {os.getenv('BYBIT_HEDGE_MODE', 'not set')}")
    print(f"Default leverage: {client.default_leverage}")
    
    # 2. Проверяем баланс
    print("\n=== Проверка баланса ===")
    try:
        balance = await client.get_balance("USDT")
        print(f"Общий баланс: ${balance.total:.2f}")
        print(f"Доступный баланс: ${balance.available:.2f}")
        print(f"Используется: ${balance.frozen:.2f}")
        
        if balance.available < 15:
            print(f"⚠️ Недостаточно средств для тестового ордера (нужно минимум $15)")
            return
    except Exception as e:
        print(f"Ошибка получения баланса: {e}")
        return
    
    # 3. Получаем текущую цену BTCUSDT
    print("\n=== Получение рыночной цены ===")
    try:
        ticker = await client.get_ticker("BTCUSDT")
        current_price = ticker.last_price
        print(f"Текущая цена BTC: ${current_price:.2f}")
    except Exception as e:
        print(f"Ошибка получения тикера: {e}")
        return
    
    # 4. Рассчитываем размер позиции для минимального ордера
    min_order_value = 15.0  # Минимум 15 USDT для безопасности
    leverage = 5
    quantity = (min_order_value / current_price)
    
    print(f"\n=== Параметры тестового ордера ===")
    print(f"Символ: BTCUSDT")
    print(f"Тип: LIMIT (лимитный)")
    print(f"Сторона: BUY")
    print(f"Количество: {quantity:.6f} BTC")
    print(f"Цена: ${current_price * 0.95:.2f} (на 5% ниже рынка)")
    print(f"Leverage: {leverage}x")
    print(f"Стоимость позиции: ${quantity * current_price:.2f}")
    print(f"Требуемая маржа: ${(quantity * current_price / leverage):.2f}")
    
    # 5. Проверяем positionIdx который будет использован
    position_idx = client._get_position_idx("BUY")
    print(f"\n=== Проверка positionIdx ===")
    print(f"PositionIdx для BUY: {position_idx}")
    print(f"Режим: {'One-way' if position_idx == 0 else 'Hedge'}")
    
    # 6. Создаем тестовый лимитный ордер (ниже рынка, чтобы не исполнился)
    print("\n=== Создание тестового ордера ===")
    
    # Подготавливаем запрос
    order_request = OrderRequest(
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=quantity,
        price=current_price * 0.95,  # На 5% ниже рынка
        time_in_force=TimeInForce.GTC,
        leverage=leverage
    )
    
    print("Отправка ордера...")
    
    try:
        response = await client.place_order(order_request)
        
        if response.success:
            print(f"✅ Ордер создан успешно!")
            print(f"   Order ID: {response.order_id}")
            print(f"   Status: {response.status}")
            
            # Отменяем тестовый ордер
            if response.order_id:
                await asyncio.sleep(1)
                print("\n=== Отмена тестового ордера ===")
                try:
                    cancel_result = await client.cancel_order("BTCUSDT", response.order_id)
                    if cancel_result:
                        print(f"✅ Ордер {response.order_id} отменен")
                    else:
                        print(f"⚠️ Не удалось отменить ордер")
                except Exception as e:
                    print(f"Ошибка при отмене: {e}")
        else:
            print(f"❌ Ошибка создания ордера: {response.message}")
            
    except Exception as e:
        print(f"❌ Исключение при создании ордера: {e}")
    
    print("\n=== Тест завершен ===")

if __name__ == "__main__":
    asyncio.run(test_order_creation())