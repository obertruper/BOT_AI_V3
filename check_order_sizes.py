#!/usr/bin/env python3
"""
Проверка минимальных размеров ордеров для всех символов
"""
import asyncio
import os
import sys

sys.path.append(".")

import ccxt.pro as ccxt
from dotenv import load_dotenv

load_dotenv()


async def check_order_sizes():
    """Проверка минимальных размеров для всех активных символов"""

    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")

    exchange = ccxt.bybit(
        {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"defaultType": "swap", "accountType": "unified"},
        }
    )

    try:
        print("🔍 Проверка минимальных размеров ордеров на Bybit...\n")

        # Загружаем рынки
        markets = await exchange.load_markets()

        # Получаем баланс
        balance = await exchange.fetch_balance()
        available_usdt = balance.get("USDT", {}).get("free", 0)
        print(f"💰 Доступный баланс: {available_usdt:.2f} USDT\n")

        # Проверяем популярные символы
        symbols = [
            "BTC/USDT:USDT",
            "ETH/USDT:USDT",
            "SOL/USDT:USDT",
            "DOGE/USDT:USDT",
            "XRP/USDT:USDT",
            "ADA/USDT:USDT",
        ]

        print("📊 Минимальные размеры для популярных символов:\n")
        print("-" * 80)
        print(
            f"{'Символ':<15} {'Цена':<12} {'Мин. кол-во':<15} {'Мин. в USDT':<12} {'Шаг цены':<12}"
        )
        print("-" * 80)

        for symbol in symbols:
            if symbol in markets:
                market = markets[symbol]
                ticker = await exchange.fetch_ticker(symbol)
                price = ticker["last"]

                # Минимальное количество контрактов
                min_amount = (
                    market["limits"]["amount"]["min"]
                    if market["limits"]["amount"]["min"]
                    else 0.001
                )
                # Шаг цены
                price_precision = (
                    market["precision"]["price"] if market["precision"]["price"] else 0.01
                )
                # Шаг количества
                amount_precision = (
                    market["precision"]["amount"] if market["precision"]["amount"] else 0.001
                )

                # Минимальная стоимость ордера
                min_value_usdt = min_amount * price

                # Форматируем символ без суффикса
                display_symbol = symbol.split(":")[0]

                print(
                    f"{display_symbol:<15} ${price:<11.2f} {min_amount:<15.6f} ${min_value_usdt:<11.2f} {price_precision:<12}"
                )

                # Проверяем, можем ли открыть позицию с текущим балансом
                if min_value_usdt > available_usdt:
                    print("   ⚠️ Недостаточно средств для открытия минимальной позиции")

                # Рекомендуемый размер (с учетом комиссий и запаса)
                recommended_size = max(
                    min_value_usdt * 1.2, 6
                )  # Минимум 6 USDT или 120% от минимума
                if recommended_size <= available_usdt:
                    recommended_qty = recommended_size / price
                    # Округляем до правильной точности
                    if amount_precision > 0:
                        recommended_qty = (
                            round(recommended_qty / amount_precision) * amount_precision
                        )
                    print(
                        f"   ✅ Рекомендуемый размер: {recommended_qty:.6f} ({recommended_size:.2f} USDT)"
                    )

        print("-" * 80)

        # Проверяем общие ограничения
        print("\n📋 Общие ограничения Bybit:")
        print("   • Минимальный размер ордера: 5 USDT (для большинства пар)")
        print("   • Максимальное плечо: 100x (зависит от символа)")
        print("   • Комиссия Maker: 0.01%")
        print("   • Комиссия Taker: 0.06%")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await exchange.close()


if __name__ == "__main__":
    asyncio.run(check_order_sizes())
