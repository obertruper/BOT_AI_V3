#!/usr/bin/env python3
"""
Тестирование улучшенной системы логирования
Демонстрация полного цикла торговли с детальными логами
"""

import asyncio
from datetime import datetime

from core.logging.trade_logger import get_trade_logger
from trading.orders.order_logger import OrderLogger
from trading.sltp.sltp_logger import SLTPLogger


async def simulate_trade_cycle():
    """Симуляция полного торгового цикла с детальным логированием"""

    # Инициализация логгеров
    trade_logger = get_trade_logger()
    order_logger = OrderLogger()
    sltp_logger = SLTPLogger()

    print("\n" + "=" * 60)
    print("🚀 ЗАПУСК СИМУЛЯЦИИ ТОРГОВОГО ЦИКЛА")
    print("=" * 60)

    # 1. ПОЛУЧЕНИЕ СИГНАЛА
    print("\n📡 Этап 1: Получение сигнала")
    signal = {
        "id": "SIG_001",
        "symbol": "BTCUSDT",
        "signal_type": "BUY",
        "strength": 0.75,
        "confidence": 0.82,
        "source": "ML_STRATEGY",
        "price": 50000,
    }

    trade_logger.log_signal_received(signal)
    await asyncio.sleep(0.5)

    # 2. ОБРАБОТКА СИГНАЛА
    print("\n⚙️ Этап 2: Обработка сигнала")
    trade_logger.log_signal_processing(
        signal["id"], "VALIDATION", {"checks_passed": True, "risk_approved": True}
    )
    await asyncio.sleep(0.5)

    # 3. СОЗДАНИЕ ОРДЕРА
    print("\n📝 Этап 3: Создание ордера")
    order = {
        "id": "ORD_001",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": 0.01,
        "price": 50000,
        "leverage": 5,
        "signal_id": signal["id"],
    }

    trade_logger.log_order_creation(order)

    # Валидация ордера
    order_logger.log_order_validation(
        order, {"valid": True, "checks": ["size", "balance", "leverage"]}
    )

    # Проверка рисков
    order_logger.log_order_risk_check(
        order, {"risk_percent": 2.0, "max_allowed": 3.0, "approved": True}
    )
    await asyncio.sleep(0.5)

    # 4. ОТПРАВКА ОРДЕРА
    print("\n📤 Этап 4: Отправка ордера на биржу")
    trade_logger.log_order_submission(
        order["id"], "BYBIT", {"retCode": 0, "retMsg": "OK", "orderId": "EX_ORD_123"}
    )

    order_logger.log_order_lifecycle(
        order["id"],
        "SUBMITTED",
        {"exchange_id": "EX_ORD_123", "timestamp": datetime.now().isoformat()},
    )
    await asyncio.sleep(0.5)

    # 5. ИСПОЛНЕНИЕ ОРДЕРА
    print("\n✅ Этап 5: Исполнение ордера")
    execution = {
        "executed_qty": 0.01,
        "executed_price": 50050,  # Небольшой slippage
        "commission": 0.00001,
        "commission_asset": "BTC",
        "slippage": 0.1,
        "execution_time_ms": 152,
    }

    trade_logger.log_order_execution(order["id"], execution)
    order_logger.log_order_execution_details(order["id"], execution)
    await asyncio.sleep(0.5)

    # 6. ОТКРЫТИЕ ПОЗИЦИИ
    print("\n🟢 Этап 6: Открытие позиции")
    position = {
        "id": "POS_001",
        "symbol": "BTCUSDT",
        "side": "LONG",
        "size": 0.01,
        "entry_price": 50050,
        "leverage": 5,
    }

    trade_logger.log_position_opened(position)
    await asyncio.sleep(0.5)

    # 7. УСТАНОВКА SL/TP
    print("\n🎯 Этап 7: Установка SL/TP с частичными уровнями")

    # Расчет SL/TP
    sltp_logger.log_sltp_calculation(
        position,
        {"percent": 2.0, "price": 49049, "distance": 1001},
        {"percent": 4.0, "price": 52052, "risk_reward_ratio": 2.0},
    )

    # Частичные TP уровни
    partial_levels = [
        {"price": 50550, "percent": 1.0, "close_ratio": 0.3, "quantity": 0.003},
        {"price": 51050, "percent": 2.0, "close_ratio": 0.3, "quantity": 0.003},
        {"price": 51550, "percent": 3.0, "close_ratio": 0.4, "quantity": 0.004},
    ]

    sltp_logger.log_partial_tp_setup(position["id"], partial_levels)

    trade_logger.log_sltp_setup(
        position["id"], sl_price=49049, tp_price=52052, partial_levels=partial_levels
    )
    await asyncio.sleep(0.5)

    # 8. СИМУЛЯЦИЯ ДВИЖЕНИЯ ЦЕНЫ И TRAILING STOP
    print("\n📈 Этап 8: Движение цены и Trailing Stop")

    current_price = 50050
    highest_price = current_price
    current_sl = 49049
    trailing_activated = False
    updates_count = 0

    # Симулируем рост цены
    price_movements = [50200, 50500, 50800, 51000, 50900, 51200]

    for new_price in price_movements:
        current_price = new_price
        profit_pct = (
            (current_price - position["entry_price"]) / position["entry_price"]
        ) * 100

        # Обновление PnL
        unrealized_pnl = (current_price - position["entry_price"]) * position["size"]
        trade_logger.log_pnl_update(position["id"], unrealized_pnl, 0, profit_pct)

        # Активация trailing stop при 1% прибыли
        if profit_pct >= 1.0 and not trailing_activated:
            trailing_activated = True
            trade_logger.log_trailing_activated(
                position["id"], current_price, profit_pct
            )

        # Обновление trailing stop
        if trailing_activated and current_price > highest_price:
            highest_price = current_price
            new_sl = current_price * 0.995  # 0.5% trailing distance

            if new_sl > current_sl:
                trade_logger.log_trailing_update(
                    position["id"], current_sl, new_sl, current_price
                )
                current_sl = new_sl
                updates_count += 1

                # Логирование состояния trailing
                sltp_logger.log_trailing_stop_state(
                    position["id"],
                    {
                        "activated": True,
                        "current_price": current_price,
                        "entry_price": position["entry_price"],
                        "current_sl": current_sl,
                        "highest_price": highest_price,
                        "profit_percent": profit_pct,
                        "updates_count": updates_count,
                    },
                )

        await asyncio.sleep(0.3)

    # 9. ЧАСТИЧНОЕ ЗАКРЫТИЕ
    print("\n📊 Этап 9: Частичное закрытие на первом уровне")

    # Симулируем достижение первого TP
    if current_price >= partial_levels[0]["price"]:
        sltp_logger.log_partial_tp_execution(
            position["id"],
            level=1,
            executed_qty=0.003,
            executed_price=partial_levels[0]["price"],
            remaining_qty=0.007,
        )

        trade_logger.log_partial_close(
            position["id"],
            level=1,
            percent=30,
            quantity=0.003,
            price=partial_levels[0]["price"],
        )

        # Перенос SL в безубыток
        trade_logger.log_sl_moved_to_breakeven(
            position["id"],
            position["entry_price"],
            position["entry_price"] + 10,  # Небольшой отступ
        )

        sltp_logger.log_sl_adjustment(
            position["id"],
            "Перенос в безубыток после частичного закрытия",
            current_sl,
            position["entry_price"] + 10,
            position["entry_price"],
        )

        await asyncio.sleep(0.5)

    # 10. ЗАЩИТА ПРИБЫЛИ
    print("\n🛡️ Этап 10: Защита прибыли")

    sltp_logger.log_profit_protection(
        position["id"],
        {
            "profit_percent": profit_pct,
            "locked_profit": 1.0,
            "new_sl": current_sl,
            "type": "partial",
        },
    )
    await asyncio.sleep(0.5)

    # 11. ЗАКРЫТИЕ ПОЗИЦИИ
    print("\n🔴 Этап 11: Закрытие позиции")

    close_price = 51100
    final_pnl = (close_price - position["entry_price"]) * position["size"]

    trade_logger.log_position_closed(
        position["id"], close_price, final_pnl, "TP достигнут"
    )

    trade_logger.log_sltp_triggered(position["id"], "TP", close_price, final_pnl)
    await asyncio.sleep(0.5)

    # 12. СТАТИСТИКА
    print("\n📊 Этап 12: Итоговая статистика")
    trade_logger.log_daily_summary()

    stats = trade_logger.get_statistics()
    print("\n📈 Статистика торгового цикла:")
    for key, value in stats.items():
        print(f"   {key}: {value}")

    print("\n" + "=" * 60)
    print("✅ СИМУЛЯЦИЯ ЗАВЕРШЕНА")
    print("=" * 60)
    print("\n📁 Логи сохранены в:")
    print("   - data/logs/trades_*.log")
    print("   - data/logs/bot_trading.log")
    print("   - Консольный вывод с цветным форматированием")


