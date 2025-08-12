#!/usr/bin/env python3
"""
Проверка статуса счета Bybit
"""

import asyncio
import hashlib
import hmac
import os
import time

import aiohttp
from dotenv import load_dotenv

load_dotenv()


async def check_account():
    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")

    print("🔍 Проверка счета Bybit")
    print("=" * 50)

    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"

    # 1. Проверяем баланс
    print("\n💰 Баланс счета:")
    params = "accountType=UNIFIED"
    param_str = timestamp + api_key + recv_window + params
    signature = hmac.new(
        bytes(api_secret, "utf-8"), bytes(param_str, "utf-8"), hashlib.sha256
    ).hexdigest()

    headers = {
        "X-BAPI-API-KEY": api_key,
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-SIGN": signature,
        "X-BAPI-RECV-WINDOW": recv_window,
    }

    async with aiohttp.ClientSession() as session:
        # Баланс
        url = "https://api.bybit.com/v5/account/wallet-balance"
        async with session.get(
            url, headers=headers, params={"accountType": "UNIFIED"}
        ) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("retCode") == 0:
                    for account in data["result"]["list"]:
                        print(f"  Тип счета: {account['accountType']}")
                        print(f"  Общий баланс: ${account['totalEquity']}")
                        print(
                            f"  Доступный баланс: ${account['totalAvailableBalance']}"
                        )
                        print(f"  Используемая маржа: ${account['totalInitialMargin']}")

                        # Проверяем достаточность средств
                        available = float(account["totalAvailableBalance"])
                        if available < 10:
                            print(
                                "  ⚠️ ВНИМАНИЕ: Недостаточно средств! Нужно минимум $10"
                            )
                        else:
                            print("  ✅ Достаточно средств для торговли")

        # 2. Проверяем позиции
        print("\n📊 Открытые позиции:")
        timestamp = str(int(time.time() * 1000))
        params = "category=linear&settleCoin=USDT"
        param_str = timestamp + api_key + recv_window + params
        signature = hmac.new(
            bytes(api_secret, "utf-8"), bytes(param_str, "utf-8"), hashlib.sha256
        ).hexdigest()

        headers["X-BAPI-TIMESTAMP"] = timestamp
        headers["X-BAPI-SIGN"] = signature

        url = "https://api.bybit.com/v5/position/list"
        async with session.get(
            url, headers=headers, params={"category": "linear", "settleCoin": "USDT"}
        ) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("retCode") == 0:
                    positions = data["result"]["list"]
                    open_positions = [
                        p for p in positions if float(p.get("size", "0")) != 0
                    ]

                    if open_positions:
                        for pos in open_positions:
                            print(
                                f"  • {pos['symbol']}: {pos['side']} {pos['size']} @ {pos['avgPrice']}"
                            )
                            print(f"    PnL: ${pos['unrealisedPnl']}")
                    else:
                        print("  Нет открытых позиций")

        # 3. Проверяем активные ордера
        print("\n📝 Активные ордера:")
        timestamp = str(int(time.time() * 1000))
        params = "category=linear&settleCoin=USDT"
        param_str = timestamp + api_key + recv_window + params
        signature = hmac.new(
            bytes(api_secret, "utf-8"), bytes(param_str, "utf-8"), hashlib.sha256
        ).hexdigest()

        headers["X-BAPI-TIMESTAMP"] = timestamp
        headers["X-BAPI-SIGN"] = signature

        url = "https://api.bybit.com/v5/order/realtime"
        async with session.get(
            url, headers=headers, params={"category": "linear", "settleCoin": "USDT"}
        ) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("retCode") == 0:
                    orders = data["result"]["list"]
                    if orders:
                        for order in orders[:5]:
                            print(
                                f"  • {order['symbol']}: {order['side']} {order['qty']} @ {order.get('price', 'Market')}"
                            )
                            print(f"    Статус: {order['orderStatus']}")
                    else:
                        print("  Нет активных ордеров")


if __name__ == "__main__":
    asyncio.run(check_account())
