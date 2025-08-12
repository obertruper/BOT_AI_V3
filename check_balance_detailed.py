#!/usr/bin/env python3
"""
Детальная проверка баланса счета Bybit
"""

import asyncio
import os

from dotenv import load_dotenv

from exchanges.bybit.client import BybitClient

# Загружаем переменные окружения
load_dotenv()


async def check_balance():
    """Проверка баланса на Bybit"""

    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")
    testnet = os.getenv("BYBIT_TESTNET", "false").lower() == "true"

    print(f"🔑 API Key: {api_key[:8]}... ({len(api_key)} символов)")
    print(f"🔑 API Secret: {api_secret[:8]}... ({len(api_secret)} символов)")
    print(f"🌐 Режим: {'Testnet' if testnet else 'Production'}")
    print("-" * 50)

    # Проверяем длину ключей
    if len(api_key) < 18:
        print(
            f"⚠️ ВНИМАНИЕ: API ключ слишком короткий ({len(api_key)} символов, ожидается 18-20)"
        )
    if len(api_secret) < 40:
        print(
            f"⚠️ ВНИМАНИЕ: API секрет слишком короткий ({len(api_secret)} символов, ожидается 40-44)"
        )

    try:
        # Создаем клиент
        client = BybitClient(api_key=api_key, api_secret=api_secret, sandbox=testnet)

        print("🔍 Проверяем баланс счета...")

        # Получаем баланс (для USDT контракта)
        balance = await client.get_balance(currency="USDT")

        if balance:
            print("\n💰 Баланс счета:")
            print("-" * 50)

            total_equity = 0
            for coin, data in balance.items():
                if isinstance(data, dict):
                    equity = data.get("equity", 0)
                    available = data.get("available_balance", 0)
                    if equity > 0:
                        print(f"  {coin}:")
                        print(f"    • Всего: {equity:.4f}")
                        print(f"    • Доступно: {available:.4f}")

                        if coin == "USDT":
                            total_equity = equity

            print("-" * 50)
            print(f"💵 Общий баланс в USDT: {total_equity:.2f}")

            if total_equity < 10:
                print("\n⚠️ ВНИМАНИЕ: Недостаточно средств для торговли!")
                print("   Минимальный рекомендуемый баланс: 10 USDT")
        else:
            print("❌ Не удалось получить баланс")

        # Проверяем открытые позиции
        print("\n📊 Проверяем открытые позиции...")
        positions = await client.get_positions()

        if positions:
            open_positions = [p for p in positions if p.get("size", 0) != 0]
            if open_positions:
                print(f"Найдено {len(open_positions)} открытых позиций:")
                for pos in open_positions:
                    print(
                        f"  • {pos.get('symbol')}: {pos.get('size')} @ {pos.get('avg_price')}"
                    )
            else:
                print("Нет открытых позиций")

        # Проверяем активные ордера
        print("\n📝 Проверяем активные ордера...")
        orders = await client.get_open_orders()

        if orders:
            print(f"Найдено {len(orders)} активных ордеров:")
            for order in orders[:5]:  # Показываем первые 5
                print(
                    f"  • {order.get('symbol')}: {order.get('side')} {order.get('qty')} @ {order.get('price')}"
                )
        else:
            print("Нет активных ордеров")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print("\n🔍 Возможные причины:")
        print("  1. Неверные API ключи")
        print("  2. API ключи обрезаны или повреждены")
        print("  3. Недостаточно прав доступа для ключей")
        print("  4. Ключи для другой сети (testnet/mainnet)")


if __name__ == "__main__":
    asyncio.run(check_balance())
