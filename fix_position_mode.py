#!/usr/bin/env python3
"""
Скрипт для проверки и исправления режима позиций на Bybit
"""
import asyncio
import sys
import os
sys.path.append('.')

import ccxt.pro as ccxt
from dotenv import load_dotenv

load_dotenv()

async def check_and_fix_position_mode():
    """Проверка и исправление режима позиций"""
    
    api_key = os.getenv('BYBIT_API_KEY')
    api_secret = os.getenv('BYBIT_API_SECRET')
    
    exchange = ccxt.bybit({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'swap',
            'accountType': 'unified'
        }
    })
    
    try:
        print("🔍 Проверка режима позиций на Bybit...")
        
        # Получаем информацию об аккаунте
        balance = await exchange.fetch_balance()
        print(f"💰 Баланс USDT: {balance.get('USDT', {}).get('total', 0):.2f}")
        print(f"   Доступно: {balance.get('USDT', {}).get('free', 0):.2f}")
        
        # Получаем открытые позиции
        positions = await exchange.fetch_positions()
        print(f"\n📊 Открытых позиций: {len(positions)}")
        
        for pos in positions:
            print(f"   - {pos['symbol']}: {pos['side']} {pos['contracts']} контрактов")
            if 'info' in pos and 'positionIdx' in pos['info']:
                print(f"     positionIdx: {pos['info']['positionIdx']}")
        
        # Пробуем получить режим позиций через API
        print("\n🔧 Проверка режима позиций...")
        
        # Тестовый запрос для определения режима
        # Создаем минимальный ордер для BTCUSDT
        test_symbol = 'BTC/USDT:USDT'
        
        # Пробуем с positionIdx=0 (one-way mode)
        print("\n📝 Тест с one-way mode (positionIdx=0)...")
        try:
            # Проверяем минимальный размер ордера
            markets = await exchange.load_markets()
            market = markets[test_symbol]
            min_qty = market['limits']['amount']['min']
            print(f"   Минимальный размер: {min_qty}")
            
            # Делаем запрос без positionIdx (эквивалентно positionIdx=0)
            ticker = await exchange.fetch_ticker(test_symbol)
            price = ticker['last']
            
            # Рассчитываем минимальное количество для 6 USDT
            min_order_value = 6  # USDT
            min_contracts = min_order_value / price
            
            print(f"   Текущая цена: {price:.2f}")
            print(f"   Минимальное количество: {min_contracts:.6f}")
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
        
        # Проверяем настройки через приватный API
        print("\n🔍 Проверка настроек аккаунта...")
        try:
            # Используем прямой API запрос для получения информации об аккаунте
            account_info = await exchange.private_get_v5_account_info()
            if 'result' in account_info:
                unified_margin_status = account_info['result'].get('unifiedMarginStatus')
                print(f"   Unified Margin Status: {unified_margin_status}")
                
                # Проверяем режим маржи
                margin_mode = account_info['result'].get('marginMode', 'UNKNOWN')
                print(f"   Margin Mode: {margin_mode}")
        except Exception as e:
            print(f"   Не удалось получить информацию об аккаунте: {e}")
        
        # Определяем рекомендуемый режим
        print("\n✅ Рекомендации:")
        if len(positions) > 0:
            # Анализируем существующие позиции
            has_hedge_positions = any(
                pos.get('info', {}).get('positionIdx', 0) != 0 
                for pos in positions
            )
            
            if has_hedge_positions:
                print("   ➡️ Обнаружены позиции в HEDGE режиме")
                print("   ➡️ Установите BYBIT_HEDGE_MODE=true в .env")
            else:
                print("   ➡️ Обнаружены позиции в ONE-WAY режиме")
                print("   ➡️ Установите BYBIT_HEDGE_MODE=false в .env")
        else:
            print("   ➡️ Нет открытых позиций")
            print("   ➡️ Рекомендуется использовать ONE-WAY режим")
            print("   ➡️ Установите BYBIT_HEDGE_MODE=false в .env")
        
        # Проверяем текущую настройку
        current_hedge_mode = os.getenv('BYBIT_HEDGE_MODE', 'false').lower() == 'true'
        print(f"\n📋 Текущая настройка BYBIT_HEDGE_MODE: {current_hedge_mode}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(check_and_fix_position_mode())