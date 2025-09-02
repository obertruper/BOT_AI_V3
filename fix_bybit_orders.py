#!/usr/bin/env python3
"""
Исправление проблем с созданием ордеров на Bybit
"""

import asyncio
import os
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from exchanges.bybit import get_bybit_client
from core.logger import setup_logger
from dotenv import load_dotenv
import json

# Загружаем переменные окружения
load_dotenv()

logger = setup_logger("bybit_fix")


async def check_account_mode(client: BybitClient):
    """Проверка режима аккаунта и настроек"""
    try:
        # 1. Проверяем настройки аккаунта
        logger.info("Checking account settings...")
        
        # Получаем информацию о счете
        response = await client._make_request(
            "GET", 
            "/v5/account/info",
            auth=True
        )
        
        if response.get("retCode") == 0:
            result = response.get("result", {})
            logger.info(f"Account UID: {result.get('uid')}")
            logger.info(f"Account type: {result.get('accountType')}")
            logger.info(f"Unified margin status: {result.get('unifiedMarginStatus')}")
            logger.info(f"Margin mode: {result.get('marginMode')}")
            
        # 2. Проверяем позиционный режим
        symbols = ["BTCUSDT", "ETHUSDT"]
        
        for symbol in symbols:
            logger.info(f"\nChecking position mode for {symbol}...")
            
            # Получаем текущие позиции
            positions = await client.get_positions(symbol)
            
            if positions:
                for pos in positions:
                    position_idx = pos.get("positionIdx", 0)
                    logger.info(f"Position found: {symbol}")
                    logger.info(f"  Position Index: {position_idx} (0=OneWay, 1=BuyHedge, 2=SellHedge)")
                    logger.info(f"  Side: {pos.get('side')}")
                    logger.info(f"  Size: {pos.get('size')}")
                    logger.info(f"  Leverage: {pos.get('leverage')}")
            else:
                logger.info(f"No open positions for {symbol}")
                
            # Пробуем получить информацию о режиме позиций
            try:
                params = {
                    "category": "linear",
                    "symbol": symbol
                }
                response = await client._make_request(
                    "GET",
                    "/v5/account/position-mode",
                    params,
                    auth=True
                )
                
                if response.get("retCode") == 0:
                    mode = response.get("result", {}).get("mode")
                    logger.info(f"Position mode for {symbol}: {mode} (0=MergedSingle, 3=BothSides)")
            except Exception as e:
                logger.warning(f"Could not get position mode: {e}")
                
    except Exception as e:
        logger.error(f"Error checking account mode: {e}")


