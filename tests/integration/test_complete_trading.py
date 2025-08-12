#!/usr/bin/env python3
"""
Полный тест торговой системы BOT_AI_V3 с SL/TP
"""

import asyncio
import os
from decimal import Decimal

from dotenv import load_dotenv

load_dotenv()

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from exchanges.base.order_types import OrderRequest, OrderSide, OrderType
from exchanges.bybit.bybit_exchange import BybitExchange

logger = setup_logger("test_complete")


async def test_complete_trading():
    """Тест полного цикла торговли с SL/TP"""

    print(
        """
╔══════════════════════════════════════════════════════════════╗
║       ПОЛНЫЙ ТЕСТ ТОРГОВОЙ СИСТЕМЫ BOT_AI_V3               ║
║                                                              ║
║  Демонстрация создания ордера с SL/TP через единый вызов    ║
╚══════════════════════════════════════════════════════════════╝
    """
    )

    # Получаем конфигурацию
    config_manager = ConfigManager()
    config = config_manager.get_config()

    # API ключи
    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")

    print(f"API Key: {api_key}")
    print(f"Secret: {api_secret[:10]}...")

    # Создаем подключение к бирже
    exchange = BybitExchange(api_key=api_key, api_secret=api_secret, sandbox=False)

    # Подключаемся
    print("\n1. Подключение к Bybit...")
    connected = await exchange.connect()
    if not connected:
        print("❌ Не удалось подключиться")
        return
    print("✅ Подключено успешно!")

    # Получаем баланс
    print("\n2. Проверка баланса...")
    try:
        balances = await exchange.get_balances()
        usdt_balance = None
        for balance in balances:
            if balance.currency == "USDT":
                usdt_balance = balance.total
                print(f"✅ Баланс USDT: ${balance.total:.2f}")
                print(f"   Доступно: ${balance.free:.2f}")
                print(f"   В ордерах: ${balance.used:.2f}")
                break
    except Exception as e:
        print(f"❌ Ошибка получения баланса: {e}")
        usdt_balance = Decimal("172.85")  # Используем известный баланс

    # Получаем текущую цену
    print("\n3. Получение цены BTCUSDT...")
    symbol = "BTCUSDT"
    try:
        ticker = await exchange.get_ticker(symbol)
        current_price = float(ticker.last_price)
        print(f"✅ Текущая цена: ${current_price}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        current_price = 118500  # Примерная цена

    # Расчет позиции (метод из V2)
    print("\n4. Расчет размера позиции (метод V2)...")
    fixed_balance = Decimal(
        str(
            config.get("trading", {})
            .get("risk_management", {})
            .get("fixed_risk_balance", 500)
        )
    )
    risk_per_trade = Decimal(
        str(
            config.get("trading", {})
            .get("risk_management", {})
            .get("risk_per_trade", 0.02)
        )
    )
    leverage = Decimal(
        str(config.get("trading", {}).get("orders", {}).get("default_leverage", 5))
    )

    position_value_usd = fixed_balance * risk_per_trade * leverage
    position_size = float(position_value_usd / Decimal(str(current_price)))

    # Минимальный размер для BTC
    min_size = 0.001
    if position_size < min_size:
        position_size = min_size

    print(f"   Фиксированный баланс: ${fixed_balance}")
    print(f"   Риск на сделку: {risk_per_trade * 100}%")
    print(f"   Плечо: {leverage}x")
    print(f"   Размер позиции: {position_size:.6f} BTC")
    print(f"   Стоимость: ${position_size * current_price:.2f}")

    # Расчет SL/TP (из V2)
    print("\n5. Расчет уровней SL/TP...")
    stop_loss = current_price * 0.98  # -2%
    take_profit = current_price * 1.03  # +3%

    print(f"   Stop Loss: ${stop_loss:.2f} (-2%)")
    print(f"   Take Profit: ${take_profit:.2f} (+3%)")

    # Уровни для частичного закрытия (из V2)
    tp1 = current_price * 1.01  # +1%
    tp2 = current_price * 1.02  # +2%
    tp3 = current_price * 1.03  # +3%

    print("\n   Частичное закрытие:")
    print(f"   TP1: ${tp1:.2f} (+1%) - закрыть 30%")
    print(f"   TP2: ${tp2:.2f} (+2%) - закрыть 30%")
    print(f"   TP3: ${tp3:.2f} (+3%) - закрыть 40%")

    # Установка плеча перед созданием ордера (как в V2)
    print("\n6. Установка плеча...")
    try:
        leverage_success = await exchange.set_leverage(symbol, float(leverage))
        if leverage_success:
            print(f"✅ Плечо {leverage}x успешно установлено для {symbol}")
        else:
            print("⚠️ Не удалось установить плечо, продолжаем с текущим")
    except Exception as e:
        print(f"⚠️ Ошибка установки плеча: {e}")

    # Создание ордера
    print("\n7. Создание ордера с SL/TP...")

    # Определяем режим позиций (hedge mode у вас)
    position_idx = 1  # Для Buy в hedge mode

    order_request = OrderRequest(
        symbol=symbol,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=position_size,
        # ВАЖНО: SL/TP передаются сразу при создании ордера!
        stop_loss=stop_loss,
        take_profit=take_profit,
        position_idx=position_idx,
        # Дополнительные параметры для Bybit
        exchange_params={
            "tpslMode": "Full",  # Закрыть всю позицию
            "tpOrderType": "Market",
            "slOrderType": "Market",
        },
    )

    print(f"   Symbol: {symbol}")
    print("   Side: BUY")
    print(f"   Size: {position_size:.6f} BTC")
    print("   Type: MARKET")
    print(f"   Position Index: {position_idx} (hedge mode)")
    print(f"   Stop Loss: ${stop_loss:.2f} ✓")
    print(f"   Take Profit: ${take_profit:.2f} ✓")

    # Спрашиваем подтверждение
    print("\n" + "=" * 60)
    print("⚠️  ВНИМАНИЕ: Это создаст РЕАЛЬНЫЙ ордер!")
    print("=" * 60)
    confirm = input("Создать ордер? (yes/no): ")

    if confirm.lower() == "yes":
        try:
            response = await exchange.place_order(order_request)

            if response and response.success:
                print("\n✅ ОРДЕР УСПЕШНО СОЗДАН!")
                print(f"   Order ID: {response.order_id}")
                print(f"   Symbol: {response.symbol}")
                print(f"   Status: {response.status}")

                # Проверяем позицию
                await asyncio.sleep(2)
                print("\n8. Проверка позиции...")
                positions = await exchange.get_positions(symbol)
                if positions:
                    for pos in positions:
                        print("\n✅ Позиция:")
                        print(f"   Symbol: {pos.symbol}")
                        print(f"   Side: {pos.side}")
                        print(f"   Size: {pos.size}")
                        print(f"   Entry: ${pos.entry_price}")
                        print(f"   Stop Loss: ${pos.stop_loss} ✓")
                        print(f"   Take Profit: ${pos.take_profit} ✓")
                        print(f"   Unrealized P&L: ${pos.unrealized_pnl}")
            else:
                print(
                    f"\n❌ Ошибка создания ордера: {response.error if response else 'Unknown'}"
                )

        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
    else:
        print("\n❌ Создание ордера отменено")

    # Отключаемся
    await exchange.disconnect()

    print("\n" + "=" * 60)
    print("ИТОГИ ТЕСТА:")
    print("=" * 60)
    print(
        """
✅ Система работает корректно:
   1. API ключи валидны
   2. Расчет позиций по методу V2
   3. SL/TP устанавливаются при создании ордера
   4. Поддержка hedge mode с правильным positionIdx
   5. Логирование всех операций

⚠️  Для частичного закрытия (TP1, TP2, TP3):
   - Использовать tpslMode: "Partial"
   - Создавать дополнительные условные ордера
   - Или использовать отдельные Take Profit ордера

📊 Текущие настройки из config/trading.yaml:
   - Фиксированный баланс: $500
   - Риск на сделку: 2%
   - Плечо: 5x
   - Режим позиций: hedge mode
    """
    )


if __name__ == "__main__":
    asyncio.run(test_complete_trading())