async def test_error_logging():
    """Тестирование логирования ошибок"""
    print("\n" + "=" * 60)
    print("❌ ТЕСТ ЛОГИРОВАНИЯ ОШИБОК")
    print("=" * 60)

    trade_logger = get_trade_logger()
    sltp_logger = SLTPLogger()
    order_logger = OrderLogger()

    # Ошибка валидации
    trade_logger.log_signal_rejected("SIG_002", "Недостаточный баланс")

    # Ошибка ордера
    order_logger.log_order_retry("ORD_002", 1, "Connection timeout")
    order_logger.log_order_retry("ORD_002", 2, "Rate limit exceeded")

    # Ошибка SL/TP
    sltp_logger.log_sltp_error(
        "POS_002",
        "SET_STOP_LOSS",
        "Invalid stop loss price",
        {"attempted_sl": 48000, "current_price": 50000},
    )

    # Общая ошибка
    trade_logger.log_error(
        "API_ERROR",
        "Failed to connect to exchange",
        {"exchange": "BYBIT", "attempts": 3},
        Exception("Connection refused"),
    )

    print("\n✅ Ошибки залогированы")


async def main():
    """Главная функция тестирования"""
    print("\n🎯 ТЕСТИРОВАНИЕ УЛУЧШЕННОЙ СИСТЕМЫ ЛОГИРОВАНИЯ")
    print("=" * 60)

    # Запускаем симуляцию торгового цикла
    await simulate_trade_cycle()

    # Тестируем логирование ошибок
    await test_error_logging()

    print("\n✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ")
    print("\n💡 Рекомендации:")
    print("1. Проверьте файлы логов в data/logs/")
    print("2. Настройте уровни логирования в config/logging.yaml")
    print("3. Используйте trade_logger для всех торговых операций")
    print("4. Добавьте WebSocket логирование для real-time отслеживания")
    print("5. Настройте ротацию логов для production")


if __name__ == "__main__":
    asyncio.run(main())
