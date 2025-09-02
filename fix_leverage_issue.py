#!/usr/bin/env python3
"""
Скрипт для проверки и исправления проблем с установкой кредитного плеча на Bybit
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

# Загружаем переменные окружения
load_dotenv()

logger = setup_logger("leverage_fixer")


async def check_leverage_settings(client: BybitClient, symbol: str):
    """Проверка текущих настроек кредитного плеча"""
    try:
        # Получаем текущую позицию
        positions = await client.get_positions(symbol)
        if positions:
            for pos in positions:
                logger.info(f"Position {symbol}: leverage={pos.get('leverage', 'N/A')}, side={pos.get('side', 'N/A')}")
        
        # Попробуем получить информацию о символе
        try:
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
                    logger.info(f"  Max leverage: {inst.get('leverageFilter', {}).get('maxLeverage', 'N/A')}")
                    logger.info(f"  Min leverage: {inst.get('leverageFilter', {}).get('minLeverage', 'N/A')}")
                    logger.info(f"  Current settings: {inst.get('leverageFilter', {})}")
        except Exception as e:
            logger.error(f"Failed to get instrument info: {e}")
            
    except Exception as e:
        logger.error(f"Error checking leverage: {e}")


async def fix_leverage_mode(client: BybitClient, symbol: str, leverage: float = 5.0):
    """Исправление проблем с установкой кредитного плеча"""
    try:
        logger.info(f"Fixing leverage for {symbol} to {leverage}x")
        
        # Сначала проверяем текущие настройки
        await check_leverage_settings(client, symbol)
        
        # Пробуем установить режим позиции (One-way mode)
        try:
            params = {
                "category": "linear",
                "symbol": symbol,
                "mode": 0  # 0 = One-way mode
            }
            response = await client._make_request("POST", "/v5/position/switch-mode", params, auth=True)
            if response.get("retCode") == 0:
                logger.info(f"✅ Position mode set to One-way for {symbol}")
            elif response.get("retCode") == 110025:  # Уже установлен
                logger.info(f"Position mode already set for {symbol}")
            else:
                logger.warning(f"Position mode setting response: {response}")
        except Exception as e:
            logger.warning(f"Could not set position mode: {e}")
        
        # Теперь пробуем установить кредитное плечо
        try:
            # Используем правильный формат для Bybit API v5
            params = {
                "category": "linear",
                "symbol": symbol,
                "buyLeverage": str(leverage),
                "sellLeverage": str(leverage)
            }
            
            response = await client._make_request("POST", "/v5/position/set-leverage", params, auth=True)
            
            if response.get("retCode") == 0:
                logger.info(f"✅ Leverage successfully set to {leverage}x for {symbol}")
                return True
            elif response.get("retCode") == 110043:
                # Leverage is already set or position exists
                logger.info(f"Leverage already set or position exists for {symbol}")
                
                # Проверяем, есть ли открытая позиция
                positions = await client.get_positions(symbol)
                if positions:
                    logger.info(f"Open position found for {symbol}, leverage changes not allowed")
                else:
                    logger.info(f"Leverage already configured for {symbol}")
                return True
            else:
                logger.error(f"Failed to set leverage: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting leverage: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Critical error in fix_leverage_mode: {e}")
        return False


async def main():
    """Главная функция"""
    logger.info("=" * 60)
    logger.info("Starting Leverage Fix Script")
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
    
    # Инициализируем клиента (если есть метод initialize)
    if hasattr(client, 'initialize'):
        await client.initialize()
    
    # Список символов для проверки
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "LINKUSDT"]
    
    # Проверяем и исправляем кредитное плечо для каждого символа
    for symbol in symbols:
        logger.info(f"\n--- Processing {symbol} ---")
        await fix_leverage_mode(client, symbol, leverage=5.0)
        await asyncio.sleep(1)  # Небольшая задержка между запросами
    
    # Закрываем клиента (если есть метод close)
    if hasattr(client, 'close'):
        await client.close()
    elif hasattr(client, 'session'):
        await client.session.close()
    
    logger.info("\n" + "=" * 60)
    logger.info("Leverage Fix Script Completed")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())