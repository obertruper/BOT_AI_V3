#!/usr/bin/env python3
"""
Проверка баланса аккаунта Bybit
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

# Загружаем переменные окружения
load_dotenv()

logger = setup_logger("balance_check")


async def check_balance(client: BybitClient):
    """Проверка баланса на всех типах аккаунтов"""
    
    account_types = ["CONTRACT", "UNIFIED", "SPOT"]
    
    for account_type in account_types:
        logger.info(f"\nChecking {account_type} account...")
        
        try:
            params = {
                "accountType": account_type
            }
            
            response = await client._make_request(
                "GET",
                "/v5/account/wallet-balance",
                params,
                auth=True
            )
            
            if response.get("retCode") == 0:
                accounts = response.get("result", {}).get("list", [])
                
                if accounts:
                    for account in accounts:
                        logger.info(f"Account type: {account.get('accountType')}")
                        
                        coins = account.get("coin", [])
                        for coin in coins:
                            coin_name = coin.get("coin")
                            if coin_name in ["USDT", "BTC", "ETH"]:
                                wallet_balance = coin.get("walletBalance", "0")
                                available = coin.get("availableToWithdraw", "0")
                                equity = coin.get("equity", "0")
                                
                                logger.info(f"\n{coin_name}:")
                                logger.info(f"  Wallet balance: {wallet_balance}")
                                logger.info(f"  Available: {available}")
                                logger.info(f"  Equity: {equity}")
                                
                                # Проверяем, достаточно ли баланса для минимального ордера
                                if coin_name == "USDT":
                                    try:
                                        available_float = float(available) if available else 0
                                        min_order_value = 10  # Минимальный размер ордера в USDT
                                        
                                        if available_float < min_order_value:
                                            logger.warning(f"⚠️ Insufficient USDT balance: {available_float:.2f} < {min_order_value}")
                                            logger.warning("You need to deposit more USDT to trade")
                                        else:
                                            logger.info(f"✅ Sufficient USDT balance for trading: {available_float:.2f}")
                                    except:
                                        pass
                else:
                    logger.info(f"No {account_type} account found")
                    
            else:
                error_msg = response.get("retMsg", "Unknown error")
                if "Account type does not match" in error_msg:
                    logger.info(f"{account_type} account not available")
                else:
                    logger.warning(f"Error: {error_msg}")
                    
        except Exception as e:
            logger.error(f"Error checking {account_type}: {e}")


async def main():
    """Главная функция"""
    logger.info("=" * 60)
    logger.info("Bybit Balance Check")
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
    
    # Проверяем баланс
    await check_balance(client)
    
    # Закрываем сессию
    if hasattr(client, 'session'):
        await client.session.close()
    
    logger.info("\n" + "=" * 60)
    logger.info("Balance check completed")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())