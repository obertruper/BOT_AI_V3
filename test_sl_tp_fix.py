#!/usr/bin/env python3
"""Тестирование установки SL/TP после создания позиции"""

import asyncio
import os

from dotenv import load_dotenv

from exchanges.base.order_types import OrderRequest, OrderSide, OrderType
from exchanges.bybit.client import BybitClient

load_dotenv()


async def test_sl_tp_setup():
    """Тест создания рыночного ордера с автоматической установкой SL/TP"""

    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")

    if not api_key or not api_secret:
        print("❌ API ключи не найдены в .env")
        return

    client = BybitClient(api_key, api_secret)

    # 1. Получаем текущую цену
    print("\n=== Получение рыночной цены ===")
    symbol = "SOLUSDT"  # Используем SOL для теста (дешевле BTC)

    try:
        ticker = await client.get_ticker(symbol)
        current_price = ticker.last_price
        print(f"Текущая цена {symbol}: ${current_price:.2f}")
    except Exception as e:
        print(f"Ошибка получения тикера: {e}")
        return

    # 2. Проверяем баланс
    print("\n=== Проверка баланса ===")
    balance = await client.get_balance("USDT")
    print(f"Доступный баланс: ${balance.available:.2f}")

    if balance.available < 20:
        print("⚠️ Недостаточно средств для теста (нужно минимум $20)")
        return

    # 3. Рассчитываем параметры ордера
    min_order_value = 15.0  # Минимум для Bybit
    leverage = 5
    quantity = min_order_value / current_price

    # SL и TP уровни
    stop_loss_price = current_price * 0.98  # -2% от цены входа
    take_profit_price = current_price * 1.03  # +3% от цены входа

    print("\n=== Параметры тестового ордера ===")
    print(f"Символ: {symbol}")
    print("Тип: MARKET (рыночный)")
    print("Сторона: BUY (длинная позиция)")
    print(f"Количество: {quantity:.3f} SOL")
    print(f"Leverage: {leverage}x")
    print(f"Стоимость позиции: ${quantity * current_price:.2f}")
    print(f"Требуемая маржа: ${(quantity * current_price / leverage):.2f}")
    print(f"Stop Loss: ${stop_loss_price:.2f} (-2%)")
    print(f"Take Profit: ${take_profit_price:.2f} (+3%)")

    # 4. Создаем рыночный ордер с SL/TP
    print("\n=== Создание рыночного ордера с SL/TP ===")

    order_request = OrderRequest(
        symbol=symbol,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=quantity,
        leverage=leverage,
        stop_loss=stop_loss_price,  # SL будет установлен после открытия позиции
        take_profit=take_profit_price,  # TP будет установлен после открытия позиции
    )

    print("Отправка ордера...")

    try:
        response = await client.place_order(order_request)

        if response.success:
            print("✅ Ордер создан успешно!")
            print(f"   Order ID: {response.order_id}")

            # Ждем исполнения и проверяем позицию
            await asyncio.sleep(2)

            print("\n=== Проверка позиции ===")
            position = await client.get_position(symbol)

            if position and position.is_open:
                print("✅ Позиция открыта:")
                print(f"   Размер: {position.size} SOL")
                print(f"   Цена входа: ${position.entry_price:.2f}")
                print(f"   Текущий PnL: ${position.unrealized_pnl:.2f}")
                print(
                    f"   Stop Loss: ${position.stop_loss:.2f}"
                    if position.stop_loss
                    else "   Stop Loss: ❌ не установлен"
                )
                print(
                    f"   Take Profit: ${position.take_profit:.2f}"
                    if position.take_profit
                    else "   Take Profit: ❌ не установлен"
                )

                # Если SL/TP не установились автоматически, устанавливаем вручную
                if not position.stop_loss or not position.take_profit:
                    print("\n=== Установка SL/TP вручную ===")

                    if not position.stop_loss:
                        sl_response = await client.set_stop_loss(symbol, stop_loss_price)
                        if sl_response.success:
                            print(f"✅ Stop Loss установлен на ${stop_loss_price:.2f}")
                        else:
                            print(f"❌ Ошибка установки SL: {sl_response.message}")

                    if not position.take_profit:
                        tp_response = await client.set_take_profit(symbol, take_profit_price)
                        if tp_response.success:
                            print(f"✅ Take Profit установлен на ${take_profit_price:.2f}")
                        else:
                            print(f"❌ Ошибка установки TP: {tp_response.message}")

                # Финальная проверка
                await asyncio.sleep(1)
                position = await client.get_position(symbol)

                print("\n=== Финальная проверка позиции ===")
                print(
                    f"Stop Loss: {'✅ ' + str(position.stop_loss) if position.stop_loss else '❌ не установлен'}"
                )
                print(
                    f"Take Profit: {'✅ ' + str(position.take_profit) if position.take_profit else '❌ не установлен'}"
                )

                # Предлагаем закрыть позицию
                print("\n=== Закрытие тестовой позиции ===")
                user_input = input("Закрыть позицию? (y/n): ")

                if user_input.lower() == "y":
                    close_response = await client.close_position(symbol)
                    if close_response.success:
                        print("✅ Позиция закрыта")
                    else:
                        print(f"❌ Ошибка закрытия: {close_response.message}")
                else:
                    print("⚠️ Позиция оставлена открытой. Не забудьте закрыть вручную!")
            else:
                print("❌ Позиция не найдена после создания ордера")

        else:
            print(f"❌ Ошибка создания ордера: {response.message}")

    except Exception as e:
        print(f"❌ Исключение при создании ордера: {e}")

    print("\n=== Тест завершен ===")


if __name__ == "__main__":
    asyncio.run(test_sl_tp_setup())