async def fix_order_parameters(client: BybitClient, symbol: str = "BTCUSDT"):
    """Исправление параметров создания ордера"""
    try:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing order creation for {symbol}")
        logger.info(f"{'='*60}")
        
        # 1. Получаем информацию об инструменте
        instrument_info = await client.get_instrument_info(symbol)
        logger.info(f"Min qty: {instrument_info.min_order_qty}")
        logger.info(f"Qty step: {instrument_info.qty_step}")
        logger.info(f"Tick size: {instrument_info.tick_size}")
        
        # 2. Получаем текущую цену
        ticker = await client.get_ticker(symbol)
        current_price = ticker.last_price
        logger.info(f"Current price: {current_price}")
        
        # 3. Формируем минимальный ордер
        min_qty = max(instrument_info.min_order_qty, 0.001)
        
        # Округляем количество по qty_step
        from decimal import Decimal, ROUND_DOWN
        qty_decimal = Decimal(str(min_qty))
        step_decimal = Decimal(str(instrument_info.qty_step))
        rounded_qty = (qty_decimal / step_decimal).quantize(Decimal('1'), rounding=ROUND_DOWN) * step_decimal
        formatted_qty = str(rounded_qty)
        
        logger.info(f"Order quantity: {formatted_qty}")
        
        # 4. Пробуем разные варианты параметров
        test_configs = [
            # Вариант 1: One-way mode без positionIdx
            {
                "name": "One-way without positionIdx",
                "params": {
                    "category": "linear",
                    "symbol": symbol,
                    "side": "Buy",
                    "orderType": "Market",
                    "qty": formatted_qty,
                    "timeInForce": "IOC"
                }
            },
            # Вариант 2: One-way mode с positionIdx=0
            {
                "name": "One-way with positionIdx=0",
                "params": {
                    "category": "linear",
                    "symbol": symbol,
                    "side": "Buy",
                    "orderType": "Market",
                    "qty": formatted_qty,
                    "timeInForce": "IOC",
                    "positionIdx": 0
                }
            },
            # Вариант 3: Hedge mode Buy side
            {
                "name": "Hedge mode Buy (positionIdx=1)",
                "params": {
                    "category": "linear",
                    "symbol": symbol,
                    "side": "Buy",
                    "orderType": "Market",
                    "qty": formatted_qty,
                    "timeInForce": "IOC",
                    "positionIdx": 1
                }
            },
            # Вариант 4: С reduceOnly
            {
                "name": "With reduceOnly=false",
                "params": {
                    "category": "linear",
                    "symbol": symbol,
                    "side": "Buy",
                    "orderType": "Market",
                    "qty": formatted_qty,
                    "timeInForce": "IOC",
                    "reduceOnly": False
                }
            }
        ]
        
        for config in test_configs:
            logger.info(f"\n--- Testing: {config['name']} ---")
            logger.info(f"Parameters: {json.dumps(config['params'], indent=2)}")
            
            try:
                response = await client._make_request(
                    "POST",
                    "/v5/order/create",
                    config['params'],
                    auth=True
                )
                
                if response.get("retCode") == 0:
                    logger.info(f"✅ SUCCESS! Order created with {config['name']}")
                    order_id = response.get("result", {}).get("orderId")
                    logger.info(f"Order ID: {order_id}")
                    
                    # Отменяем тестовый ордер
                    if order_id:
                        await asyncio.sleep(0.5)
                        try:
                            cancel_params = {
                                "category": "linear",
                                "symbol": symbol,
                                "orderId": order_id
                            }
                            cancel_response = await client._make_request(
                                "POST",
                                "/v5/order/cancel",
                                cancel_params,
                                auth=True
                            )
                            if cancel_response.get("retCode") == 0:
                                logger.info("Order cancelled")
                        except:
                            pass  # Игнорируем ошибки отмены
                    
                    return config['params']  # Возвращаем рабочую конфигурацию
                    
                else:
                    logger.warning(f"❌ Failed: {response.get('retMsg')} (code: {response.get('retCode')})")
                    
            except Exception as e:
                logger.error(f"Exception: {e}")
        
        return None
        
    except Exception as e:
        logger.error(f"Error in fix_order_parameters: {e}")
        return None


async def main():
    """Главная функция"""
    logger.info("=" * 60)
    logger.info("Bybit Order Fix Script")
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
    
    # 1. Проверяем режим аккаунта
    await check_account_mode(client)
    
    # 2. Тестируем создание ордеров
    working_params = await fix_order_parameters(client)
    
    if working_params:
        logger.info("\n" + "="*60)
        logger.info("✅ SOLUTION FOUND!")
        logger.info("Working parameters configuration:")
        logger.info(json.dumps(working_params, indent=2))
        logger.info("="*60)
        
        # Сохраняем рабочую конфигурацию
        with open("working_order_params.json", "w") as f:
            json.dump(working_params, f, indent=2)
            logger.info("Configuration saved to working_order_params.json")
    else:
        logger.error("Could not find working order configuration")
    
    # Закрываем сессию
    if hasattr(client, 'session'):
        await client.session.close()
    
    logger.info("\n" + "=" * 60)
    logger.info("Fix script completed")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())