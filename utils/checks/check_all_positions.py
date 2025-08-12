#!/usr/bin/env python3
"""
Проверка всех позиций и их плеча
"""

import asyncio
import os

from dotenv import load_dotenv

load_dotenv()

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from exchanges.bybit.client import BybitClient


async def check_all_positions():
    """Проверка всех открытых позиций"""

    print("=" * 60)
    print("ПРОВЕРКА ВСЕХ ПОЗИЦИЙ И ПЛЕЧА")
    print("=" * 60)

    client = BybitClient(
        api_key=os.getenv("BYBIT_API_KEY"),
        api_secret=os.getenv("BYBIT_API_SECRET"),
        sandbox=False,
    )

    try:
        # Получаем все позиции
        response = await client._make_request(
            "GET",
            "/v5/position/list",
            {"category": "linear", "settleCoin": "USDT"},
            auth=True,
        )

        if response and "result" in response:
            positions = response["result"].get("list", [])

            open_positions = []
            for pos in positions:
                size = float(pos.get("size", 0))
                if size > 0:
                    open_positions.append(pos)

            if open_positions:
                print(f"\n📊 Найдено открытых позиций: {len(open_positions)}\n")

                for pos in open_positions:
                    symbol = pos.get("symbol")
                    side = pos.get("side")
                    size = pos.get("size")
                    leverage = pos.get("leverage")
                    entry_price = pos.get("avgPrice")
                    stop_loss = pos.get("stopLoss", "")
                    take_profit = pos.get("takeProfit", "")

                    print(f"{'=' * 40}")
                    print(f"📌 {symbol}")
                    print(f"   Side: {side}")
                    print(f"   Size: {size}")
                    print(f"   Entry: ${entry_price}")

                    # ВАЖНО: Проверяем плечо
                    print(f"   ⚠️ ПЛЕЧО: {leverage}x", end="")
                    if float(leverage) != 5:
                        print(" ❌ ДОЛЖНО БЫТЬ 5x!")
                    else:
                        print(" ✅")

                    # SL/TP
                    if stop_loss:
                        print(f"   SL: ${stop_loss} ✅")
                    else:
                        print("   SL: НЕ УСТАНОВЛЕН ❌")

                    if take_profit:
                        print(f"   TP: ${take_profit} ✅")
                    else:
                        print("   TP: НЕ УСТАНОВЛЕН ❌")
            else:
                print("\n❌ Нет открытых позиций")

        # Исправляем плечо для позиций где оно != 5
        print("\n" + "=" * 60)
        print("ИСПРАВЛЕНИЕ ПЛЕЧА")
        print("=" * 60)

        symbols_to_fix = []
        for pos in open_positions:
            if float(pos.get("leverage", 0)) != 5:
                symbols_to_fix.append(pos.get("symbol"))

        if symbols_to_fix:
            print(f"\n⚙️ Нужно исправить плечо для: {', '.join(symbols_to_fix)}")

            for symbol in symbols_to_fix:
                try:
                    print(f"\n🔧 Устанавливаем плечо 5x для {symbol}...")

                    params = {
                        "category": "linear",
                        "symbol": symbol,
                        "buyLeverage": "5",
                        "sellLeverage": "5",
                    }

                    response = await client._make_request(
                        "POST", "/v5/position/set-leverage", params, auth=True
                    )

                    if response and response.get("retCode") == 0:
                        print("   ✅ Плечо установлено на 5x")
                    else:
                        print(f"   ❌ Ошибка: {response}")

                except Exception as e:
                    print(f"   ❌ Ошибка: {e}")
        else:
            print("\n✅ Все позиции имеют правильное плечо (5x)")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")

    print("\n" + "=" * 60)
    print("РЕКОМЕНДАЦИИ:")
    print("=" * 60)
    print(
        """
1. Плечо должно устанавливаться ПЕРЕД открытием позиции
2. Проверяйте конфигурацию: config/trading.yaml
   orders:
     default_leverage: 5
3. OrderManager должен всегда вызывать set_leverage()
4. Для существующих позиций плечо не изменится
5. Новые позиции будут открываться с правильным плечом
    """
    )


if __name__ == "__main__":
    asyncio.run(check_all_positions())
