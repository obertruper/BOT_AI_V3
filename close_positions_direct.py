#!/usr/bin/env python3
"""
Прямое закрытие позиций через API Bybit
"""

import asyncio
import hashlib
import hmac
import json
import os
import sys
import time

import aiohttp
from dotenv import load_dotenv

# Добавляем корневую директорию в PATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()


async def close_all_positions_direct():
    """Закрытие всех позиций напрямую через API"""

    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")

    base_url = "https://api.bybit.com"

    async with aiohttp.ClientSession() as session:
        # Получаем позиции
        timestamp = str(int(time.time() * 1000))
        sign_str = f"{timestamp}{api_key}5000category=linear&settleCoin=USDT"
        signature = hmac.new(api_secret.encode(), sign_str.encode(), hashlib.sha256).hexdigest()

        headers = {
            "X-BAPI-API-KEY": api_key,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-SIGN": signature,
            "X-BAPI-RECV-WINDOW": "5000",
        }

        # Получаем позиции
        async with session.get(
            f"{base_url}/v5/position/list",
            headers=headers,
            params={"category": "linear", "settleCoin": "USDT"},
        ) as resp:
            data = await resp.json()

        if data.get("retCode") != 0:
            print(f"❌ Ошибка получения позиций: {data}")
            return

        positions = data.get("result", {}).get("list", [])

        if not positions:
            print("📊 Нет открытых позиций")
            return

        print(f"📊 Найдено {len(positions)} позиций для закрытия")

        # Закрываем каждую позицию
        for pos in positions:
            symbol = pos["symbol"]
            side = pos["side"]  # Buy или Sell
            size = pos["size"]

            if float(size) == 0:
                continue

            print(f"\nЗакрываем {symbol}:")
            print(f"  Направление: {side}")
            print(f"  Размер: {size}")

            # Для закрытия создаем противоположный ордер
            close_side = "Sell" if side == "Buy" else "Buy"

            # Подготавливаем параметры ордера
            order_params = {
                "category": "linear",
                "symbol": symbol,
                "side": close_side,
                "orderType": "Market",
                "qty": size,
                "timeInForce": "IOC",
                "reduceOnly": True,
                "positionIdx": 0,  # One-way mode для закрытия
            }

            # Создаем подпись для ордера
            timestamp = str(int(time.time() * 1000))
            params_str = json.dumps(order_params, separators=(",", ":"))
            sign_str = f"{timestamp}{api_key}5000{params_str}"
            signature = hmac.new(api_secret.encode(), sign_str.encode(), hashlib.sha256).hexdigest()

            headers = {
                "X-BAPI-API-KEY": api_key,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-SIGN": signature,
                "X-BAPI-RECV-WINDOW": "5000",
                "Content-Type": "application/json",
            }

            # Отправляем ордер
            async with session.post(
                f"{base_url}/v5/order/create", headers=headers, json=order_params
            ) as resp:
                result = await resp.json()

            if result.get("retCode") == 0:
                print("  ✅ Позиция закрыта")
            else:
                print(f"  ❌ Ошибка: {result.get('retMsg', 'Unknown error')}")

        # Ждем обновления баланса
        await asyncio.sleep(2)

        # Проверяем финальный баланс
        timestamp = str(int(time.time() * 1000))
        sign_str = f"{timestamp}{api_key}5000accountType=UNIFIED&coin=USDT"
        signature = hmac.new(api_secret.encode(), sign_str.encode(), hashlib.sha256).hexdigest()

        headers = {
            "X-BAPI-API-KEY": api_key,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-SIGN": signature,
            "X-BAPI-RECV-WINDOW": "5000",
        }

        async with session.get(
            f"{base_url}/v5/account/wallet-balance",
            headers=headers,
            params={"accountType": "UNIFIED", "coin": "USDT"},
        ) as resp:
            data = await resp.json()

        if data.get("retCode") == 0:
            balances = data.get("result", {}).get("list", [])
            if balances:
                coin_data = balances[0].get("coin", [])
                for coin in coin_data:
                    if coin.get("coin") == "USDT":
                        print("\n💵 Баланс USDT:")
                        print(f"  Всего: {coin.get('walletBalance', 0)}")
                        print(f"  Доступно: {coin.get('availableToWithdraw', 0)}")
                        break


if __name__ == "__main__":
    asyncio.run(close_all_positions_direct())
