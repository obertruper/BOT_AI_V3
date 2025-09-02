#!/usr/bin/env python3
"""
Детальная диагностика проблем с Bybit API
"""

import asyncio
import os
import sys
import json
import hmac
import hashlib
import time
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from core.logger import setup_logger
from dotenv import load_dotenv
import aiohttp

# Загружаем переменные окружения
load_dotenv()

logger = setup_logger("bybit_debug")


def generate_signature(api_secret: str, params_str: str) -> str:
    """Генерация подписи для Bybit API v5"""
    return hmac.new(
        api_secret.encode('utf-8'),
        params_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


async def test_direct_api_call():
    """Прямой вызов Bybit API для диагностики"""
    
    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")
    
    if not api_key or not api_secret:
        logger.error("API credentials not found")
        return
    
    base_url = "https://api.bybit.com"
    
    async with aiohttp.ClientSession() as session:
        # 1. Проверяем информацию об аккаунте
        logger.info("\n" + "="*60)
        logger.info("1. Checking account info...")
        logger.info("="*60)
        
        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"
        
        # Параметры для запроса баланса
        params = {
            "accountType": "CONTRACT",  # Для деривативов
            "api_key": api_key,
            "timestamp": timestamp,
            "recv_window": recv_window
        }
        
        # Создаем строку параметров для подписи
        param_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
        signature = generate_signature(api_secret, param_str)
        params["sign"] = signature
        
        headers = {
            "X-BAPI-API-KEY": api_key,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-SIGN": signature,
            "X-BAPI-RECV-WINDOW": recv_window
        }
        
        url = f"{base_url}/v5/account/wallet-balance"
        
        async with session.get(url, params=params, headers=headers) as response:
            data = await response.json()
            logger.info(f"Account info response: {json.dumps(data, indent=2)}")
            
            if data.get("retCode") == 0:
                accounts = data.get("result", {}).get("list", [])
                for account in accounts:
                    for coin in account.get("coin", []):
                        if coin.get("coin") == "USDT":
                            logger.info(f"USDT Balance: {coin.get('walletBalance')}")
                            logger.info(f"Available Balance: {coin.get('availableToWithdraw')}")
        
        # 2. Проверяем настройки позиций для BTCUSDT
        logger.info("\n" + "="*60)
        logger.info("2. Checking position info for BTCUSDT...")
        logger.info("="*60)
        
        timestamp = str(int(time.time() * 1000))
        
        params = {
            "category": "linear",
            "symbol": "BTCUSDT",
            "api_key": api_key,
            "timestamp": timestamp,
            "recv_window": recv_window
        }
        
        param_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
        signature = generate_signature(api_secret, param_str)
        params["sign"] = signature
        
        headers["X-BAPI-TIMESTAMP"] = timestamp
        headers["X-BAPI-SIGN"] = signature
        
        url = f"{base_url}/v5/position/list"
        
        async with session.get(url, params=params, headers=headers) as response:
            data = await response.json()
            logger.info(f"Position info: {json.dumps(data, indent=2)}")
            
            if data.get("retCode") == 0:
                positions = data.get("result", {}).get("list", [])
                if positions:
                    for pos in positions:
                        logger.info(f"Position mode: {pos.get('positionIdx')} (0=OneWay, 1=BuyHedge, 2=SellHedge)")
                        logger.info(f"Current leverage: {pos.get('leverage')}")
                else:
                    logger.info("No open positions")
        
        # 3. Проверяем информацию об инструменте
        logger.info("\n" + "="*60)
        logger.info("3. Checking BTCUSDT instrument info...")
        logger.info("="*60)
        
        params = {
            "category": "linear",
            "symbol": "BTCUSDT"
        }
        
        url = f"{base_url}/v5/market/instruments-info"
        
        async with session.get(url, params=params) as response:
            data = await response.json()
            
            if data.get("retCode") == 0:
                instruments = data.get("result", {}).get("list", [])
                if instruments:
                    inst = instruments[0]
                    logger.info(f"Min order qty: {inst.get('lotSizeFilter', {}).get('minOrderQty')}")
                    logger.info(f"Qty step: {inst.get('lotSizeFilter', {}).get('qtyStep')}")
                    logger.info(f"Min leverage: {inst.get('leverageFilter', {}).get('minLeverage')}")
                    logger.info(f"Max leverage: {inst.get('leverageFilter', {}).get('maxLeverage')}")
                    logger.info(f"Leverage step: {inst.get('leverageFilter', {}).get('leverageStep')}")
        
        # 4. Пробуем создать минимальный тестовый ордер
        logger.info("\n" + "="*60)
        logger.info("4. Testing minimal order creation...")
        logger.info("="*60)
        
        # Получаем текущую цену
        params = {
            "category": "linear",
            "symbol": "BTCUSDT"
        }
        
        url = f"{base_url}/v5/market/tickers"
        async with session.get(url, params=params) as response:
            data = await response.json()
            current_price = 0
            if data.get("retCode") == 0:
                tickers = data.get("result", {}).get("list", [])
                if tickers:
                    current_price = float(tickers[0].get("lastPrice", 0))
                    logger.info(f"Current BTCUSDT price: {current_price}")
        
        # Создаем тестовый ордер с минимальными параметрами
        timestamp = str(int(time.time() * 1000))
        
        # ВАЖНО: Используем минимальное количество и правильные параметры
        order_params = {
            "category": "linear",
            "symbol": "BTCUSDT",
            "side": "Buy",
            "orderType": "Market",
            "qty": "0.001",  # Минимальное количество для BTCUSDT
            "timeInForce": "IOC",
            "positionIdx": 0  # One-way mode
        }
        
        # Для POST запроса параметры идут в body
        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"
        
        # Для подписи POST запроса в Bybit v5
        # Формат: timestamp + api_key + recv_window + raw_request_body
        request_body = json.dumps(order_params, separators=(',', ':'), ensure_ascii=False)
        param_str = f"{timestamp}{api_key}{recv_window}{request_body}"
        signature = generate_signature(api_secret, param_str)
        
        headers = {
            "X-BAPI-API-KEY": api_key,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-SIGN": signature,
            "X-BAPI-RECV-WINDOW": recv_window,
            "Content-Type": "application/json"
        }
        
        logger.info(f"Order parameters: {json.dumps(order_params, indent=2)}")
        logger.info(f"Headers: {json.dumps({k: v[:20] + '...' if k == 'X-BAPI-SIGN' else v for k, v in headers.items()}, indent=2)}")
        
        url = f"{base_url}/v5/order/create"
        
        async with session.post(url, json=order_params, headers=headers) as response:
            data = await response.json()
            logger.info(f"Order creation response: {json.dumps(data, indent=2)}")
            
            if data.get("retCode") == 0:
                logger.info("✅ Order created successfully!")
                order_id = data.get("result", {}).get("orderId")
                logger.info(f"Order ID: {order_id}")
            else:
                logger.error(f"❌ Order creation failed!")
                logger.error(f"Error code: {data.get('retCode')}")
                logger.error(f"Error message: {data.get('retMsg')}")
                
                # Анализ конкретных ошибок
                error_code = data.get('retCode')
                if error_code == 10001:
                    logger.info("\nError 10001 - Parameter verification failed")
                    logger.info("Possible issues:")
                    logger.info("1. Check if symbol format is correct (should be BTCUSDT, not BTCUSDT.P)")
                    logger.info("2. Check if quantity meets minimum requirements")
                    logger.info("3. Check if account has enough balance")
                    logger.info("4. Check if positionIdx matches account mode")
                elif error_code == 110043:
                    logger.info("\nError 110043 - Set leverage failed")
                    logger.info("Possible issues:")
                    logger.info("1. Leverage value out of allowed range")
                    logger.info("2. Position already exists with different leverage")
                    logger.info("3. Account mode doesn't support leverage change")


async def main():
    """Главная функция"""
    logger.info("=" * 60)
    logger.info("Bybit API Direct Debug Test")
    logger.info("=" * 60)
    
    await test_direct_api_call()
    
    logger.info("\n" + "=" * 60)
    logger.info("Debug test completed")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())