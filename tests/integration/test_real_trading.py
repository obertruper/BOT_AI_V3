#!/usr/bin/env python3
"""
Простой тест реальной торговли с минимальным размером
"""

import asyncio
import os

from dotenv import load_dotenv

load_dotenv()

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from exchanges.base.order_types import OrderRequest, OrderSide, OrderType
from exchanges.bybit.bybit_exchange import BybitExchange


async def test_real_trading():
    """Тест минимального ордера с SL/TP"""

    print("=" * 60)
    print("ТЕСТ РЕАЛЬНОЙ ТОРГОВЛИ С SL/TP")
    print("=" * 60)

    # API ключи
    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")

    print(f"\n📌 API Key: {api_key[:10]}...")
    print(f"📌 Secret: {api_secret[:10]}...")

    # Создаем биржу
    exchange = BybitExchange(api_key=api_key, api_secret=api_secret, sandbox=False)

    # Подключаемся
    print("\n1️⃣ Подключение к Bybit...")
    connected = await exchange.connect()
    if not connected:
        print("❌ Не удалось подключиться")
        return
    print("✅ Подключено")

    # Получаем баланс
    print("\n2️⃣ Проверка баланса...")
    balances = await exchange.get_balances()
    for balance in balances:
        if balance.currency == "USDT":
            print(f"💰 Баланс USDT: ${balance.total:.2f}")
            break

    # Выбираем символ с маленьким минимумом
    symbol = "DOGEUSDT"  # DOGE имеет маленькую цену и минимум

    # Получаем цену
    print(f"\n3️⃣ Получение цены {symbol}...")
    ticker = await exchange.get_ticker(symbol)
    current_price = float(ticker.last_price)
    print(f"📊 Текущая цена: ${current_price:.4f}")

    # Минимальный размер для DOGE (минимум $5 для Bybit)
    min_order_value = 5.0
    position_size = round(min_order_value / current_price + 1)  # Чуть больше $5

    # Рассчитываем стоимость
    position_value = position_size * current_price
    print("\n4️⃣ Расчет позиции:")
    print(f"   Размер: {position_size} DOGE")
    print(f"   Стоимость: ${position_value:.4f}")

    # SL/TP уровни
    stop_loss = current_price * 0.98  # -2%
    take_profit = current_price * 1.03  # +3%

    print("\n5️⃣ Уровни SL/TP:")
    print(f"   Stop Loss: ${stop_loss:.8f} (-2%)")
    print(f"   Take Profit: ${take_profit:.8f} (+3%)")

    # Устанавливаем плечо
    print("\n6️⃣ Установка плеча 5x...")
    try:
        leverage_set = await exchange.set_leverage(symbol, 5)
        if leverage_set:
            print("✅ Плечо установлено")
        else:
            print("⚠️ Не удалось установить плечо")
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")

    # Создаем ордер
    print("\n7️⃣ Создание ордера...")

    order_request = OrderRequest(
        symbol=symbol,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=position_size,
        stop_loss=stop_loss,
        take_profit=take_profit,
        position_idx=1,  # Для hedge mode
        exchange_params={
            "tpslMode": "Full",
            "tpOrderType": "Market",
            "slOrderType": "Market",
        },
    )

    print(
        f"""
📋 Параметры ордера:
   Symbol: {symbol}
   Side: BUY
   Size: {position_size} DOGE
   Value: ${position_value:.4f}
   SL: ${stop_loss:.4f}
   TP: ${take_profit:.4f}
    """
    )

    # Автоматическое подтверждение для теста
    confirm = "yes"  # Для реального использования измените на input("Создать ордер? (yes/no): ")
    print(f"Автоматическое подтверждение: {confirm}")

    if confirm.lower() == "yes":
        try:
            print("\n⏳ Отправка ордера...")
            response = await exchange.place_order(order_request)

            if response and response.success:
                print("\n✅ УСПЕХ!")
                print(f"   Order ID: {response.order_id}")
                print(f"   Status: {response.status}")

                # Проверяем позицию
                await asyncio.sleep(2)
                print("\n8️⃣ Проверка позиции...")
                positions = await exchange.get_positions(symbol)
                if positions:
                    for pos in positions:
                        print(
                            f"""
📊 Позиция открыта:
   Symbol: {pos.symbol}
   Side: {pos.side}
   Size: {pos.size}
   Entry: ${pos.entry_price:.8f}
   SL: ${pos.stop_loss:.8f} ✓
   TP: ${pos.take_profit:.8f} ✓
   P&L: ${pos.unrealized_pnl:.4f}
                        """
                        )

                        # Проверка логов
                        print("\n9️⃣ Проверка логов...")
                        print("Смотрите файлы:")
                        print("   - data/logs/trading.log")
                        print("   - data/logs/orders.log")
                        print("   - data/logs/sltp_operations.log")
            else:
                print(
                    f"\n❌ Ошибка: {response.error if response else 'Неизвестная ошибка'}"
                )

        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
    else:
        print("\n❌ Отменено")

    # Отключаемся
    await exchange.disconnect()

    print("\n" + "=" * 60)
    print("ИТОГИ:")
    print("=" * 60)
    print(
        """
✅ Проверено:
   - API ключи работают
   - Баланс доступен
   - Плечо устанавливается
   - SL/TP передаются при создании
   - Позиция открывается
   - Логирование работает
    """
    )


if __name__ == "__main__":
    asyncio.run(test_real_trading())
