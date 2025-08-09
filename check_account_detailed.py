#!/usr/bin/env python3
"""
Детальная проверка состояния аккаунта Bybit
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# Устанавливаем переменные окружения
os.environ["PGPORT"] = "5555"
os.environ["PGUSER"] = "obertruper"
os.environ["PGDATABASE"] = "bot_trading_v3"


async def main():
    """Главная функция"""
    print("=== Детальная проверка аккаунта Bybit ===\n")

    try:
        from exchanges.bybit.client import BybitClient

        client = BybitClient(
            api_key=os.getenv("BYBIT_API_KEY"),
            api_secret=os.getenv("BYBIT_API_SECRET"),
            sandbox=False,
        )

        print("1️⃣ Информация о кошельке (Unified account):")

        try:
            wallet_info = await client._make_request(
                "GET", "/v5/account/wallet-balance", {"accountType": "UNIFIED"}
            )

            if wallet_info and "list" in wallet_info:
                for account in wallet_info["list"]:
                    print(f"\n   Account type: {account.get('accountType', 'N/A')}")
                    print(f"   Total equity: {account.get('totalEquity', 'N/A')}")
                    print(
                        f"   Total margin balance: {account.get('totalMarginBalance', 'N/A')}"
                    )
                    print(
                        f"   Total available balance: {account.get('totalAvailableBalance', 'N/A')}"
                    )

                    if "coin" in account:
                        for coin_info in account["coin"]:
                            if coin_info["coin"] == "USDT":
                                print("\n   USDT детали:")
                                print(
                                    f"   - Wallet balance: {coin_info.get('walletBalance', 'N/A')}"
                                )
                                print(
                                    f"   - Available balance: {coin_info.get('availableBalance', 'N/A')}"
                                )
                                print(f"   - Equity: {coin_info.get('equity', 'N/A')}")
                                print(
                                    f"   - Used margin: {coin_info.get('usedMargin', 'N/A')}"
                                )
                                print(
                                    f"   - Unrealized PnL: {coin_info.get('unrealisedPnl', 'N/A')}"
                                )
                                print(
                                    f"   - Cumulative realized PnL: {coin_info.get('cumRealisedPnl', 'N/A')}"
                                )

        except Exception as e:
            print(f"   Ошибка: {e}")

        print("\n2️⃣ Проверка режима позиций:")

        try:
            # Проверяем настройки позиций
            position_info = await client._make_request(
                "GET", "/v5/position/switch-mode", {}
            )

            if position_info:
                print(f"   Position mode: {position_info}")

        except Exception as e:
            print(f"   Ошибка получения режима позиций: {e}")

        print("\n3️⃣ Проверка открытых позиций (детально):")

        try:
            # Получаем все позиции
            positions = await client._make_request(
                "GET", "/v5/position/list", {"category": "linear", "settleCoin": "USDT"}
            )

            if positions and "list" in positions:
                pos_list = positions["list"]
                if pos_list:
                    print(f"   Найдено позиций: {len(pos_list)}")
                    for pos in pos_list:
                        if float(pos.get("size", 0)) > 0:
                            print(f"\n   Позиция {pos['symbol']}:")
                            print(f"   - Side: {pos.get('side', 'N/A')}")
                            print(f"   - Size: {pos.get('size', 'N/A')}")
                            print(
                                f"   - Position value: {pos.get('positionValue', 'N/A')}"
                            )
                            print(f"   - Position idx: {pos.get('positionIdx', 'N/A')}")
                            print(
                                f"   - Unrealized PnL: {pos.get('unrealisedPnl', 'N/A')}"
                            )
                            print(f"   - Position MM: {pos.get('positionMM', 'N/A')}")
                            print(f"   - Position IM: {pos.get('positionIM', 'N/A')}")
                else:
                    print("   Нет открытых позиций")

        except Exception as e:
            print(f"   Ошибка: {e}")

        print("\n4️⃣ Проверка заблокированных средств:")

        try:
            # Проверяем историю транзакций
            transactions = await client._make_request(
                "GET",
                "/v5/account/transaction-log",
                {
                    "accountType": "UNIFIED",
                    "category": "linear",
                    "currency": "USDT",
                    "limit": 10,
                },
            )

            if transactions and "list" in transactions:
                trans_list = transactions["list"]
                if trans_list:
                    print("   Последние транзакции:")
                    for trans in trans_list[:5]:
                        print(
                            f"   - {trans.get('transactionTime', 'N/A')}: {trans.get('type', 'N/A')} {trans.get('amount', 'N/A')} USDT"
                        )

        except Exception as e:
            print(f"   Ошибка получения транзакций: {e}")

        print("\n5️⃣ Проверка настроек маржи:")

        try:
            # Проверяем настройки маржи для BTCUSDT
            margin_info = await client._make_request(
                "GET", "/v5/account/set-margin-mode", {}
            )

            print(f"   Margin mode: {margin_info}")

        except Exception as e:
            print(f"   Ошибка: {e}")

    except Exception as e:
        print(f"\n❌ Общая ошибка: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
