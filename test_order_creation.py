#!/usr/bin/env python3
"""
Тестирование создания ордеров на Bybit для диагностики ошибки 10001
"""

import asyncio
import os
import sys
from decimal import Decimal
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from exchanges.bybit import get_bybit_client
from core.logger import setup_logger
from dotenv import load_dotenv
import json

# Загружаем переменные окружения
load_dotenv()

logger = setup_logger("order_test")


async def test_order_creation(client: BybitClient):
    """Тестирование создания ордера с минимальными параметрами"""
    
    symbol = "BTCUSDT"
    
    try:
        # 1. Получаем информацию о символе
        logger.info(f"Getting instrument info for {symbol}...")
        params = {
            "category": "linear",
            "symbol": symbol
        }
        response = await client._make_request("GET", "/v5/market/instruments-info", params)
        
        if response.get("retCode") == 0:
            instruments = response.get("result", {}).get("list", [])
            if instruments:
                inst = instruments[0]
                logger.info(f"Symbol {symbol} info:")
                logger.info(f"  Min order qty: {inst.get('lotSizeFilter', {}).get('minOrderQty')}")
                logger.info(f"  Max order qty: {inst.get('lotSizeFilter', {}).get('maxOrderQty')}")
                logger.info(f"  Qty step: {inst.get('lotSizeFilter', {}).get('qtyStep')}")
                logger.info(f"  Price tick: {inst.get('priceFilter', {}).get('tickSize')}")
                
                min_qty = float(inst.get('lotSizeFilter', {}).get('minOrderQty', 0.001))
                qty_step = float(inst.get('lotSizeFilter', {}).get('qtyStep', 0.001))
        
        # 2. Получаем текущую цену
        logger.info(f"Getting current price for {symbol}...")
        params = {
            "category": "linear",
            "symbol": symbol
        }
        response = await client._make_request("GET", "/v5/market/tickers", params)
        
        current_price = 0
        if response.get("retCode") == 0:
            tickers = response.get("result", {}).get("list", [])
            if tickers:
                current_price = float(tickers[0].get("lastPrice", 0))
                logger.info(f"Current price: {current_price}")
        
        if current_price == 0:
            logger.error("Could not get current price")
            return
        
        # 3. Проверяем баланс
        logger.info("Getting account balance...")
        params = {
            "accountType": "UNIFIED"  # или CONTRACT для контрактного счета
        }
        response = await client._make_request("GET", "/v5/account/wallet-balance", params, auth=True)
        
        if response.get("retCode") == 0:
            accounts = response.get("result", {}).get("list", [])
            if accounts:
                account = accounts[0]
                usdt_balance = 0
                for coin in account.get("coin", []):
                    if coin.get("coin") == "USDT":
                        balance_str = coin.get("availableToWithdraw", "0")
                        if balance_str and balance_str != "":
                            usdt_balance = float(balance_str)
                        else:
                            usdt_balance = 0
                        logger.info(f"Available USDT balance: {usdt_balance}")
                        break
        
        # 4. Рассчитываем минимальный размер ордера
        min_order_value = min_qty * current_price
        logger.info(f"Minimum order value: {min_order_value} USDT")
        
        # 5. Пробуем создать минимальный тестовый ордер
        test_qty = max(min_qty, 0.001)  # Используем минимально возможное количество
        
        # Округляем количество согласно qty_step
        test_qty = round(test_qty / qty_step) * qty_step
        test_qty = f"{test_qty:.8f}".rstrip('0').rstrip('.')
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Creating test MARKET BUY order:")
        logger.info(f"  Symbol: {symbol}")
        logger.info(f"  Side: Buy")
        logger.info(f"  Quantity: {test_qty}")
        logger.info(f"  Order value: ~{float(test_qty) * current_price:.2f} USDT")
        logger.info(f"{'='*60}\n")
        
        # Создаем ордер с минимальными параметрами
        order_params = {
            "category": "linear",
            "symbol": symbol,
            "side": "Buy",
            "orderType": "Market",
            "qty": test_qty,
            "timeInForce": "IOC",  # Immediate or Cancel для рыночного ордера
            "positionIdx": 0  # One-way mode
        }
        
        logger.info(f"Order parameters: {json.dumps(order_params, indent=2)}")
        
        # Отправляем ордер
        response = await client._make_request("POST", "/v5/order/create", order_params, auth=True)
        
        logger.info(f"\nResponse: {json.dumps(response, indent=2)}")
        
        if response.get("retCode") == 0:
            logger.info("✅ Order created successfully!")
            order_id = response.get("result", {}).get("orderId")
            logger.info(f"Order ID: {order_id}")
            
            # Проверяем статус ордера
            if order_id:
                await asyncio.sleep(1)
                status_params = {
                    "category": "linear",
                    "orderId": order_id
                }
                status_response = await client._make_request("GET", "/v5/order/realtime", status_params, auth=True)
                if status_response.get("retCode") == 0:
                    orders = status_response.get("result", {}).get("list", [])
                    if orders:
                        order = orders[0]
                        logger.info(f"Order status: {order.get('orderStatus')}")
                        logger.info(f"Order filled qty: {order.get('cumExecQty')}")
                        logger.info(f"Order avg price: {order.get('avgPrice')}")
        else:
            logger.error(f"❌ Order creation failed!")
            logger.error(f"Error code: {response.get('retCode')}")
            logger.error(f"Error message: {response.get('retMsg')}")
            
            # Анализ ошибки 10001
            if response.get("retCode") == 10001:
                logger.info("\n" + "="*60)
                logger.info("Error 10001 Analysis:")
                logger.info("This error means 'Parameter verification failed'")
                logger.info("Common causes:")
                logger.info("1. Invalid symbol format")
                logger.info("2. Invalid quantity (too small, too large, wrong decimal places)")
                logger.info("3. Invalid side (must be 'Buy' or 'Sell')")
                logger.info("4. Invalid orderType (must be 'Market', 'Limit', etc.)")
                logger.info("5. Missing required parameters")
                logger.info("6. Wrong positionIdx for account mode")
                logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def main():
    """Главная функция"""
    logger.info("=" * 60)
    logger.info("Bybit Order Creation Test")
    logger.info("=" * 60)
    
    # Создаем клиента Bybit
    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")
    
    if not api_key or not api_secret:
        logger.error("Bybit API credentials not found in environment")
        return
    
    client = get_bybit_client(
        api_key=api_key,
        api_secret=api_secret,
        sandbox=False
    )
    
    # Тестируем создание ордера
    await test_order_creation(client)
    
    # Закрываем сессию
    if hasattr(client, 'session'):
        await client.session.close()
    
    logger.info("\n" + "=" * 60)
    logger.info("Test completed")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())